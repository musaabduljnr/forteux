from uuid import UUID, uuid4

from app.core.auth import Principal, get_current_principal
from app.db.models import Membership, Project, Tenant, User


def _create_workspace(db_session, name: str):
    user = User(oidc_issuer="issuer", oidc_subject=f"{name}-{uuid4()}")
    tenant = Tenant(name=name)
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(Membership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    project = Project(tenant_id=tenant.id, name=f"{name} project", created_by=user.id)
    db_session.add(project)
    db_session.commit()
    return user, tenant, project


def test_project_queries_are_tenant_isolated(client, db_session):
    user_a, tenant_a, project_a = _create_workspace(db_session, "A")
    _user_b, _tenant_b, project_b = _create_workspace(db_session, "B")
    client.app.dependency_overrides[get_current_principal] = lambda: Principal(
        id=user_a.id,
        tenant_id=tenant_a.id,
        issuer="issuer",
        subject="subject",
    )
    try:
        listed = client.get("/api/v1/projects")
        hidden = client.get(f"/api/v1/projects/{project_b.id}")
    finally:
        client.app.dependency_overrides.pop(get_current_principal, None)

    assert listed.status_code == 200
    assert [project["id"] for project in listed.json()] == [str(project_a.id)]
    assert hidden.status_code == 404


def test_project_creation_uses_authenticated_owner(client, db_session):
    user, tenant, _project = _create_workspace(db_session, "Owner")
    client.app.dependency_overrides[get_current_principal] = lambda: Principal(
        id=user.id,
        tenant_id=tenant.id,
        issuer="issuer",
        subject="subject",
    )
    try:
        response = client.post("/api/v1/projects", json={"name": " New project "})
    finally:
        client.app.dependency_overrides.pop(get_current_principal, None)

    assert response.status_code == 201
    created = db_session.get(Project, UUID(response.json()["id"]))
    assert created is not None
    assert created.tenant_id == tenant.id
    assert created.created_by == user.id
    assert created.name == "New project"
