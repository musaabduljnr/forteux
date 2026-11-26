from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import Membership, Tenant, User
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)
DEV_AUTH_ISSUER = "forteux-dev-auth"
DEV_AUTH_CLIENT_ID = "forteux-dev-client"
DEFAULT_DEV_SECRET = "forteux-dev-secret-key-32bytes-min"

@dataclass(frozen=True)
class Principal:
    id: UUID
    tenant_id: UUID
    issuer: str
    subject: str


@lru_cache
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, timeout=5)


def issue_dev_token(email: str, name: str, settings: Settings | None = None) -> tuple[str, int, str]:
    current_settings = settings or get_settings()
    if current_settings.app_env == "production" or not current_settings.dev_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "dev_auth_disabled", "message": "Development authentication is disabled"},
        )
    now = datetime.now(timezone.utc)
    expires_in = 3600
    subject = str(uuid5(NAMESPACE_DNS, f"dev:{email.lower().strip()}"))
    secret = current_settings.dev_auth_secret or DEFAULT_DEV_SECRET
    claims = {
        "iss": DEV_AUTH_ISSUER,
        "sub": subject,
        "client_id": DEV_AUTH_CLIENT_ID,
        "token_use": "access",
        "email": email.strip(),
        "name": name.strip(),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(claims, secret, algorithm="HS256")
    return token, expires_in, subject


def verify_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        # Check unverified header/claims to distinguish development tokens from OIDC tokens
        unverified = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        token_iss = unverified.get("iss")
        token_aud = unverified.get("aud")

        if token_iss == DEV_AUTH_ISSUER:
            if settings.app_env == "production" or not settings.dev_auth_enabled:
                raise jwt.InvalidTokenError("Development authentication is not permitted")
            secret = settings.dev_auth_secret or DEFAULT_DEV_SECRET
            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                issuer=DEV_AUTH_ISSUER,
                options={"verify_aud": False, "require": ["exp", "iat", "sub", "iss"]},
            )
            if claims.get("token_use") != "access" or claims.get("client_id") != DEV_AUTH_CLIENT_ID:
                raise jwt.InvalidTokenError("Token is not an access token for development client")
            return claims

        # Check for Supabase JWT (HS256 with JWT secret or RS256/ES256 with JWKS)
        is_supabase_token = (
            (token_iss and "supabase.co" in token_iss)
            or token_aud == "authenticated"
            or (settings.supabase_url and token_iss and settings.supabase_url in token_iss)
        )
        if is_supabase_token:
            token_alg = jwt.get_unverified_header(token).get("alg")
            if settings.supabase_jwt_secret and token_alg == "HS256":
                try:
                    claims = jwt.decode(
                        token,
                        settings.supabase_jwt_secret,
                        algorithms=["HS256"],
                        options={"verify_aud": False, "require": ["exp", "iat", "sub"]},
                    )
                    user_meta = claims.get("user_metadata") or {}
                    if not claims.get("name") and user_meta.get("full_name"):
                        claims["name"] = user_meta["full_name"]
                    return claims
                except (jwt.InvalidSignatureError, jwt.InvalidAlgorithmError):
                    # Might be signed with asymmetric key
                    pass

            if token_iss:
                jwks_url = f"{token_iss.rstrip('/')}/.well-known/jwks.json"
                signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
                claims = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256", "ES256"],
                    issuer=token_iss,
                    options={"verify_aud": False, "require": ["exp", "iat", "sub", "iss"]},
                )
                user_meta = claims.get("user_metadata") or {}
                if not claims.get("name") and user_meta.get("full_name"):
                    claims["name"] = user_meta["full_name"]
                return claims

        issuer, client_id, jwks_url = settings.require_oidc()
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False, "require": ["exp", "iat", "sub", "iss"]},
        )
        if claims.get("token_use") != "access" or claims.get("client_id") != client_id:
            raise jwt.InvalidTokenError("Token is not an access token for this client")
        return claims
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "auth_not_configured", "message": "Authentication is not configured"},
        ) from error
    except jwt.PyJWKClientConnectionError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "identity_provider_unavailable", "message": "Authentication is temporarily unavailable"},
        ) from error
    except (jwt.PyJWTError, OSError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "A valid access token is required"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "Sign in is required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = verify_access_token(credentials.credentials)
    issuer = claims["iss"]
    subject = claims["sub"]
    user = db.scalar(select(User).where(User.oidc_issuer == issuer, User.oidc_subject == subject))
    if user is None:
        user = User(
            oidc_issuer=issuer,
            oidc_subject=subject,
            email=claims.get("email"),
            display_name=claims.get("name"),
        )
        tenant = Tenant(name=(claims.get("email") or "Personal workspace")[:200])
        db.add_all([user, tenant])
        try:
            db.flush()
            db.add(Membership(tenant_id=tenant.id, user_id=user.id, role="owner"))
            db.commit()
        except IntegrityError:
            db.rollback()
            user = db.scalar(select(User).where(User.oidc_issuer == issuer, User.oidc_subject == subject))
            if user is None:
                raise
    if user.disabled_at is not None:
        raise HTTPException(status_code=403, detail={"code": "account_disabled", "message": "This account is disabled"})
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id).order_by(Membership.created_at))
    if membership is None:
        tenant = Tenant(name=(claims.get("email") or "Personal workspace")[:200])
        db.add(tenant)
        try:
            db.flush()
            membership = Membership(tenant_id=tenant.id, user_id=user.id, role="owner")
            db.add(membership)
            db.commit()
        except IntegrityError:
            db.rollback()
            membership = db.scalar(
                select(Membership).where(Membership.user_id == user.id).order_by(Membership.created_at)
            )
            if membership is None:
                raise
    return Principal(id=user.id, tenant_id=membership.tenant_id, issuer=issuer, subject=subject)
