import io
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core import auth
from app.core.config import Settings
from app.db.models import Audit, AuditPrompt, AuditScreen, Finding, Membership, Project, PromptVersion, ScreenAsset, Tenant, User
from app.services.ai_vision import DeterministicVisionProvider
from app.services.storage import get_storage


def create_sample_png_bytes(width: int = 1440, height: int = 900) -> bytes:
    img = Image.new("RGB", (width, height), color="navy")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class MockStorage:
    def __init__(self):
        self.objects = {}

    def head(self, key):
        if key not in self.objects:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "404", "Message": "NoSuchKey"}}, "HeadObject")
        data, ctype = self.objects[key]
        return {"ContentLength": len(data), "ContentType": ctype}

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    def get_object(self, key: str) -> bytes:
        if key not in self.objects:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "404", "Message": "NoSuchKey"}}, "GetObject")
        return self.objects[key][0]

    def presign_upload(self, key: str, content_type: str, max_bytes: int):
        return f"http://test-storage/{key}?put"

    def presign_download(self, key: str, filename: str):
        return f"http://test-storage/{key}/{filename}"

    def delete(self, key: str):
        self.objects.pop(key, None)


@pytest.fixture
def auth_headers(monkeypatch):
    settings = Settings(
        app_env="development",
        dev_auth_enabled=True,
        dev_auth_secret="test-secret-at-least-32-bytes-long-key",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    token, _, _ = auth.issue_dev_token("auditor@forteux.local", "Test Auditor", settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_storage_instance():
    return MockStorage()


def setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance):
    """Helper to set up a project, screenshot, audit, and analyze to produce findings."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage_instance

    # 1. Project
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Stitch Redesign Project"})
    project_id = p_res.json()["id"]

    # 2. Upload Screen
    img_bytes = create_sample_png_bytes(1440, 900)
    up_res = client.post(
        f"/api/v1/projects/{project_id}/uploads",
        headers={**auth_headers, "Idempotency-Key": f"key-{uuid4()}"},
        json={"filename": "dashboard.png", "content_type": "image/png", "size": len(img_bytes)},
    )
    asset_id = up_res.json()["asset_id"]
    asset = db_session.get(ScreenAsset, UUID(asset_id))
    mock_storage_instance.put_object(asset.object_key, img_bytes, "image/png")
    client.post(f"/api/v1/projects/{project_id}/assets/{asset_id}/complete", headers=auth_headers)

    # 3. Audit
    a_res = client.post(
        f"/api/v1/projects/{project_id}/audits",
        headers=auth_headers,
        json={
            "name": "SaaS Analytics Dashboard Audit",
            "mode": "single",
            "context": {
                "product": "Pulse Analytics",
                "goal": "Review conversion metrics and adjust campaign budget",
                "audience": "Marketing Managers",
                "constraints": "Keep primary brand indigo #4F46E5",
            },
        },
    )
    audit_id = a_res.json()["id"]

    # 4. Attach Screen
    client.post(
        f"/api/v1/projects/{project_id}/audits/{audit_id}/screens",
        headers=auth_headers,
        json={"screen_asset_id": asset_id, "sequence_index": 0, "screen_label": "Campaign Overview"},
    )

    # 5. Analyze Screen to generate findings
    analysis_res = client.post(f"/api/v1/projects/{project_id}/audits/{audit_id}/analyze", headers=auth_headers)
    findings = analysis_res.json()["findings"]
    assert len(findings) >= 2

    return project_id, audit_id, asset_id, findings


def test_prompt_generation_with_selected_findings(client, db_session, auth_headers, mock_storage_instance):
    project_id, audit_id, asset_id, findings = setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance)
    try:
        # Select all findings
        selected_ids = [f["id"] for f in findings]
        res = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={"selected_finding_ids": selected_ids},
        )
        assert res.status_code == 201
        data = res.json()

        assert data["audit_id"] == audit_id
        assert data["version_number"] == 1
        assert len(data["selected_finding_ids"]) == len(selected_ids)
        assert len(data["versions"]) == 1

        prompt_text = data["content"]
        # Required structural sections
        assert "# Google Stitch Redesign Brief" in prompt_text
        assert "## 1. Role & Objective" in prompt_text
        assert "## 2. Existing Interface Context" in prompt_text
        assert "## 3. Core Design Objectives" in prompt_text
        assert "## 4. Prioritized Issues & Required Design Solutions" in prompt_text
        assert "## 5. Visual Design Requirements" in prompt_text
        assert "Strict Design Constraints" in prompt_text
        assert "Expected Output for Google Stitch" in prompt_text
        assert "Pulse Analytics" in prompt_text
        assert "Marketing Managers" in prompt_text
        assert "Keep primary brand indigo #4F46E5" in prompt_text

        # Verify all selected findings are detailed
        for f in findings:
            assert f["title"] in prompt_text
            assert f["why_it_matters"] in prompt_text
            assert f["recommended_fix"] in prompt_text
    finally:
        client.app.dependency_overrides.pop(get_storage, None)


def test_prompt_generation_excludes_unselected_findings(client, db_session, auth_headers, mock_storage_instance):
    project_id, audit_id, asset_id, findings = setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance)
    try:
        assert len(findings) >= 2
        included_finding = findings[0]
        excluded_finding = findings[1]

        # Only select first finding
        res = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={"selected_finding_ids": [included_finding["id"]]},
        )
        assert res.status_code == 201
        prompt_text = res.json()["content"]

        # Included finding must be present
        assert included_finding["title"] in prompt_text
        assert included_finding["recommended_fix"] in prompt_text

        # Excluded finding must NOT be present as an issue
        assert f"### Issue 1: {included_finding['title']}" in prompt_text
        assert f"{excluded_finding['title']}" not in prompt_text
        assert f"{excluded_finding['description']}" not in prompt_text
    finally:
        client.app.dependency_overrides.pop(get_storage, None)


def test_prompt_generation_empty_selection_fails(client, db_session, auth_headers, mock_storage_instance):
    project_id, audit_id, asset_id, findings = setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance)
    try:
        res = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={"selected_finding_ids": []},
        )
        assert res.status_code in (400, 422)
    finally:
        client.app.dependency_overrides.pop(get_storage, None)


def test_prompt_generation_with_invalid_or_foreign_finding_id(client, db_session, auth_headers, mock_storage_instance):
    project_id, audit_id, asset_id, findings = setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance)
    try:
        foreign_id = str(uuid4())
        res = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={"selected_finding_ids": [foreign_id]},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "invalid_findings"
    finally:
        client.app.dependency_overrides.pop(get_storage, None)


def test_prompt_generation_user_instructions(client, db_session, auth_headers, mock_storage_instance):
    project_id, audit_id, asset_id, findings = setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance)
    try:
        res = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={
                "selected_finding_ids": [findings[0]["id"]],
                "user_instructions": "Adopt a clean bento-grid card layout with 12px pill badges and muted gray secondary tabs.",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["user_instructions"] == "Adopt a clean bento-grid card layout with 12px pill badges and muted gray secondary tabs."
        assert "User-Specified Design Instructions" in data["content"]
        assert "Adopt a clean bento-grid card layout" in data["content"]
    finally:
        client.app.dependency_overrides.pop(get_storage, None)


def test_prompt_editing_and_restoring(client, db_session, auth_headers, mock_storage_instance):
    project_id, audit_id, asset_id, findings = setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance)
    try:
        # 1. Create prompt
        create_res = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={"selected_finding_ids": [findings[0]["id"]]},
        )
        prompt_id = create_res.json()["id"]
        orig_content = create_res.json()["original_generated_content"]

        # 2. Edit prompt
        edited_text = "This is a custom user-edited prompt with specific manual design guidelines."
        patch_res = client.patch(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt/{prompt_id}",
            headers=auth_headers,
            json={"content": edited_text},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["content"] == edited_text
        assert patch_res.json()["original_generated_content"] == orig_content

        # 3. Restore original
        restore_res = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt/{prompt_id}/restore-original",
            headers=auth_headers,
        )
        assert restore_res.status_code == 200
        assert restore_res.json()["content"] == orig_content
    finally:
        client.app.dependency_overrides.pop(get_storage, None)


def test_prompt_regeneration_and_version_history(client, db_session, auth_headers, mock_storage_instance):
    project_id, audit_id, asset_id, findings = setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance)
    try:
        # Generation 1 (v1)
        r1 = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={"selected_finding_ids": [findings[0]["id"]]},
        )
        assert r1.status_code == 201
        assert r1.json()["version_number"] == 1

        # Regeneration 2 (v2 with more findings)
        all_ids = [f["id"] for f in findings]
        r2 = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={"selected_finding_ids": all_ids, "user_instructions": "Make it modern"},
        )
        assert r2.status_code == 201
        v2_data = r2.json()
        assert v2_data["version_number"] == 2
        assert len(v2_data["versions"]) == 2
        assert v2_data["versions"][0]["version_number"] == 2
        assert v2_data["versions"][1]["version_number"] == 1

        # Query GET /prompt
        get_res = client.get(f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt", headers=auth_headers)
        assert get_res.status_code == 200
        assert get_res.json()["version_number"] == 2
    finally:
        client.app.dependency_overrides.pop(get_storage, None)


def test_prompt_tenant_isolation(client, db_session, auth_headers, mock_storage_instance):
    project_id, audit_id, asset_id, findings = setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance)
    try:
        client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={"selected_finding_ids": [findings[0]["id"]]},
        )

        # Another tenant's principal
        other_user = User(oidc_issuer="issuer", oidc_subject=f"other-{uuid4()}")
        other_tenant = Tenant(name="Tenant Beta")
        db_session.add_all([other_user, other_tenant])
        db_session.flush()
        db_session.add(Membership(tenant_id=other_tenant.id, user_id=other_user.id, role="owner"))
        db_session.commit()

        client.app.dependency_overrides[auth.get_current_principal] = lambda: auth.Principal(
            id=other_user.id,
            tenant_id=other_tenant.id,
            issuer="issuer",
            subject="subject",
        )

        # Attempt to access prompt
        res = client.get(f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt")
        assert res.status_code == 404
    finally:
        client.app.dependency_overrides.pop(auth.get_current_principal, None)
        client.app.dependency_overrides.pop(get_storage, None)


def test_prompt_quality_evaluation(client, db_session, auth_headers, mock_storage_instance):
    """
    Evaluates prompt output quality against 7 explicit quality criteria:
    1. Selected findings present
    2. Excluded findings omitted
    3. Actionable design outcomes
    4. Product context preservation
    5. Constraints protection
    6. Severity prioritization
    7. Clean markdown structure
    """
    project_id, audit_id, asset_id, findings = setup_audit_with_findings(client, db_session, auth_headers, mock_storage_instance)
    try:
        assert len(findings) >= 2
        selected = [findings[0]]
        unselected = [findings[1]]

        res = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/prompt",
            headers=auth_headers,
            json={"selected_finding_ids": [selected[0]["id"]]},
        )
        assert res.status_code == 201
        prompt = res.json()["content"]

        # 1. Selected findings present
        assert selected[0]["title"] in prompt
        # 2. Excluded findings omitted
        assert unselected[0]["title"] not in prompt
        # 3. Actionable design outcomes
        assert "Required Improvement" in prompt
        # 4. Product context preservation
        assert "Pulse Analytics" in prompt
        # 5. Constraints protection
        assert "Strict Design Constraints" in prompt
        assert "Do not alter the fundamental purpose" in prompt
        # 6. Severity prioritization
        assert f"[{selected[0]['severity'].upper()}]" in prompt
        # 7. Clean markdown structure
        assert prompt.startswith("# Google Stitch Redesign Brief")
        assert "## 1. Role & Objective" in prompt
    finally:
        client.app.dependency_overrides.pop(get_storage, None)
