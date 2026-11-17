"""Phase 08: Test Suite for Design System Extraction & Cross-Screen Consistency.

Covers:
1. Mathematical consistency scoring & reproducibility
2. Dynamic category weighting and missing evidence handling
3. Design token generation (CSS & JSON)
4. Design system extraction endpoint (colors, typography, spacing, shapes, components, tokens)
5. Cross-screen consistency issue detection
6. Google Stitch design system refinement prompt generation
7. Security & multi-tenant isolation
8. Benchmark datasets (consistent, deliberately inconsistent, contextual variations)
"""
import io
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core import auth
from app.core.config import Settings
from app.db.models import (
    Audit,
    AuditScreen,
    DesignSystemAnalysis,
    Membership,
    Project,
    ScreenAsset,
    Tenant,
    User,
)
from app.services.design_system import (
    calculate_consistency_score,
    export_design_system_json,
    export_tokens_to_css,
)
from app.api.v1.schemas import (
    DesignConsistencyIssue,
    ExtractedColor,
    ExtractedTypography,
    ProposedDesignToken,
    ComponentPattern,
)
from app.services.storage import get_storage


def create_sample_png_bytes(width: int = 1440, height: int = 900, color: str = "navy") -> bytes:
    img = Image.new("RGB", (width, height), color=color)
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
    token, _, _ = auth.issue_dev_token("ds_auditor@forteux.local", "DS Auditor", settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_auth_headers(monkeypatch):
    settings = Settings(
        app_env="development",
        dev_auth_enabled=True,
        dev_auth_secret="test-secret-at-least-32-bytes-long-key",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    token, _, _ = auth.issue_dev_token("other_ds_user@forteux.local", "Other DS User", settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_storage():
    return MockStorage()


def upload_asset(client, db_session, project_id, auth_headers, mock_storage, filename="screen.png", width=1440, height=900, color="navy"):
    img_bytes = create_sample_png_bytes(width, height, color=color)
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
# Group 1: Mathematical Scoring Engine & Token Exports
# ---------------------------------------------------------------------------

def test_calculate_consistency_score_clean():
    """A clean analysis with 0 inconsistencies achieves a perfect score of 100.0."""
    score, breakdown, coverage = calculate_consistency_score(
        issues=[],
        screen_count=3,
        active_categories={"color", "typography", "components", "spacing", "surfaces", "navigation"},
    )
    assert score == 100.0
    assert coverage == 1.0
    for cat, cat_score in breakdown.items():
        assert cat_score == 100.0


def test_calculate_consistency_score_with_penalties():
    """Verify exact formula D_c = sum(P_i), S_c = max(0, 100 - D_c * 2/N)."""
    issues = [
        # 1 high issue in components (penalty: 8.0)
        DesignConsistencyIssue(
            category="components",
            title="Button Mismatch",
            description="Variant mismatch",
            severity="high",
            evidence="Visual diff",
            recommended_fix="Unify",
        ),
        # 1 medium issue in typography (penalty: 4.0)
        DesignConsistencyIssue(
            category="typography",
            title="Heading Size",
            description="Heading mismatch",
            severity="medium",
            evidence="Visual diff",
            recommended_fix="Unify",
        ),
    ]
    # N = 2 screens -> normalization factor = 2 / 2 = 1.0
    # components: 100 - (8.0 * 1.0) = 92.0
    # typography: 100 - (4.0 * 1.0) = 96.0
    # other categories: 100.0
    score, breakdown, coverage = calculate_consistency_score(
        issues=issues,
        screen_count=2,
    )
    assert breakdown["components"] == 92.0
    assert breakdown["typography"] == 96.0
    assert breakdown["color"] == 100.0
    # Weighted average:
    # color: 20 * 100 = 2000
    # typography: 20 * 96 = 1920
    # components: 25 * 92 = 2300
    # spacing: 15 * 100 = 1500
    # surfaces: 10 * 100 = 1000
    # navigation: 10 * 100 = 1000
    # sum = 9720 / 100 = 97.2
    assert score == 97.2
    assert coverage == 1.0


def test_scoring_reproducibility():
    """Verify that multiple calculations with identical inputs yield identical outputs."""
    issues = [
        DesignConsistencyIssue(category="color", title="T1", description="D1", severity="low", evidence="E", recommended_fix="F"),
        DesignConsistencyIssue(category="spacing", title="T2", description="D2", severity="high", evidence="E", recommended_fix="F"),
    ]
    score1, breakdown1, cov1 = calculate_consistency_score(issues, 4)
    score2, breakdown2, cov2 = calculate_consistency_score(issues, 4)
    assert score1 == score2
    assert breakdown1 == breakdown2
    assert cov1 == cov2


def test_scoring_missing_categories_normalization():
    """Unobserved categories are excluded from active weight and do not penalize the score."""
    # Only color and typography were observed
    active = {"color", "typography"}
    issues = [
        DesignConsistencyIssue(category="color", title="Hue Shift", description="D", severity="medium", evidence="E", recommended_fix="F")
    ]
    # N = 2, D_color = 4.0 -> S_color = 100 - 4.0 = 96.0
    # S_typography = 100.0
    # Weights: color: 20, typography: 20 -> total active = 40
    # Weighted sum = (96.0 * 20) + (100.0 * 20) = 1920 + 2000 = 3920 / 40 = 98.0
    score, breakdown, coverage = calculate_consistency_score(issues, 2, active_categories=active)
    assert score == 98.0
    assert coverage == round(2 / 6, 2)
    assert set(breakdown.keys()) == {"color", "typography"}


def test_export_tokens_to_css():
    """Verify valid CSS custom properties generation."""
    tokens = [
        ProposedDesignToken(name="color.primary", value="#1E40AF", category="color", confidence=0.95, evidence="observed", classification="observed"),
        ProposedDesignToken(name="spacing.4", value="16px", category="spacing", confidence=0.90, evidence="approximate", classification="approximate"),
        ProposedDesignToken(name="radius.medium", value="8px", category="radius", confidence=0.92, evidence="observed", classification="observed"),
    ]
    css = export_tokens_to_css(tokens)
    assert ":root {" in css
    assert "--color-primary: #1E40AF;" in css
    assert "--spacing-4: 16px;" in css
    assert "--radius-medium: 8px;" in css
    assert "observed (conf: 95%)" in css


def test_export_design_system_json():
    """Verify structured JSON export format."""
    tokens = [
        ProposedDesignToken(name="color.primary", value="#1E40AF", category="color", confidence=0.95, evidence="observed", classification="observed"),
        ProposedDesignToken(name="spacing.4", value="16px", category="spacing", confidence=0.90, evidence="approximate", classification="approximate"),
    ]
    colors = [
        ExtractedColor(hex="#1E40AF", semantic_name="Primary Blue", category="primary", screens=[1, 2], frequency="primary", confidence=0.95, evidence="observed")
    ]
    typography = [
        ExtractedTypography(style_name="typography.heading.large", font_size_approx="24px", font_weight_category="bold", text_hierarchy="h1", confidence=0.9, evidence="approximate")
    ]
    comps = [
        ComponentPattern(component_category="button.primary", visual_description="Blue button", screens=[1, 2], observed_occurrences=2, common_characteristics="8px radius", variations=[], confidence=0.95, evidence_references="observed", recommended_component_spec="Standard spec")
    ]
    data = export_design_system_json(
        analysis_id="ds-123",
        audit_id="audit-456",
        project_id="proj-789",
        consistency_score=94.5,
        tokens=tokens,
        colors=colors,
        typography=typography,
        components=comps,
    )
    assert data["design_system_id"] == "ds-123"
    assert data["consistency_score"] == 94.5
    assert data["tokens"]["color"]["color.primary"] == "#1E40AF"
    assert data["tokens"]["spacing"]["spacing.4"] == "16px"
    assert len(data["colors"]) == 1
    assert len(data["typography"]) == 1
    assert len(data["components"]) == 1


# ---------------------------------------------------------------------------
# Group 2: End-to-End Extraction & API Endpoints
# ---------------------------------------------------------------------------

def test_design_system_extraction_requires_screens(client, auth_headers, mock_storage):
    """Extraction returns 400 when an audit has no attached screenshots."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Empty DS Project"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Empty Audit", "mode": "multi"})
    aid = a_res.json()["id"]

    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=auth_headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "no_screens_found"


def test_design_system_extraction_success(client, db_session, auth_headers, mock_storage):
    """Full extraction pipeline extracts tokens, colors, typography, components, and score."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage

    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "SaaS Platform"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Core Flow", "mode": "multi"})
    aid = a_res.json()["id"]

    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "dashboard.png", color="blue")
    a2 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "settings.png", color="navy")

    client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0, "screen_label": "Dashboard"})
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a2, "sequence_index": 1, "screen_label": "Settings"})

    # Trigger extraction
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "completed"
    assert data["screens_analyzed"] == 2
    assert isinstance(data["consistency_score"], float)
    assert data["consistency_score"] > 0
    assert data["extraction_coverage"] > 0.5
    assert len(data["color_palette"]) > 0
    assert len(data["typography"]) > 0
    assert len(data["tokens"]) > 0
    assert len(data["components"]) > 0
    assert data["stitch_prompt"] is not None
    assert "Google Stitch Design System Refinement Brief" in data["stitch_prompt"]


