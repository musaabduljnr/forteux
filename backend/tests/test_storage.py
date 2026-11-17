from uuid import UUID, uuid4
from urllib.parse import parse_qs, urlparse

import boto3
from botocore.config import Config

from app.core.auth import Principal, get_current_principal
from app.core.config import Settings
from app.db.models import Membership, Project, ScreenAsset, Tenant, User
from app.services.storage import S3Storage, get_storage


def test_presigned_urls_are_short_lived_and_constrain_object_content():
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="test-access-key",
        aws_secret_access_key="test-secret-key",
        config=Config(signature_version="s3v4"),
    )
    settings = Settings(
        app_env="test",
        aws_region="us-east-1",
        s3_bucket="private-test-bucket",
        s3_upload_ttl_seconds=120,
        s3_download_ttl_seconds=180,
    )
    storage = S3Storage(settings, client)

    upload = urlparse(storage.presign_upload("tenant/project/image", "image/png", 1024))
    download = urlparse(storage.presign_download("tenant/project/image", 'screen"one.png'))

    assert upload.scheme == "https"
    upload_query = parse_qs(upload.query)
    download_query = parse_qs(download.query)
    assert upload_query.get("X-Amz-Expires", upload_query.get("Expires")) == ["120"]
    signed_headers = set(upload_query.get("X-Amz-SignedHeaders", [""])[0].split(";"))
    assert {"content-length", "content-type", "host"}.issubset(signed_headers)
    assert download.scheme == "https"
    assert download_query.get("X-Amz-Expires", download_query.get("Expires")) == ["180"]
    assert download_query["response-content-type"] == ["application/octet-stream"]


def test_s3_storage_supports_minio_endpoint(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "minioadmin")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
    settings = Settings(
        app_env="development",
        aws_region="us-east-1",
        s3_bucket="forteux-private-screenshots",
        s3_endpoint_url="http://localhost:9000",
    )
    storage = S3Storage(settings)
    assert storage.settings.s3_endpoint_url == "http://localhost:9000"
    assert storage.bucket == "forteux-private-screenshots"
    url = storage.presign_upload("tenant/project/image", "image/png", 2048)
    assert "http://localhost:9000" in url
    assert "forteux-private-screenshots" in url


def test_authenticated_asset_upload_retrieval_and_deletion(client, db_session):
    user = User(oidc_issuer="issuer", oidc_subject=f"subject-{uuid4()}")
    tenant = Tenant(name="Private workspace")
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(Membership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    project = Project(tenant_id=tenant.id, name="Private project", created_by=user.id)
    db_session.add(project)
    db_session.commit()
    principal = Principal(id=user.id, tenant_id=tenant.id, issuer="issuer", subject=user.oidc_subject)

    class FakeStorage:
        def __init__(self):
            self.objects = {}
            self.deleted = []

        def presign_upload(self, key, content_type, size):
            return f"https://private.example.test/{key}?operation=put&size={size}&type={content_type}"

        def head(self, key):
            return self.objects[key]

        def presign_download(self, key, filename):
            assert filename == "screen.png"
            return f"https://private.example.test/{key}?operation=get"

        def delete(self, key):
            self.deleted.append(key)

    storage = FakeStorage()
    client.app.dependency_overrides[get_current_principal] = lambda: principal
    client.app.dependency_overrides[get_storage] = lambda: storage
    try:
        response = client.post(
            f"/api/v1/projects/{project.id}/uploads",
            headers={"Idempotency-Key": "screen-upload-001"},
            json={"filename": "../screen.png", "content_type": "image/png", "size": 1024},
        )
        assert response.status_code == 201
        asset_id = response.json()["asset_id"]
        asset = db_session.get(ScreenAsset, UUID(asset_id))
        assert asset is not None
        assert asset.status == "pending_upload"
        assert "screen.png" not in asset.object_key

        replay = client.post(
            f"/api/v1/projects/{project.id}/uploads",
            headers={"Idempotency-Key": "screen-upload-001"},
            json={"filename": "../screen.png", "content_type": "image/png", "size": 1024},
        )
        assert replay.status_code == 200
        assert replay.json()["asset_id"] == asset_id

        storage.objects[asset.object_key] = {"ContentLength": 1024, "ContentType": "image/png"}
        completed = client.post(f"/api/v1/projects/{project.id}/assets/{asset_id}/complete")
        assert completed.status_code == 200
        assert completed.json()["status"] == "uploaded_unverified"

        download = client.get(f"/api/v1/projects/{project.id}/assets/{asset_id}/download")
        assert download.status_code == 200
        assert "private.example.test" in download.json()["download_url"]

        deleted = client.delete(f"/api/v1/projects/{project.id}/assets/{asset_id}")
        assert deleted.status_code == 204
        db_session.refresh(asset)
        assert asset.status == "deleted"
        assert asset.object_key in storage.deleted
    finally:
        client.app.dependency_overrides.pop(get_current_principal, None)
        client.app.dependency_overrides.pop(get_storage, None)
