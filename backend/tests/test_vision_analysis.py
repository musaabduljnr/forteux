import io
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core import auth
from app.core.config import Settings
from app.db.models import Audit, AuditScreen, Finding, Membership, Project, ScreenAsset, Tenant, User
from app.services.ai_vision import (
    AIVisionService,
    AnalysisResult,
    BoundingBox,
    DeterministicVisionProvider,
    FindingResult,
    VisionProvider,
    get_vision_service,
)
from app.services.image import ImageValidationError, validate_and_process_image
from app.services.storage import get_storage


def create_sample_png_bytes(width: int = 400, height: int = 300, color: str = "red") -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_sample_jpeg_bytes(width: int = 400, height: int = 300, color: str = "blue") -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


class MockStorage:
    def __init__(self):
        self.objects = {}

    def presign_upload(self, key, content_type, size):
        return f"https://mock-storage.test/{key}?put"

    def head(self, key):
        if key not in self.objects:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "404", "Message": "NoSuchKey"}}, "HeadObject")
        data, ctype = self.objects[key]
        return {"ContentLength": len(data), "ContentType": ctype}

    def get_object(self, key):
        if key not in self.objects:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "404", "Message": "NoSuchKey"}}, "GetObject")
        return self.objects[key][0]

    def put_object(self, key, data, content_type):
        self.objects[key] = (data, content_type)

    def presign_download(self, key, filename):
        return f"https://mock-storage.test/{key}?get"

    def delete(self, key):
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


def test_image_validation_valid_png():
    raw = create_sample_png_bytes(500, 300)
    meta = validate_and_process_image(raw, "image/png")
    assert meta.width == 500
    assert meta.height == 300
    assert meta.format == "PNG"
    assert meta.mime_type == "image/png"
    assert len(meta.sha256) == 64


def test_image_validation_valid_jpeg():
    raw = create_sample_jpeg_bytes(800, 600)
    meta = validate_and_process_image(raw, "image/jpeg")
    assert meta.width == 800
    assert meta.height == 600
    assert meta.format == "JPEG"


def test_image_validation_invalid_magic_bytes():
    bad_data = b"NOT_AN_IMAGE_FILE_BYTES"
    with pytest.raises(ImageValidationError) as err:
        validate_and_process_image(bad_data, "image/png")
    assert err.value.code == "invalid_magic_bytes"


def test_bounding_box_normalization_and_clamping():
    # Valid box
    b = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
    assert b.x == 0.1
    assert b.y == 0.2
    assert b.width == 0.3
    assert b.height == 0.4

    # Overflow clamped to 1.0 boundary
    overflow = BoundingBox(x=0.8, y=0.7, width=0.5, height=0.5)
    assert overflow.x == 0.8
    assert overflow.width <= 0.2  # clamped so x + width <= 1.0
    assert overflow.height <= 0.3


def test_complete_upload_and_image_dimension_extraction(client, db_session, auth_headers, mock_storage_instance):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage_instance
    try:
        # 1. Create project
        p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Vision Test Project"})
        assert p_res.status_code == 201
        project_id = p_res.json()["id"]

        # 2. Initiate upload
        img_bytes = create_sample_png_bytes(640, 480)
        up_res = client.post(
            f"/api/v1/projects/{project_id}/uploads",
            headers={**auth_headers, "Idempotency-Key": f"key-{uuid4()}"},
            json={"filename": "dashboard.png", "content_type": "image/png", "size": len(img_bytes)},
        )
        assert up_res.status_code == 201
        asset_id = up_res.json()["asset_id"]

        # 3. Simulate upload to storage
        asset = db_session.get(ScreenAsset, UUID(asset_id))
        mock_storage_instance.put_object(asset.object_key, img_bytes, "image/png")

        # 4. Complete upload
        comp_res = client.post(f"/api/v1/projects/{project_id}/assets/{asset_id}/complete", headers=auth_headers)
        assert comp_res.status_code == 200
        data = comp_res.json()
        assert data["status"] == "uploaded_verified"
        assert data["width_px"] == 640
        assert data["height_px"] == 480
        assert data["sha256"] is not None
    finally:
        client.app.dependency_overrides.pop(get_storage, None)


