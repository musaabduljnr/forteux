import io
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core import auth
from app.core.config import Settings
from app.db.models import Audit, AuditPrompt, AuditScreen, Finding, Membership, Project, ScreenAsset, Tenant, User
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
    token, _, _ = auth.issue_dev_token("flow_auditor@forteux.local", "Flow Auditor", settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_storage():
    return MockStorage()


def upload_asset(client, db_session, project_id, auth_headers, mock_storage, filename="screen.png", width=1440, height=900):
    img_bytes = create_sample_png_bytes(width, height)
    up_res = client.post(
        f"/api/v1/projects/{project_id}/uploads",
        headers={**auth_headers, "Idempotency-Key": f"key-{uuid4()}"},
        json={"filename": filename, "content_type": "image/png", "size": len(img_bytes)},
    )
    asset_id = up_res.json()["asset_id"]
    asset = db_session.get(ScreenAsset, UUID(asset_id))
    mock_storage.put_object(asset.object_key, img_bytes, "image/png")
    client.post(f"/api/v1/projects/{project_id}/assets/{asset_id}/complete", headers=auth_headers)
    return asset_id


# ---------------------------------------------------------------------------
# Group A: Screen Management
# ---------------------------------------------------------------------------


def test_multi_screen_audit_creation(client, auth_headers):
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Multi Project"})
    project_id = p_res.json()["id"]

    a_res = client.post(
        f"/api/v1/projects/{project_id}/audits",
        headers=auth_headers,
        json={
            "name": "Checkout Flow Journey",
            "mode": "multi",
            "context": {"journey_name": "Checkout Flow", "product": "E-Commerce"},
        },
    )
    assert a_res.status_code == 201
    data = a_res.json()
    assert data["mode"] == "multi"
    assert data["name"] == "Checkout Flow Journey"


def test_attach_multiple_screens(client, db_session, auth_headers, mock_storage):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "P1"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Flow", "mode": "multi"})
    aid = a_res.json()["id"]

    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "step1.png")
    a2 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "step2.png")
    a3 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "step3.png")

    s1 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0, "screen_label": "Cart"})
    s2 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a2, "sequence_index": 1, "screen_label": "Shipping"})
    s3 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a3, "sequence_index": 2, "screen_label": "Payment"})

    assert s1.status_code == 201
    assert s2.status_code == 201
    assert s3.status_code == 201

    list_res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers)
    assert list_res.status_code == 200
    screens = list_res.json()
    assert len(screens) == 3
    assert [s["screen_label"] for s in screens] == ["Cart", "Shipping", "Payment"]
    assert [s["sequence_index"] for s in screens] == [0, 1, 2]


def test_screen_label_and_description_update(client, db_session, auth_headers, mock_storage):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "P2"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Flow", "mode": "multi"})
    aid = a_res.json()["id"]
    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "step1.png")
    s1 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0, "screen_label": "Original"})
    sid = s1.json()["id"]

    patch_res = client.patch(
        f"/api/v1/projects/{pid}/audits/{aid}/screens/{sid}",
        headers=auth_headers,
        json={"screen_label": "Updated Cart Step", "screen_description": "Initial cart review screen with promo code input"},
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["screen_label"] == "Updated Cart Step"
    assert data["screen_description"] == "Initial cart review screen with promo code input"


def test_screen_reorder(client, db_session, auth_headers, mock_storage):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "P3"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Flow", "mode": "multi"})
    aid = a_res.json()["id"]
    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s1.png")
    a2 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s2.png")
    s1 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0, "screen_label": "First"}).json()
    s2 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a2, "sequence_index": 1, "screen_label": "Second"}).json()

    # Reorder: swap sequence indices
    reorder_res = client.post(
        f"/api/v1/projects/{pid}/audits/{aid}/screens/reorder",
        headers=auth_headers,
        json={"screens": [{"screen_id": s1["id"], "sequence_index": 1}, {"screen_id": s2["id"], "sequence_index": 0}]},
    )
    assert reorder_res.status_code == 200
    reordered = reorder_res.json()
    assert reordered[0]["id"] == s2["id"]
    assert reordered[0]["sequence_index"] == 0
    assert reordered[1]["id"] == s1["id"]
    assert reordered[1]["sequence_index"] == 1


def test_remove_screen_from_multi_audit(client, db_session, auth_headers, mock_storage):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "P4"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Flow", "mode": "multi"})
    aid = a_res.json()["id"]
    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s1.png")
    a2 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s2.png")
    s1 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0}).json()
    s2 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a2, "sequence_index": 1}).json()

    del_res = client.delete(f"/api/v1/projects/{pid}/audits/{aid}/screens/{s2['id']}", headers=auth_headers)
    assert del_res.status_code == 204

    list_res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers)
    assert len(list_res.json()) == 1


def test_single_audit_enforce_one_screen_limit(client, db_session, auth_headers, mock_storage):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "P5"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Single", "mode": "single"})
    aid = a_res.json()["id"]
    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s1.png")
    a2 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s2.png")

    client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0})
    s2_res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a2, "sequence_index": 1})
    assert s2_res.status_code == 409


