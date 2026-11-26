from datetime import datetime, timezone
from uuid import uuid4

from app.core.auth import Principal, get_current_principal
from app.db.models import (
    AnalysisJob,
    Audit,
    AuditScreen,
    Finding,
    Membership,
    Project,
    ScreenAsset,
    Tenant,
    User,
)


def _create_user_workspace(db_session, label: str) -> tuple[User, Tenant]:
    user = User(oidc_issuer="issuer", oidc_subject=f"{label}-{uuid4()}")
    tenant = Tenant(name=f"Workspace {label}")
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(Membership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    return user, tenant


def _add_screen_asset(db_session, tenant_id, project_id, user_id, name: str) -> ScreenAsset:
    asset = ScreenAsset(
        tenant_id=tenant_id,
        project_id=project_id,
        uploaded_by=user_id,
        object_key=f"tenants/{tenant_id}/projects/{project_id}/{uuid4()}.png",
        original_filename=name,
        declared_content_type="image/png",
        declared_size=1024,
        idempotency_key=f"idem-{uuid4()}",
        status="uploaded_verified",
    )
    db_session.add(asset)
    db_session.flush()
    return asset


def _seed_audit(
    db_session,
    *,
    tenant_id,
    project_id,
    user_id,
    name: str,
    audit_status: str,
    job_status: str,
    screen_count: int,
    finding_count: int,
    deleted_at=None,
) -> Audit:
    audit = Audit(
        tenant_id=tenant_id,
        project_id=project_id,
        created_by=user_id,
        name=name,
        mode="multi" if screen_count > 1 else "single",
        status=audit_status,
        deleted_at=deleted_at,
    )
    db_session.add(audit)
    db_session.flush()

    for idx in range(screen_count):
        asset = _add_screen_asset(db_session, tenant_id, project_id, user_id, f"screen-{idx}.png")
        db_session.add(
            AuditScreen(
                tenant_id=tenant_id,
                audit_id=audit.id,
                screen_asset_id=asset.id,
                sequence_index=idx,
                screen_label=f"Screen {idx + 1}",
            )
        )

    job = AnalysisJob(
        tenant_id=tenant_id,
        audit_id=audit.id,
        status=job_status,
        provider="deterministic",
        model="deterministic-v1",
    )
    db_session.add(job)
    db_session.flush()

    for idx in range(finding_count):
        db_session.add(
            Finding(
                tenant_id=tenant_id,
                audit_id=audit.id,
                analysis_job_id=job.id,
                title=f"Finding {idx + 1}",
                category="Visual hierarchy",
                severity="medium",
                confidence=0.85,
                description="Observed contrast issue",
                why_it_matters="Low contrast reduces legibility",
                recommended_fix="Increase contrast",
                evidence_type="observed",
                evidence="Button text contrast ratio below 4.5:1",
            )
        )

    db_session.commit()
    return audit


def test_dashboard_requires_authentication(client):
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401


def test_dashboard_scenario_a_fresh_user_sees_zeros(client, db_session):
    user, tenant = _create_user_workspace(db_session, "Fresh")
    client.app.dependency_overrides[get_current_principal] = lambda: Principal(
        id=user.id, tenant_id=tenant.id, issuer="issuer", subject="fresh"
    )
    try:
        res = client.get("/api/v1/dashboard/summary")
    finally:
        client.app.dependency_overrides.pop(get_current_principal, None)

    assert res.status_code == 200
    assert res.json() == {
        "total_audits": 0,
        "screens_analysed": 0,
        "issues_identified": 0,
        "total_projects": 0,
        "recent_audits": [],
        "recent_projects": [],
    }


def test_dashboard_scenario_b_genuine_user_data(client, db_session):
    user, tenant = _create_user_workspace(db_session, "Genuine")
    project = Project(tenant_id=tenant.id, name="Checkout Revamp", created_by=user.id)
    db_session.add(project)
    db_session.flush()
    audit = _seed_audit(
        db_session,
        tenant_id=tenant.id,
        project_id=project.id,
        user_id=user.id,
        name="Checkout Audit",
        audit_status="completed",
        job_status="completed",
        screen_count=2,
        finding_count=3,
    )

    client.app.dependency_overrides[get_current_principal] = lambda: Principal(
        id=user.id, tenant_id=tenant.id, issuer="issuer", subject="genuine"
    )
    try:
        res = client.get("/api/v1/dashboard/summary")
    finally:
        client.app.dependency_overrides.pop(get_current_principal, None)

    assert res.status_code == 200
    data = res.json()
    assert data["total_audits"] == 1
    assert data["screens_analysed"] == 2
    assert data["issues_identified"] == 3
    assert data["total_projects"] == 1
    assert len(data["recent_audits"]) == 1
    assert data["recent_audits"][0]["id"] == str(audit.id)
    assert data["recent_audits"][0]["project_name"] == "Checkout Revamp"
    assert data["recent_audits"][0]["screen_count"] == 2
    assert data["recent_audits"][0]["finding_count"] == 3
    assert len(data["recent_projects"]) == 1
    assert data["recent_projects"][0]["id"] == str(project.id)
    assert data["recent_projects"][0]["audit_count"] == 1


def test_dashboard_scenario_c_user_isolation(client, db_session):
    user_a, tenant_a = _create_user_workspace(db_session, "UserA")
    user_b, tenant_b = _create_user_workspace(db_session, "UserB")

    proj_a = Project(tenant_id=tenant_a.id, name="Alpha Project", created_by=user_a.id)
    proj_b = Project(tenant_id=tenant_b.id, name="Beta Secret Project", created_by=user_b.id)
    db_session.add_all([proj_a, proj_b])
    db_session.flush()

    _seed_audit(
        db_session,
        tenant_id=tenant_a.id,
        project_id=proj_a.id,
        user_id=user_a.id,
        name="Alpha Audit",
        audit_status="completed",
        job_status="completed",
        screen_count=1,
        finding_count=1,
    )
    _seed_audit(
        db_session,
        tenant_id=tenant_b.id,
        project_id=proj_b.id,
        user_id=user_b.id,
        name="Beta Secret Audit",
        audit_status="completed",
        job_status="completed",
        screen_count=4,
        finding_count=7,
    )

    client.app.dependency_overrides[get_current_principal] = lambda: Principal(
        id=user_a.id, tenant_id=tenant_a.id, issuer="issuer", subject="a"
    )
    try:
        res = client.get("/api/v1/dashboard/summary")
    finally:
        client.app.dependency_overrides.pop(get_current_principal, None)

    assert res.status_code == 200
    data = res.json()
    assert data["total_audits"] == 1
    assert data["screens_analysed"] == 1
    assert data["issues_identified"] == 1
    assert data["total_projects"] == 1
    assert [p["name"] for p in data["recent_projects"]] == ["Alpha Project"]
    assert [a["name"] for a in data["recent_audits"]] == ["Alpha Audit"]


def test_dashboard_scenario_d_failed_and_incomplete_audits_excluded_from_completed_metrics(client, db_session):
    user, tenant = _create_user_workspace(db_session, "FailedAudit")
    project = Project(tenant_id=tenant.id, name="Main Project", created_by=user.id)
    db_session.add(project)
    db_session.flush()

    _seed_audit(
        db_session,
        tenant_id=tenant.id,
        project_id=project.id,
        user_id=user.id,
        name="Completed Audit",
        audit_status="completed",
        job_status="completed",
        screen_count=1,
        finding_count=2,
    )
    _seed_audit(
        db_session,
        tenant_id=tenant.id,
        project_id=project.id,
        user_id=user.id,
        name="Failed Audit",
        audit_status="failed",
        job_status="failed",
        screen_count=3,
        finding_count=5,
    )
    _seed_audit(
        db_session,
        tenant_id=tenant.id,
        project_id=project.id,
        user_id=user.id,
        name="Draft Audit",
        audit_status="draft",
        job_status="pending",
        screen_count=2,
        finding_count=0,
    )

    client.app.dependency_overrides[get_current_principal] = lambda: Principal(
        id=user.id, tenant_id=tenant.id, issuer="issuer", subject="failed"
    )
    try:
        res = client.get("/api/v1/dashboard/summary")
    finally:
        client.app.dependency_overrides.pop(get_current_principal, None)

    assert res.status_code == 200
    data = res.json()
    assert data["total_audits"] == 3
    assert data["screens_analysed"] == 1
    assert data["issues_identified"] == 2


def test_dashboard_scenario_e_deleted_records_excluded(client, db_session):
    user, tenant = _create_user_workspace(db_session, "Deleted")
    active_proj = Project(tenant_id=tenant.id, name="Active Project", created_by=user.id)
    deleted_proj = Project(
        tenant_id=tenant.id,
        name="Deleted Project",
        created_by=user.id,
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add_all([active_proj, deleted_proj])
    db_session.flush()

    _seed_audit(
        db_session,
        tenant_id=tenant.id,
        project_id=active_proj.id,
        user_id=user.id,
        name="Active Audit",
        audit_status="completed",
        job_status="completed",
        screen_count=1,
        finding_count=2,
    )
    _seed_audit(
        db_session,
        tenant_id=tenant.id,
        project_id=active_proj.id,
        user_id=user.id,
        name="Deleted Audit",
        audit_status="completed",
        job_status="completed",
        screen_count=4,
        finding_count=6,
        deleted_at=datetime.now(timezone.utc),
    )
    _seed_audit(
        db_session,
        tenant_id=tenant.id,
        project_id=deleted_proj.id,
        user_id=user.id,
        name="Orphaned Audit In Deleted Project",
        audit_status="completed",
        job_status="completed",
        screen_count=2,
        finding_count=3,
    )

    client.app.dependency_overrides[get_current_principal] = lambda: Principal(
        id=user.id, tenant_id=tenant.id, issuer="issuer", subject="deleted"
    )
    try:
        res = client.get("/api/v1/dashboard/summary")
    finally:
        client.app.dependency_overrides.pop(get_current_principal, None)

    assert res.status_code == 200
    data = res.json()
    assert data["total_projects"] == 1
    assert data["total_audits"] == 1
    assert data["screens_analysed"] == 1
    assert data["issues_identified"] == 2
    assert [a["name"] for a in data["recent_audits"]] == ["Active Audit"]
    assert [p["name"] for p in data["recent_projects"]] == ["Active Project"]
