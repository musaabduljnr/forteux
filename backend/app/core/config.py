from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "production"] = "production"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    database_url: str | None = None

    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_jwks_url: str | None = None

    aws_region: str | None = None
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_upload_ttl_seconds: int = Field(default=300, ge=60, le=900)
    s3_download_ttl_seconds: int = Field(default=300, ge=60, le=900)

    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    knowledge_max_doc_bytes: int = Field(default=20 * 1024 * 1024, ge=1)
    knowledge_embedding_model: str = "deterministic-v1"
    knowledge_embedding_dimensions: int = 768
    allowed_origins: str = ""

    dev_auth_enabled: bool = False
    dev_auth_secret: str | None = None

    def __init__(self, **values: object):
        super().__init__(**values)
        if self.app_env == "production" and self.dev_auth_enabled:
            raise RuntimeError("DEV_AUTH_ENABLED cannot be enabled in production environment")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def jwks_url(self) -> str | None:
        if self.oidc_jwks_url:
            return self.oidc_jwks_url
        if self.oidc_issuer:
            return f"{self.oidc_issuer.rstrip('/')}/.well-known/jwks.json"
        return None

    def require_database(self) -> str:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        if self.app_env == "production":
            parsed = urlsplit(self.database_url)
            if parsed.scheme not in {"postgresql", "postgresql+psycopg", "postgres"}:
                raise RuntimeError("Production DATABASE_URL must use PostgreSQL")
            sslmode = parse_qs(parsed.query).get("sslmode", [])
            if not sslmode or sslmode[0] not in {"require", "verify-ca", "verify-full"}:
                raise RuntimeError("Production PostgreSQL connections must require TLS")
        return self.database_url

    def require_oidc(self) -> tuple[str, str, str]:
        if not self.oidc_issuer or not self.oidc_client_id or not self.jwks_url:
            if self.app_env != "production" and self.dev_auth_enabled:
                return "forteux-dev-auth", "forteux-dev-client", "http://localhost:8000/api/v1/auth/dev-jwks"
            raise RuntimeError("OIDC_ISSUER, OIDC_CLIENT_ID, and OIDC_JWKS_URL are required")
        if self.app_env == "production" and not self.oidc_issuer.startswith("https://"):
            raise RuntimeError("Production OIDC_ISSUER must use HTTPS")
        if self.app_env == "production" and not self.jwks_url.startswith("https://"):
            raise RuntimeError("Production OIDC_JWKS_URL must use HTTPS")
        return self.oidc_issuer.rstrip("/"), self.oidc_client_id, self.jwks_url

    def require_storage(self) -> tuple[str, str]:
        if not self.aws_region or not self.s3_bucket:
            raise RuntimeError("AWS_REGION and S3_BUCKET are required")
        if self.app_env == "production" and self.s3_endpoint_url and not self.s3_endpoint_url.startswith("https://"):
            raise RuntimeError("Production S3_ENDPOINT_URL must use HTTPS")
        return self.aws_region, self.s3_bucket


@lru_cache
def get_settings() -> Settings:
    return Settings()