def test_single_screen_ai_analysis_workflow(client, db_session, auth_headers, mock_storage_instance):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage_instance
    try:
        # 1. Create project
        p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Audit Analysis Project"})
        project_id = p_res.json()["id"]

        # 2. Upload and complete screenshot
        img_bytes = create_sample_png_bytes(1440, 900)
        up_res = client.post(
            f"/api/v1/projects/{project_id}/uploads",
            headers={**auth_headers, "Idempotency-Key": f"key-{uuid4()}"},
            json={"filename": "checkout.png", "content_type": "image/png", "size": len(img_bytes)},
        )
        asset_id = up_res.json()["asset_id"]
        asset = db_session.get(ScreenAsset, UUID(asset_id))
        mock_storage_instance.put_object(asset.object_key, img_bytes, "image/png")
        client.post(f"/api/v1/projects/{project_id}/assets/{asset_id}/complete", headers=auth_headers)

        # 3. Create single-screen audit
        a_res = client.post(
            f"/api/v1/projects/{project_id}/audits",
            headers=auth_headers,
            json={"name": "Checkout Usability Audit", "mode": "single", "context": {"product": "Checkout Flow"}},
        )
        assert a_res.status_code == 201
        audit_id = a_res.json()["id"]

        # 4. Attach screenshot to audit
        att_res = client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/screens",
            headers=auth_headers,
            json={"screen_asset_id": asset_id, "sequence_index": 0, "screen_label": "Cart Review"},
        )
        assert att_res.status_code == 201
        assert att_res.json()["width_px"] == 1440

        # 5. List audit screens
        list_screens = client.get(f"/api/v1/projects/{project_id}/audits/{audit_id}/screens", headers=auth_headers)
        assert list_screens.status_code == 200
        assert len(list_screens.json()) == 1

        # 6. Run AI Analysis
        analysis_res = client.post(f"/api/v1/projects/{project_id}/audits/{audit_id}/analyze", headers=auth_headers)
        assert analysis_res.status_code == 200
        analysis_data = analysis_res.json()
        assert analysis_data["job"]["status"] == "completed"
        assert len(analysis_data["findings"]) > 0

        first_finding = analysis_data["findings"][0]
        assert first_finding["title"]
        assert first_finding["category"] in [
            "visual_hierarchy",
            "layout_spacing",
            "typography",
            "color_contrast",
            "components_consistency",
            "usability",
            "accessibility_indicator",
        ]
        assert first_finding["severity"] in ["critical", "high", "medium", "low"]
        assert 0.0 <= first_finding["confidence"] <= 1.0
        assert first_finding["evidence_type"] in ["observed", "inferred"]
        assert len(first_finding["bounding_boxes"]) > 0
        box = first_finding["bounding_boxes"][0]
        assert 0.0 <= box["x"] <= 1.0
        assert 0.0 <= box["y"] <= 1.0
        assert 0.0 < box["width"] <= 1.0
        assert 0.0 < box["height"] <= 1.0

        # 7. Query persisted findings endpoint
        findings_res = client.get(f"/api/v1/projects/{project_id}/audits/{audit_id}/findings", headers=auth_headers)
        assert findings_res.status_code == 200
        assert len(findings_res.json()) == len(analysis_data["findings"])
    finally:
        client.app.dependency_overrides.pop(get_storage, None)


def test_analysis_zero_findings_state(client, db_session, auth_headers, mock_storage_instance):
    class ZeroFindingsProvider(VisionProvider):
        def analyze(self, image_bytes, mime_type, image_width, image_height, context=None):
            return AnalysisResult(
                summary="The screenshot shows excellent visual balance and no significant UI/UX defects were observed.",
                findings=[],
                provider="zero-provider",
                model="zero-model-v1",
            )

    client.app.dependency_overrides[get_storage] = lambda: mock_storage_instance
    client.app.dependency_overrides[get_vision_service] = lambda: AIVisionService(ZeroFindingsProvider())
    try:
        # Setup audit and asset
        p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "P-Zero"})
        project_id = p_res.json()["id"]

        img_bytes = create_sample_png_bytes(500, 500)
        up_res = client.post(
            f"/api/v1/projects/{project_id}/uploads",
            headers={**auth_headers, "Idempotency-Key": f"key-{uuid4()}"},
            json={"filename": "clean.png", "content_type": "image/png", "size": len(img_bytes)},
        )
        asset_id = up_res.json()["asset_id"]
        asset = db_session.get(ScreenAsset, UUID(asset_id))
        mock_storage_instance.put_object(asset.object_key, img_bytes, "image/png")
        client.post(f"/api/v1/projects/{project_id}/assets/{asset_id}/complete", headers=auth_headers)

        a_res = client.post(f"/api/v1/projects/{project_id}/audits", headers=auth_headers, json={"name": "Clean UI Audit", "mode": "single"})
        audit_id = a_res.json()["id"]

        client.post(
            f"/api/v1/projects/{project_id}/audits/{audit_id}/screens",
            headers=auth_headers,
            json={"screen_asset_id": asset_id, "sequence_index": 0},
        )

        analysis_res = client.post(f"/api/v1/projects/{project_id}/audits/{audit_id}/analyze", headers=auth_headers)
        assert analysis_res.status_code == 200
        data = analysis_res.json()
        assert data["job"]["status"] == "completed"
        assert len(data["findings"]) == 0
        assert "no significant UI/UX defects" in data["job"]["summary"]
    finally:
        client.app.dependency_overrides.pop(get_storage, None)
        client.app.dependency_overrides.pop(get_vision_service, None)


def test_analysis_fails_gracefully_when_no_screenshot(client, auth_headers, mock_storage_instance):
    client.app.dependency_overrides[get_storage] = lambda: mock_storage_instance
    try:
        p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Empty Audit Project"})
        project_id = p_res.json()["id"]

        a_res = client.post(f"/api/v1/projects/{project_id}/audits", headers=auth_headers, json={"name": "No Screen Audit", "mode": "single"})
        audit_id = a_res.json()["id"]

        res = client.post(f"/api/v1/projects/{project_id}/audits/{audit_id}/analyze", headers=auth_headers)
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "no_screenshot_attached"
    finally:
        client.app.dependency_overrides.pop(get_storage, None)