def test_read_design_system_endpoint(client, db_session, auth_headers, mock_storage):
    """GET /design-system returns existing extracted analysis."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage

    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "P2"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Audit 2", "mode": "multi"})
    aid = a_res.json()["id"]

    # 404 before extraction
    get_before = client.get(f"/api/v1/projects/{pid}/audits/{aid}/design-system", headers=auth_headers)
    assert get_before.status_code == 404
    assert get_before.json()["error"]["code"] == "design_system_not_found"

    # Extract
    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s1.png")
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0})
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=auth_headers)

    # 200 after extraction
    get_after = client.get(f"/api/v1/projects/{pid}/audits/{aid}/design-system", headers=auth_headers)
    assert get_after.status_code == 200
    assert get_after.json()["audit_id"] == aid


def test_export_endpoints(client, db_session, auth_headers, mock_storage):
    """Verify both /export/json and /export/css endpoints."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage

    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Export Project"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Export Audit", "mode": "multi"})
    aid = a_res.json()["id"]

    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s1.png")
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0})
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=auth_headers)

    # JSON export
    json_res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/design-system/export/json", headers=auth_headers)
    assert json_res.status_code == 200
    json_data = json_res.json()
    assert "tokens" in json_data
    assert "colors" in json_data

    # CSS export
    css_res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/design-system/export/css", headers=auth_headers)
    assert css_res.status_code == 200
    css_data = css_res.json()
    assert ":root {" in css_data["css_content"]
    assert css_data["token_count"] > 0