# ---------------------------------------------------------------------------
# Group B: Multi-Screen Flow Analysis
# ---------------------------------------------------------------------------


def setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Flow Project"})
    pid = p_res.json()["id"]
    a_res = client.post(
        f"/api/v1/projects/{pid}/audits",
        headers=auth_headers,
        json={
            "name": "Onboarding Journey",
            "mode": "multi",
            "context": {
                "journey_name": "User Onboarding",
                "product": "SaaS Platform",
                "intended_user": "New team admins",
                "objective": "Complete workspace setup and invite teammates",
            },
        },
    )
    aid = a_res.json()["id"]

    screen_ids = []
    labels = ["Welcome", "Workspace Setup", "Invite Team", "Completion"]
    dimensions = [(1440, 900), (1440, 900), (390, 844), (1440, 900)]
    for i in range(count):
        w, h = dimensions[i % len(dimensions)]
        asset_id = upload_asset(client, db_session, pid, auth_headers, mock_storage, f"step_{i+1}.png", w, h)
        s_res = client.post(
            f"/api/v1/projects/{pid}/audits/{aid}/screens",
            headers=auth_headers,
            json={"screen_asset_id": asset_id, "sequence_index": i, "screen_label": labels[i]},
        )
        screen_ids.append(s_res.json()["id"])
    return pid, aid, screen_ids


def test_analyze_flow_success_two_screens(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["job"]["status"] == "completed"
    assert "journey_report" in data
    assert len(data["screen_level_findings"]) >= 2
    assert len(data["cross_screen_findings"]) >= 1


def test_analyze_flow_requires_multi_mode(client, db_session, auth_headers, mock_storage):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Single Audit Proj"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Single", "mode": "single"})
    aid = a_res.json()["id"]
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "unsupported_audit_mode"


def test_analyze_flow_requires_min_two_screens(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=1)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "insufficient_screens"


def test_screen_level_findings_scope(client, db_session, auth_headers, mock_storage):
    pid, aid, screen_ids = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers).json()
    for f in res["screen_level_findings"]:
        assert f["scope"] == "screen_level"
        assert len(f["affected_screen_ids"]) == 1
        assert f["affected_screen_ids"][0] in screen_ids


def test_cross_screen_findings_scope(client, db_session, auth_headers, mock_storage):
    pid, aid, screen_ids = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers).json()
    for f in res["cross_screen_findings"]:
        assert f["scope"] == "cross_screen"


def test_cross_screen_findings_reference_multiple_screens(client, db_session, auth_headers, mock_storage):
    pid, aid, screen_ids = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers).json()
    for f in res["cross_screen_findings"]:
        assert len(f["affected_screen_ids"]) >= 2
        for sid in f["affected_screen_ids"]:
            assert sid in screen_ids


def test_journey_report_in_response(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers).json()
    jr = res["journey_report"]
    assert "journey_summary" in jr
    assert "apparent_structure" in jr
    assert "overall_assessment" in jr
    assert len(jr["strengths"]) >= 1
    assert len(jr["major_friction_points"]) >= 1
    assert len(jr["recommended_improvements"]) >= 1
    assert "limitations" in jr


def test_re_analysis_clears_previous_findings(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    first_count = db_session.query(Finding).filter(Finding.audit_id == UUID(aid)).count()
    assert first_count > 0

    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    second_count = db_session.query(Finding).filter(Finding.audit_id == UUID(aid)).count()
    assert second_count == first_count


# ---------------------------------------------------------------------------
# Group C: Bounding Box & Screen References
# ---------------------------------------------------------------------------


def test_multi_screen_bounding_boxes_have_screen_id(client, db_session, auth_headers, mock_storage):
    pid, aid, screen_ids = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers).json()
    all_findings = res["screen_level_findings"] + res["cross_screen_findings"]
    for f in all_findings:
        for box in f["bounding_boxes"]:
            assert "screen_id" in box
            assert box["screen_id"] in screen_ids


def test_cross_screen_finding_boxes_on_multiple_screens(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers).json()
    cross = res["cross_screen_findings"]
    assert len(cross) >= 1
    # Check that at least one cross finding has boxes from multiple screens
    multi_box_found = False
    for f in cross:
        box_screens = {b["screen_id"] for b in f["bounding_boxes"]}
        if len(box_screens) > 1:
            multi_box_found = True
            break
    assert multi_box_found


def test_screen_level_finding_boxes_valid_coords(client, db_session, auth_headers, mock_storage):
    pid, aid, screen_ids = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers).json()
    for f in res["screen_level_findings"]:
        for box in f["bounding_boxes"]:
            assert box["screen_id"] == f["affected_screen_ids"][0]


