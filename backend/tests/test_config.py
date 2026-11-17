import pytest

from app.core.config import Settings


def test_production_database_requires_postgresql_tls():
    settings = Settings(
        app_env="production",
        database_url="postgresql+psycopg://user:password@db.example.test/app",
    )
    with pytest.raises(RuntimeError, match="require TLS"):
        settings.require_database()


def test_production_database_accepts_verified_tls():
    database_url = "postgresql+psycopg://user:password@db.example.test/app?sslmode=verify-full"
    settings = Settings(app_env="production", database_url=database_url)
    assert settings.require_database() == database_url


def test_production_jwks_endpoint_requires_https():
    settings = Settings(
        app_env="production",
        oidc_issuer="https://issuer.example.test",
        oidc_client_id="client",
        oidc_jwks_url="http://issuer.example.test/keys",
    )
    with pytest.raises(RuntimeError, match="JWKS_URL must use HTTPS"):
        settings.require_oidc()