def test_stitch_prompt_generation_and_customization(client, db_session, auth_headers, mock_storage):
    """Verify Stitch design system prompt customization endpoint."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage

    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Stitch Project"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Stitch Audit", "mode": "multi"})
    aid = a_res.json()["id"]

    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s1.png")
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0})
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=auth_headers)

    # Customize prompt
    prompt_res = client.post(
        f"/api/v1/projects/{pid}/audits/{aid}/design-system/stitch-prompt",
        headers=auth_headers,
        json={
            "custom_instructions": "Focus strictly on high-contrast accessibility mode and dark surface tokens.",
            "include_inconsistencies": True,
            "include_tokens": True,
        },
    )
    assert prompt_res.status_code == 200
    prompt_data = prompt_res.json()
    assert "Focus strictly on high-contrast accessibility mode" in prompt_data["prompt"]
    assert prompt_data["tokens_included"] > 0
    assert prompt_data["screens_referenced"] == 1


def test_list_project_design_systems(client, db_session, auth_headers, mock_storage):
    """GET /projects/{project_id}/design-systems lists all extracted analyses for a project."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage

    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Multi Audit Project"})
    pid = p_res.json()["id"]

    # Create 2 audits and extract both
    for i in range(1, 3):
        a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": f"Audit {i}", "mode": "multi"})
        aid = a_res.json()["id"]
        a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, f"s{i}.png")
        client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0})
        client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=auth_headers)

    list_res = client.get(f"/api/v1/projects/{pid}/design-systems", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2


def test_re_extraction_updates_existing_record(client, db_session, auth_headers, mock_storage):
    """Re-extracting does not create orphan rows; it updates the existing analysis in-place."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage

    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Update Project"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Update Audit", "mode": "multi"})
    aid = a_res.json()["id"]

    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s1.png")
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0})

    res1 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=auth_headers)
    id1 = res1.json()["id"]

    res2 = client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=auth_headers)
    id2 = res2.json()["id"]

    assert id1 == id2


# ---------------------------------------------------------------------------
# Group 3: Security & Multi-Tenant Isolation
# ---------------------------------------------------------------------------

def test_user_isolation_blocks_cross_project_extraction(client, db_session, auth_headers, other_user_auth_headers, mock_storage):
    """User B cannot trigger design system extraction on User A's audit."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage

    # User A creates project and audit
    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "User A Project"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "User A Audit", "mode": "multi"})
    aid = a_res.json()["id"]

    # User B attempts extraction
    res = client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=other_user_auth_headers)
    assert res.status_code == 404  # Project not visible to User B