def test_bounding_box_coords_between_zero_and_one(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers).json()
    for f in res["screen_level_findings"] + res["cross_screen_findings"]:
        for box in f["bounding_boxes"]:
            assert 0.0 <= box["x"] <= 1.0
            assert 0.0 <= box["y"] <= 1.0
            assert 0.0 < box["width"] <= 1.0
            assert 0.0 < box["height"] <= 1.0


# ---------------------------------------------------------------------------
# Group D: Journey Report & Flow Report Endpoint
# ---------------------------------------------------------------------------


def test_flow_report_404_before_analysis(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)
    res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/flow-report", headers=auth_headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "no_flow_report"


def test_flow_report_structure_after_analysis(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)

    res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/flow-report", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["journey_report"] is not None
    assert "journey_summary" in data["journey_report"]


def test_flow_report_contains_both_finding_scopes(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)

    res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/flow-report", headers=auth_headers).json()
    assert len(res["screen_level_findings"]) > 0
    assert len(res["cross_screen_findings"]) > 0


# ---------------------------------------------------------------------------
# Group E: Multi-Screen Prompt Generation
# ---------------------------------------------------------------------------


def test_multi_screen_prompt_generation_success(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)

    findings = client.get(f"/api/v1/projects/{pid}/audits/{aid}/findings", headers=auth_headers).json()
    assert len(findings) > 0
    selected_ids = [f["id"] for f in findings]

    p_res = client.post(
        f"/api/v1/projects/{pid}/audits/{aid}/prompt",
        headers=auth_headers,
        json={"selected_finding_ids": selected_ids, "user_instructions": "Use consistent 8px card radius across all screens"},
    )
    assert p_res.status_code == 201
    prompt_data = p_res.json()
    content = prompt_data["content"]

    assert "# Google Stitch Multi-Screen Redesign Brief" in content
    assert "## 1. Role & Objective" in content
    assert "## 2. Product & User Journey Context" in content
    assert "## 3. Screen Sequence Overview" in content
    assert "## 7. Navigation & Progression Architecture" in content
    assert "## 11. Expected Multi-Screen Output for Google Stitch" in content


def test_multi_screen_prompt_includes_screen_labels(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    findings = client.get(f"/api/v1/projects/{pid}/audits/{aid}/findings", headers=auth_headers).json()

    p_res = client.post(
        f"/api/v1/projects/{pid}/audits/{aid}/prompt",
        headers=auth_headers,
        json={"selected_finding_ids": [findings[0]["id"]]},
    )
    content = p_res.json()["content"]
    assert "Welcome" in content
    assert "Workspace Setup" in content


def test_multi_screen_prompt_cross_screen_section_present(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    findings = client.get(f"/api/v1/projects/{pid}/audits/{aid}/findings", headers=auth_headers).json()

    p_res = client.post(
        f"/api/v1/projects/{pid}/audits/{aid}/prompt",
        headers=auth_headers,
        json={"selected_finding_ids": [f["id"] for f in findings]},
    )
    content = p_res.json()["content"]
    assert "## 4. Cross-Screen Continuity & Consistency Fixes" in content


def test_multi_screen_prompt_excludes_unselected_findings(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=3)
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    findings = client.get(f"/api/v1/projects/{pid}/audits/{aid}/findings", headers=auth_headers).json()

    # Pick only first finding
    selected = [findings[0]["id"]]
    excluded_title = findings[-1]["title"]

    p_res = client.post(
        f"/api/v1/projects/{pid}/audits/{aid}/prompt",
        headers=auth_headers,
        json={"selected_finding_ids": selected},
    )
    content = p_res.json()["content"]
    assert findings[0]["title"] in content
    assert excluded_title not in content


# ---------------------------------------------------------------------------
# Group F: Security & Isolation
# ---------------------------------------------------------------------------


def test_tenant_isolation_multi_screen_audit(client, db_session, auth_headers, mock_storage, monkeypatch):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)

    # Different tenant token
    settings = Settings(app_env="development", dev_auth_enabled=True, dev_auth_secret="test-secret-at-least-32-bytes-long-key")
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    token_b, _, _ = auth.issue_dev_token("intruder@other.local", "Tenant B User", settings)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=headers_b)
    assert res.status_code == 404

    screens_res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=headers_b)
    assert screens_res.status_code == 404


def test_analyze_flow_project_isolation(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)
    fake_pid = uuid4()
    res = client.post(f"/api/v1/projects/{fake_pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    assert res.status_code == 404


def test_re_analysis_no_duplicate_findings(client, db_session, auth_headers, mock_storage):
    pid, aid, _ = setup_multi_screen_audit_with_screens(client, db_session, auth_headers, mock_storage, count=2)
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    f1 = client.get(f"/api/v1/projects/{pid}/audits/{aid}/findings", headers=auth_headers).json()

    client.post(f"/api/v1/projects/{pid}/audits/{aid}/analyze-flow", headers=auth_headers)
    f2 = client.get(f"/api/v1/projects/{pid}/audits/{aid}/findings", headers=auth_headers).json()

    assert len(f1) == len(f2)
