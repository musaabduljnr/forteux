from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException

from app.core import auth
from app.core.config import Settings
from app.db.models import Membership, Project, Tenant, User


@pytest.fixture
def dev_settings(monkeypatch):
    settings = Settings(
        app_env="development",
        dev_auth_enabled=True,
        dev_auth_secret="test-secret-at-least-32-bytes-long-key",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    return settings


def test_issue_and_verify_dev_token(dev_settings):
    token, expires_in, subject = auth.issue_dev_token("dev@example.test", "Dev Tester", dev_settings)
    assert isinstance(token, str)
    assert expires_in == 3600
    assert subject.startswith("dev:") or len(subject) > 10

    claims = auth.verify_access_token(token)
    assert claims["iss"] == "forteux-dev-auth"
    assert claims["sub"] == subject
    assert claims["email"] == "dev@example.test"
    assert claims["name"] == "Dev Tester"
    assert claims["client_id"] == "forteux-dev-client"
    assert claims["token_use"] == "access"


def test_dev_auth_strictly_forbidden_in_production(monkeypatch):
    # Setting dev_auth_enabled=True in production must raise RuntimeError
    with pytest.raises(RuntimeError) as err:
        Settings(app_env="production", dev_auth_enabled=True)
    assert "cannot be enabled in production" in str(err.value)

    # A dev token presented in production must be rejected with 401
    prod_settings = Settings(app_env="production", dev_auth_enabled=False)
    monkeypatch.setattr(auth, "get_settings", lambda: prod_settings)
    dev_token = jwt.encode(
        {
            "iss": "forteux-dev-auth",
            "sub": "some-sub",
            "client_id": "forteux-dev-client",
            "token_use": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "test-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as http_err:
        auth.verify_access_token(dev_token)
    assert http_err.value.status_code == 401


def test_dev_token_endpoint_disabled_when_flag_false(client, monkeypatch):
    settings = Settings(app_env="development", dev_auth_enabled=False)
    from app.api.v1 import routes
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    res = client.post("/api/v1/auth/dev-token", json={"email": "dev@example.test", "name": "Dev"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "dev_auth_disabled"


def test_dev_token_endpoint_success_when_enabled(client, monkeypatch, dev_settings):
    from app.api.v1 import routes
    monkeypatch.setattr(routes, "get_settings", lambda: dev_settings)

    res = client.post("/api/v1/auth/dev-token", json={"email": "alice@forteux.local", "name": "Alice"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert data["email"] == "alice@forteux.local"
    assert data["name"] == "Alice"


def test_dev_user_lifecycle_and_tenant_isolation(client, db_session, monkeypatch, dev_settings):
    from app.api.v1 import routes
    monkeypatch.setattr(routes, "get_settings", lambda: dev_settings)

    token_alice, _, _ = auth.issue_dev_token("alice@forteux.local", "Alice", dev_settings)
    token_bob, _, _ = auth.issue_dev_token("bob@forteux.local", "Bob", dev_settings)

    # Alice accesses /me
    res_a = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token_alice}"})
    assert res_a.status_code == 200
    alice_data = res_a.json()
    assert alice_data["email"] == "alice@forteux.local"

    # Bob accesses /me
    res_b = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token_bob}"})
    assert res_b.status_code == 200
    bob_data = res_b.json()
    assert bob_data["email"] == "bob@forteux.local"
    assert alice_data["id"] != bob_data["id"]
    assert alice_data["tenant_id"] != bob_data["tenant_id"]

    # Alice creates a project
    create_res = client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={"name": "Alice Secret Project", "description": "For Alice eyes only"},
    )
    assert create_res.status_code == 201
    project_id = create_res.json()["id"]

    # Alice can list it
    list_a = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token_alice}"})
    assert list_a.status_code == 200
    assert any(p["id"] == project_id for p in list_a.json())

    # Bob CANNOT see Alice's project in his list
    list_b = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token_bob}"})
    assert list_b.status_code == 200
    assert not any(p["id"] == project_id for p in list_b.json())

    # Bob CANNOT read Alice's project directly (404)
    read_b = client.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {token_bob}"})
    assert read_b.status_code == 404