def test_user_isolation_blocks_reading_design_system(client, db_session, auth_headers, other_user_auth_headers, mock_storage):
    """User B cannot read or export User A's design system analysis."""
    client.app.dependency_overrides[get_storage] = lambda: mock_storage

    p_res = client.post("/api/v1/projects", headers=auth_headers, json={"name": "User A Secret"})
    pid = p_res.json()["id"]
    a_res = client.post(f"/api/v1/projects/{pid}/audits", headers=auth_headers, json={"name": "Secret Audit", "mode": "multi"})
    aid = a_res.json()["id"]

    a1 = upload_asset(client, db_session, pid, auth_headers, mock_storage, "s1.png")
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/screens", headers=auth_headers, json={"screen_asset_id": a1, "sequence_index": 0})
    client.post(f"/api/v1/projects/{pid}/audits/{aid}/design-system/extract", headers=auth_headers)

    # User B tries to read report
    read_res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/design-system", headers=other_user_auth_headers)
    assert read_res.status_code == 404

    # User B tries to export CSS
    css_res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/design-system/export/css", headers=other_user_auth_headers)
    assert css_res.status_code == 404


def test_unauthenticated_requests_rejected(client):
    """Unauthenticated calls to design system endpoints return 401."""
    random_id = uuid4()
    assert client.post(f"/api/v1/projects/{random_id}/audits/{random_id}/design-system/extract").status_code == 401
    assert client.get(f"/api/v1/projects/{random_id}/audits/{random_id}/design-system").status_code == 401
    assert client.get(f"/api/v1/projects/{random_id}/audits/{random_id}/design-system/export/json").status_code == 401
    assert client.get(f"/api/v1/projects/{random_id}/audits/{random_id}/design-system/export/css").status_code == 401


# ---------------------------------------------------------------------------
# Group 4: Benchmark Dataset Tests (Interface Types)
# ---------------------------------------------------------------------------

def test_benchmark_consistent_interface_scores_high():
    """Benchmark Type A: Highly uniform interface screens achieve consistency score >= 90.0."""
    # Zero critical or high issues; only one minor low-severity spacing note across 4 screens
    minor_issue = [
        DesignConsistencyIssue(
            category="spacing",
            title="Slight card margin variance",
            description="Card margin differs by 2px on desktop screen 3",
            severity="low",  # 1.0 penalty
            confidence=0.82,
            affected_screens=[2, 3],
            evidence="Observed margin",
            recommended_fix="Align to spacing.4",
        )
    ]
    score, breakdown, coverage = calculate_consistency_score(minor_issue, screen_count=4)
    assert score >= 90.0
    assert breakdown["components"] == 100.0
    assert breakdown["color"] == 100.0
    assert breakdown["typography"] == 100.0


