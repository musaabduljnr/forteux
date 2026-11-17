from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


class HealthyStorage:
    def __init__(self, _settings):
        pass

    def healthcheck(self):
        return None


def test_liveness_does_not_depend_on_external_services():
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_readiness_checks_database_oidc_and_storage(tmp_path, monkeypatch):
    from app import main

    database_path = tmp_path / "ready.sqlite"
    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            app_env="test",
            database_url=f"sqlite:///{database_path}",
            oidc_issuer="https://issuer.example.test",
            oidc_client_id="client",
            oidc_jwks_url="https://issuer.example.test/keys",
            aws_region="us-east-1",
            s3_bucket="private-test-bucket",
        ),
    )
    monkeypatch.setattr(main, "S3Storage", HealthyStorage)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "database": "ready",
            "authentication": "configured",
            "object_storage": "ready",
        },
    }


def test_readiness_with_dev_auth_adapter(tmp_path, monkeypatch):
    from app import main

    database_path = tmp_path / "ready_dev.sqlite"
    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            app_env="development",
            database_url=f"sqlite:///{database_path}",
            dev_auth_enabled=True,
            aws_region="us-east-1",
            s3_bucket="private-test-bucket",
        ),
    )
    monkeypatch.setattr(main, "S3Storage", HealthyStorage)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["authentication"] == "configured"


def test_readiness_reports_missing_dependencies():
    from app import main

    original_settings = main.settings
    main.settings = Settings(app_env="test")
    try:
        with TestClient(app) as client:
            response = client.get("/health/ready")
    finally:
        main.settings = original_settings

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert set(response.json()["checks"].values()) == {"unavailable"}
