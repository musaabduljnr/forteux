"""Phase 09 Test Suite: Projects, Analysis History & Exports.

Covers:
1. Project extended lifecycle (update, archive, restore, soft-delete, stats, activity log)
2. Project ownership & multi-tenant isolation
3. Analysis version listing and historical comparison
4. Multi-format export engine (JSON, Markdown, CSV, ZIP packages) and download access
5. Cross-project paginated audit history with filters
6. Regression tests for previous phases
"""
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.core.config import Settings
from app.db.models import (
    AnalysisJob,
    Audit,
    AuditPrompt,
    AuditScreen,
    DesignSystemAnalysis,
    ExportJob,
    Finding,
    Membership,
    Project,
    ProjectActivityEvent,
    ScreenAsset,
    Tenant,
    User,
)


@pytest.fixture
def auth_headers(monkeypatch):
    settings = Settings(
        app_env="development",
        dev_auth_enabled=True,
        dev_auth_secret="test-secret-at-least-32-bytes-long-key",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    token, _, _ = auth.issue_dev_token("p9_user@forteux.local", "P9 User", settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_auth_headers(monkeypatch):
    settings = Settings(
        app_env="development",
        dev_auth_enabled=True,
        dev_auth_secret="test-secret-at-least-32-bytes-long-key",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    token, _, _ = auth.issue_dev_token("other_p9_user@forteux.local", "Other P9 User", settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_setup(client: TestClient, auth_headers: dict):
    res = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={
            "name": "Phase 09 Workspace",
            "description": "Comprehensive project management test",
            "category": "Fintech",
            "platform_type": "Mobile application",
            "context_text": "Consumer banking app",
        },
    )
    assert res.status_code == 201
    return res.json()


# ---------------------------------------------------------------------------
# Group 1: Project Management & Lifecycle
# ---------------------------------------------------------------------------


def test_project_update_fields(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    res = client.patch(
        f"/api/v1/projects/{pid}",
        headers=auth_headers,
        json={
            "name": "Updated Workspace Name",
            "description": "Updated description",
            "category": "E-commerce",
            "platform_type": "Web application",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Updated Workspace Name"
    assert data["description"] == "Updated description"
    assert data["category"] == "E-commerce"
    assert data["platform_type"] == "Web application"


def test_project_archive_restore(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    # Archive
    res = client.post(f"/api/v1/projects/{pid}/archive", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["archived_at"] is not None

    # Restore
    res2 = client.post(f"/api/v1/projects/{pid}/restore", headers=auth_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["archived_at"] is None


def test_project_soft_delete(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    del_res = client.delete(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert del_res.status_code == 204

    # Accessing deleted project returns 404
    get_res = client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert get_res.status_code == 404


def test_project_stats_empty(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    res = client.get(f"/api/v1/projects/{pid}/stats", headers=auth_headers)
    assert res.status_code == 200
    stats = res.json()
    assert stats["audit_count"] == 0
    assert stats["screen_count"] == 0
    assert stats["design_system_count"] == 0


def test_project_activity_logged_on_creation(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    res = client.get(f"/api/v1/projects/{pid}/activity", headers=auth_headers)
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 1
    assert any(e["event_type"] == "project_created" for e in events)


def test_project_archive_cross_user_blocked(client: TestClient, project_setup: dict, other_user_auth_headers: dict):
    pid = project_setup["id"]
    res = client.post(f"/api/v1/projects/{pid}/archive", headers=other_user_auth_headers)
    assert res.status_code == 404


def test_project_delete_cross_user_blocked(client: TestClient, project_setup: dict, other_user_auth_headers: dict):
    pid = project_setup["id"]
    res = client.delete(f"/api/v1/projects/{pid}", headers=other_user_auth_headers)
    assert res.status_code == 404


def test_project_update_cross_user_blocked(client: TestClient, project_setup: dict, other_user_auth_headers: dict):
    pid = project_setup["id"]
    res = client.patch(
        f"/api/v1/projects/{pid}",
        headers=other_user_auth_headers,
        json={"name": "Hacked Name"},
    )
    assert res.status_code == 404


def test_project_stats_counts_audits_and_screens(client: TestClient, auth_headers: dict, project_setup: dict, db_session):
    pid = UUID(project_setup["id"])
    project = db_session.get(Project, pid)

    audit = Audit(
        tenant_id=project.tenant_id,
        project_id=project.id,
        created_by=project.created_by,
        name="Stats Test Audit",
        mode="single",
        status="completed",
    )
    db_session.add(audit)
    db_session.commit()

    res = client.get(f"/api/v1/projects/{pid}/stats", headers=auth_headers)
    assert res.status_code == 200
    stats = res.json()
    assert stats["audit_count"] == 1


def test_project_activity_list_ordering(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    # Trigger multiple events
    client.patch(f"/api/v1/projects/{pid}", headers=auth_headers, json={"name": "Second Name"})
    client.post(f"/api/v1/projects/{pid}/archive", headers=auth_headers)

    res = client.get(f"/api/v1/projects/{pid}/activity", headers=auth_headers)
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 3
    # Check descending order
    dates = [e["created_at"] for e in events]
    assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# Group 2: Analysis Versioning & Comparison
# ---------------------------------------------------------------------------


def test_versions_empty_before_analysis(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    a_res = client.post(
        f"/api/v1/projects/{pid}/audits",
        headers=auth_headers,
        json={"name": "Version Test Audit", "mode": "single"},
    )
    aid = a_res.json()["id"]

    res = client.get(f"/api/v1/projects/{pid}/audits/{aid}/versions", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_versions_after_analysis_jobs(client: TestClient, auth_headers: dict, project_setup: dict, db_session):
    pid = UUID(project_setup["id"])
    project = db_session.get(Project, pid)

    audit = Audit(
        tenant_id=project.tenant_id,
        project_id=project.id,
        created_by=project.created_by,
        name="Multi Job Audit",
        mode="single",
        status="completed",
    )
    db_session.add(audit)
    db_session.flush()

    # Create two analysis jobs
    j1 = AnalysisJob(
        tenant_id=project.tenant_id,
        audit_id=audit.id,
        status="completed",
        provider="test-provider",
        model="test-model-v1",
        summary="Run 1 Summary",
    )
    j2 = AnalysisJob(
        tenant_id=project.tenant_id,
        audit_id=audit.id,
        status="completed",
        provider="test-provider",
        model="test-model-v2",
        summary="Run 2 Summary",
    )
    db_session.add_all([j1, j2])
    db_session.commit()

    res = client.get(f"/api/v1/projects/{pid}/audits/{audit.id}/versions", headers=auth_headers)
    assert res.status_code == 200
    versions = res.json()
    assert len(versions) == 2
    assert versions[0]["version_number"] == 1
    assert versions[1]["version_number"] == 2


def test_versions_comparison_missing_jobs(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    a_res = client.post(
        f"/api/v1/projects/{pid}/audits",
        headers=auth_headers,
        json={"name": "Comparison Audit", "mode": "single"},
    )
    aid = a_res.json()["id"]

    fake1 = uuid4()
    fake2 = uuid4()
    res = client.get(
        f"/api/v1/projects/{pid}/audits/{aid}/versions/compare?earlier_job_id={fake1}&later_job_id={fake2}",
        headers=auth_headers,
    )
    assert res.status_code == 404


def test_versions_comparison_same_job(client: TestClient, auth_headers: dict, project_setup: dict, db_session):
    pid = UUID(project_setup["id"])
    project = db_session.get(Project, pid)

    audit = Audit(
        tenant_id=project.tenant_id,
        project_id=project.id,
        created_by=project.created_by,
        name="Self Compare Audit",
        mode="single",
        status="completed",
    )
    db_session.add(audit)
    db_session.flush()

    job = AnalysisJob(
        tenant_id=project.tenant_id,
        audit_id=audit.id,
        status="completed",
        provider="test-provider",
        model="test-model-v1",
    )
    db_session.add(job)
    db_session.flush()

    finding = Finding(
        tenant_id=project.tenant_id,
        audit_id=audit.id,
        analysis_job_id=job.id,
        category="Accessibility",
        title="Contrast too low",
        description="Text contrast is below 4.5:1",
        why_it_matters="Difficult for visually impaired users",
        recommended_fix="Increase color darkness",
        severity="high",
        confidence=0.95,
        evidence_type="observed",
        evidence="Contrast ratio measured at 2.8:1",
    )
    db_session.add(finding)
    db_session.commit()

    res = client.get(
        f"/api/v1/projects/{pid}/audits/{audit.id}/versions/compare?earlier_job_id={job.id}&later_job_id={job.id}",
        headers=auth_headers,
    )
    assert res.status_code == 200
    comp = res.json()
    assert comp["earlier_finding_count"] == 1
    assert comp["later_finding_count"] == 1
    assert len(comp["persistent_findings"]) == 1
    assert len(comp["new_findings"]) == 0
    assert len(comp["resolved_findings"]) == 0
    assert len(comp["limitations"]) > 0


def test_versions_comparison_cross_audit_blocked(client: TestClient, auth_headers: dict, project_setup: dict, db_session):
    pid = UUID(project_setup["id"])
    project = db_session.get(Project, pid)

    a1 = Audit(tenant_id=project.tenant_id, project_id=project.id, created_by=project.created_by, name="A1", mode="single")
    a2 = Audit(tenant_id=project.tenant_id, project_id=project.id, created_by=project.created_by, name="A2", mode="single")
    db_session.add_all([a1, a2])
    db_session.flush()

    j1 = AnalysisJob(tenant_id=project.tenant_id, audit_id=a1.id, status="completed", provider="p", model="m")
    j2 = AnalysisJob(tenant_id=project.tenant_id, audit_id=a2.id, status="completed", provider="p", model="m")
    db_session.add_all([j1, j2])
    db_session.commit()

    res = client.get(
        f"/api/v1/projects/{pid}/audits/{a1.id}/versions/compare?earlier_job_id={j1.id}&later_job_id={j2.id}",
        headers=auth_headers,
    )
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Group 3: Exports
# ---------------------------------------------------------------------------


def test_export_create_json(client: TestClient, auth_headers: dict, project_setup: dict, db_session):
    pid = UUID(project_setup["id"])
    project = db_session.get(Project, pid)
    audit = Audit(tenant_id=project.tenant_id, project_id=project.id, created_by=project.created_by, name="Export Audit", mode="single")
    db_session.add(audit)
    db_session.commit()

    res = client.post(
        f"/api/v1/projects/{pid}/exports",
        headers=auth_headers,
        json={"export_type": "single_audit", "format": "json", "audit_id": str(audit.id)},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "completed"
    assert data["download_available"] is True
    assert data["format"] == "json"


def test_export_create_markdown(client: TestClient, auth_headers: dict, project_setup: dict, db_session):
    pid = UUID(project_setup["id"])
    project = db_session.get(Project, pid)
    audit = Audit(tenant_id=project.tenant_id, project_id=project.id, created_by=project.created_by, name="MD Export Audit", mode="single")
    db_session.add(audit)
    db_session.commit()

    res = client.post(
        f"/api/v1/projects/{pid}/exports",
        headers=auth_headers,
        json={"export_type": "single_audit", "format": "markdown", "audit_id": str(audit.id)},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "completed"
    assert data["format"] == "markdown"


def test_export_create_csv(client: TestClient, auth_headers: dict, project_setup: dict, db_session):
    pid = UUID(project_setup["id"])
    project = db_session.get(Project, pid)
    audit = Audit(tenant_id=project.tenant_id, project_id=project.id, created_by=project.created_by, name="CSV Export Audit", mode="single")
    db_session.add(audit)
    db_session.commit()

    res = client.post(
        f"/api/v1/projects/{pid}/exports",
        headers=auth_headers,
        json={"export_type": "single_audit", "format": "csv", "audit_id": str(audit.id)},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "completed"


def test_export_list(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    # Project package export does not require audit_id
    client.post(f"/api/v1/projects/{pid}/exports", headers=auth_headers, json={"export_type": "project_package", "format": "json"})
    client.post(f"/api/v1/projects/{pid}/exports", headers=auth_headers, json={"export_type": "project_package", "format": "markdown"})

    res = client.get(f"/api/v1/projects/{pid}/exports", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2


def test_export_get_single(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    post_res = client.post(
        f"/api/v1/projects/{pid}/exports",
        headers=auth_headers,
        json={"export_type": "project_package", "format": "json"},
    )
    eid = post_res.json()["id"]

    res = client.get(f"/api/v1/projects/{pid}/exports/{eid}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == eid
    assert res.json()["download_available"] is True


def test_export_download(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    post_res = client.post(
        f"/api/v1/projects/{pid}/exports",
        headers=auth_headers,
        json={"export_type": "project_package", "format": "markdown"},
    )
    eid = post_res.json()["id"]

    res = client.get(f"/api/v1/projects/{pid}/exports/{eid}/download", headers=auth_headers)
    assert res.status_code == 200
    assert "Project Summary" in res.text
    assert "attachment" in res.headers.get("content-disposition", "")


def test_export_cross_project_blocked(client: TestClient, project_setup: dict, other_user_auth_headers: dict):
    pid = project_setup["id"]
    res = client.get(f"/api/v1/projects/{pid}/exports", headers=other_user_auth_headers)
    assert res.status_code == 404


def test_export_requires_audit_id_for_audit_type(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    res = client.post(
        f"/api/v1/projects/{pid}/exports",
        headers=auth_headers,
        json={"export_type": "single_audit", "format": "json"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Group 4: Cross-Project History & Pagination
# ---------------------------------------------------------------------------


def test_history_endpoint_empty(client: TestClient, auth_headers: dict):
    res = client.get("/api/v1/projects/history", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_history_pagination(client: TestClient, auth_headers: dict, project_setup: dict, db_session):
    pid = UUID(project_setup["id"])
    project = db_session.get(Project, pid)

    for i in range(3):
        a = Audit(
            tenant_id=project.tenant_id,
            project_id=project.id,
            created_by=project.created_by,
            name=f"Page Audit {i}",
            mode="single",
        )
        db_session.add(a)
    db_session.commit()

    res = client.get("/api/v1/projects/history?page=1&page_size=2", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3
    assert data["page"] == 1


def test_history_filter_mode(client: TestClient, auth_headers: dict, project_setup: dict, db_session):
    pid = UUID(project_setup["id"])
    project = db_session.get(Project, pid)

    a1 = Audit(tenant_id=project.tenant_id, project_id=project.id, created_by=project.created_by, name="Single M", mode="single")
    a2 = Audit(tenant_id=project.tenant_id, project_id=project.id, created_by=project.created_by, name="Multi M", mode="multi")
    db_session.add_all([a1, a2])
    db_session.commit()

    res = client.get("/api/v1/projects/history?mode=multi", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert all(item["mode"] == "multi" for item in data["items"])


def test_history_sorting(client: TestClient, auth_headers: dict):
    res_newest = client.get("/api/v1/projects/history?sort=newest", headers=auth_headers)
    res_oldest = client.get("/api/v1/projects/history?sort=oldest", headers=auth_headers)
    assert res_newest.status_code == 200
    assert res_oldest.status_code == 200


# ---------------------------------------------------------------------------
# Group 5: Regression & Extended Smoke Tests
# ---------------------------------------------------------------------------


def test_regression_create_project_still_works(client: TestClient, auth_headers: dict):
    res = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"name": "Classic Project", "description": "Legacy format"},
    )
    assert res.status_code == 201
    assert res.json()["name"] == "Classic Project"


def test_regression_create_audit_still_works(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    res = client.post(
        f"/api/v1/projects/{pid}/audits",
        headers=auth_headers,
        json={"name": "Legacy Audit", "mode": "single"},
    )
    assert res.status_code == 201
    assert res.json()["name"] == "Legacy Audit"


def test_regression_list_audits_still_works(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    res = client.get(f"/api/v1/projects/{pid}/audits", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_regression_design_system_endpoint_accessible(client: TestClient, auth_headers: dict, project_setup: dict):
    pid = project_setup["id"]
    res = client.get(f"/api/v1/projects/{pid}/design-systems", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