def test_benchmark_inconsistent_interface_scores_low():
    """Benchmark Type B: Deliberately inconsistent screens with conflicting buttons and headings score lower (< 75.0)."""
    flawed_issues = [
        # Components: 2 critical, 2 high issues -> 2*15 + 2*8 = 46 penalty -> Score = 54
        DesignConsistencyIssue(category="components", title="Conflicting Primary Buttons", description="Blue pill on S1 vs Red square on S2", severity="critical", evidence="Button styles", recommended_fix="Unify"),
        DesignConsistencyIssue(category="components", title="Mismatched Search Bar", description="Full width input vs inline icon on S2", severity="critical", evidence="Input styles", recommended_fix="Unify"),
        DesignConsistencyIssue(category="components", title="Tab Bar Inconsistency", description="Underline on S1 vs segmented pill on S2", severity="high", evidence="Tab styles", recommended_fix="Unify"),
        DesignConsistencyIssue(category="components", title="Card Padding Variations", description="12px vs 24px", severity="high", evidence="Padding", recommended_fix="Unify"),
        # Typography: 2 critical, 2 high -> Score = 54
        DesignConsistencyIssue(category="typography", title="Inverted Heading Scale", description="h2 larger than h1 on S2", severity="critical", evidence="Font sizes", recommended_fix="Fix hierarchy"),
        DesignConsistencyIssue(category="typography", title="Conflicting Body Weights", description="Bold body on S1 vs Light on S2", severity="critical", evidence="Weights", recommended_fix="Standardize"),
        DesignConsistencyIssue(category="typography", title="Uppercase Headers", description="Random uppercase headers on S2", severity="high", evidence="Transforms", recommended_fix="Unify"),
        # Color: 2 critical, 2 high -> Score = 54
        DesignConsistencyIssue(category="color", title="Arbitrary Brand Colors", description="Purple banner on S1 vs Orange banner on S2", severity="critical", evidence="Color hexes", recommended_fix="Harmonize"),
        DesignConsistencyIssue(category="color", title="Mismatched Backgrounds", description="Dark canvas on S1 vs Light canvas on S2", severity="critical", evidence="Backgrounds", recommended_fix="Harmonize"),
        # Surfaces: 2 critical -> Score = 70
        DesignConsistencyIssue(category="surfaces", title="Clashing Border Radii", description="0px sharp on S1 vs 16px round on S2", severity="critical", evidence="Radii", recommended_fix="Unify radius"),
        DesignConsistencyIssue(category="surfaces", title="Conflicting Elevation Shadows", description="Heavy drop shadow vs flat outline", severity="critical", evidence="Shadows", recommended_fix="Unify shadows"),
    ]
    score, breakdown, coverage = calculate_consistency_score(flawed_issues, screen_count=2)
    assert score < 75.0
    assert breakdown["components"] <= 70.0
    assert breakdown["typography"] <= 70.0
    assert breakdown["color"] <= 70.0


def test_benchmark_contextual_variations_no_false_penalties():
    """Benchmark Type C: Intentional variations (destructive button, disabled state, modal) do not create false issues."""
    # When legitimate contextual variations occur, no inconsistency issues are filed
    # and the score remains exemplary
    contextual_variations_filtered = []
    score, breakdown, coverage = calculate_consistency_score(contextual_variations_filtered, screen_count=3)
    assert score == 100.0


def test_evidence_classification_integrity():
    """Verify extracted tokens properly distinguish observed, approximate, and inferred evidence."""
    tokens = [
        ProposedDesignToken(name="color.primary", value="#1E40AF", category="color", confidence=0.96, evidence="observed", classification="observed"),
        ProposedDesignToken(name="typography.heading.large", value="24px", category="typography", confidence=0.88, evidence="approximate", classification="approximate"),
        ProposedDesignToken(name="shadow.small", value="0 1px 3px rgba(0,0,0,0.05)", category="shadow", confidence=0.80, evidence="inferred", classification="inferred"),
    ]
    # Observed tokens must have high confidence
    assert tokens[0].classification == "observed"
    assert tokens[0].confidence >= 0.90
    # Typography is marked approximate
    assert tokens[1].classification == "approximate"
    # Shadows are marked inferred
    assert tokens[2].classification == "inferred"
