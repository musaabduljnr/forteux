from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import HTTPException

from app.core import auth
from app.core.config import Settings
from app.db.models import Membership, Tenant, User


@pytest.fixture
def access_token(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    issuer = "https://issuer.example.test"
    client_id = "client-test"
    settings = Settings(
        app_env="test",
        oidc_issuer=issuer,
        oidc_client_id=client_id,
        oidc_jwks_url=f"{issuer}/.well-known/jwks.json",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(
        auth,
        "_jwks_client",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
        ),
    )

    def issue(**overrides):
        now = datetime.now(timezone.utc)
        claims = {
            "iss": issuer,
            "sub": "subject-123",
            "client_id": client_id,
            "token_use": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "email": "user@example.test",
            "name": "Test User",
        }
        claims.update(overrides)
        return jwt.encode(claims, private_key, algorithm="RS256")

    return issue


def test_rejects_missing_bearer_token(client):
    response = client.get("/api/v1/projects")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.headers["www-authenticate"] == "Bearer"


def test_rejects_non_access_tokens(access_token):
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token(access_token(token_use="id"))
    assert error.value.status_code == 401


def test_reports_jwks_outage_as_temporary_authentication_failure(access_token, monkeypatch):
    def fail_to_fetch_keys(_url):
        raise jwt.PyJWKClientConnectionError("identity provider is unavailable")

    monkeypatch.setattr(auth, "_jwks_client", fail_to_fetch_keys)
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token(access_token())
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "identity_provider_unavailable"


def test_verified_identity_creates_user_and_personal_tenant(client, db_session, access_token):
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {access_token()}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "user@example.test"
    repeated = client.get("/api/v1/me", headers={"Authorization": f"Bearer {access_token()}"})
    assert repeated.status_code == 200
    assert repeated.json()["id"] == payload["id"]
    assert db_session.query(User).count() == 1
    assert db_session.query(Tenant).count() == 1
    assert db_session.query(Membership).count() == 1


def test_verifies_supabase_es256_token_even_when_jwt_secret_configured(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    issuer = "https://edlkpfrlsrgslcdwjykv.supabase.co/auth/v1"
    settings = Settings(
        app_env="test",
        supabase_url="https://edlkpfrlsrgslcdwjykv.supabase.co",
        supabase_jwt_secret="some-hs256-secret-configured-in-env",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(
        auth,
        "_jwks_client",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=private_key.public_key())
        ),
    )

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": issuer,
            "sub": "user-uuid-123",
            "aud": "authenticated",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "email": "musa@example.com",
            "user_metadata": {"full_name": "Musa Abubakar"},
        },
        private_key,
        algorithm="ES256",
    )

    claims = auth.verify_access_token(token)
    assert claims["sub"] == "user-uuid-123"
    assert claims["name"] == "Musa Abubakar"
