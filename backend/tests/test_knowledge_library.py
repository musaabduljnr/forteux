import hashlib
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
    AuditPrompt,
    AuditScreen,
    DeletionTask,
    DocumentVersion,
    Finding,
    FindingEvidence,
    KnowledgeChunk,
    KnowledgeDocument,
    Membership,
    Project,
    ScreenAsset,
    Tenant,
    User,
    utc_now,
)
from app.services.document_chunker import DocumentChunker
from app.services.document_extractor import DocumentExtractor, ExtractedPage
from app.services.embedding import DeterministicEmbeddingProvider, cosine_similarity
from app.services.knowledge_pipeline import KnowledgePipeline
from app.services.knowledge_retrieval import KnowledgeRetrieval
from app.services.prompt_generator import StitchPromptGenerator
from app.services.storage import get_storage


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------


def create_minimal_pdf_bytes(text: str = "Brand Typography Guidelines: Use Inter 16px.") -> bytes:
    """Create a syntactically valid PDF containing stream text."""
    stream_content = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET"
    stream_len = len(stream_content)
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>> endobj\n"
        b"4 0 obj <</Length " + str(stream_len).encode() + b">> stream\n"
        + stream_content.encode() + b"\nendstream\nendobj\n"
        b"5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000244 00000 n \n"
        b"0000000330 00000 n \n"
        b"trailer <</Size 6 /Root 1 0 R>>\nstartxref\n410\n%%EOF\n"
    )
    return pdf


def create_minimal_docx_bytes(paragraphs: list[str] | None = None) -> bytes:
    """Create a syntactically valid DOCX using python-docx."""
    import docx

    doc = docx.Document()
    doc.core_properties.title = "Design System Guidelines"
    for p in paragraphs or ["Typography Standards", "Use 8pt grid spacing across all containers."]:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class MockStorage:
    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}

    def head(self, key: str):
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


@pytest.fixture(autouse=True)
def mock_storage(client: TestClient):
    storage = MockStorage()
    client.app.dependency_overrides[get_storage] = lambda: storage
    yield storage
    client.app.dependency_overrides.pop(get_storage, None)


@pytest.fixture
def auth_headers(monkeypatch):
    settings = Settings(
        app_env="development",
        dev_auth_enabled=True,
        dev_auth_secret="test-secret-at-least-32-bytes-long-key",
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    token, _, _ = auth.issue_dev_token("dev@forteux.local", "Test Dev", settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tenant_and_user(client: TestClient, auth_headers):
    res = client.get("/api/v1/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    tenant_id = UUID(str(data["tenant_id"]))
    user_id = UUID(str(data["id"]))
    return tenant_id, user_id


@pytest.fixture
def project_id(client: TestClient, auth_headers, tenant_and_user) -> UUID:
    res = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"name": "Checkout App", "description": "Checkout redesign"},
    )
    assert res.status_code == 201
    return UUID(res.json()["id"])


# ---------------------------------------------------------------------------
# Unit Tests: Extractor, Chunker, Embeddings
# ---------------------------------------------------------------------------


def test_txt_extractor():
    extractor = DocumentExtractor()
    content = b"Header 1\n\nThis is paragraph one.\n\nThis is paragraph two."
    res = extractor.extract(content, "text/plain", "notes.txt")
    assert res.page_count == 1
    assert "paragraph one" in res.all_text


def test_pdf_extractor():
    extractor = DocumentExtractor()
    pdf_bytes = create_minimal_pdf_bytes("Button hierarchy guidelines")
    res = extractor.extract(pdf_bytes, "application/pdf", "brand.pdf")
    assert res.page_count >= 1
    assert res.extractor_version == "1.0.0"


def test_docx_extractor():
    extractor = DocumentExtractor()
    docx_bytes = create_minimal_docx_bytes(["Spacing Standards", "Always use 8px base units."])
    res = extractor.extract(
        docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "spacing.docx",
    )
    assert res.page_count == 1
    assert "8px base units" in res.all_text
    assert res.title == "Design System Guidelines"


def test_invalid_mime_type_raises():
    extractor = DocumentExtractor()
    with pytest.raises(Exception):
        extractor.extract(b"not an image", "image/png", "img.png")


def test_magic_byte_validation_pdf():
    extractor = DocumentExtractor()
    with pytest.raises(Exception) as exc:
        extractor.extract(b"NOT_A_PDF_CONTENT", "application/pdf", "doc.pdf")
    assert "missing %PDF header" in str(exc.value)


def test_magic_byte_validation_docx():
    extractor = DocumentExtractor()
    with pytest.raises(Exception) as exc:
        extractor.extract(
            b"NOT_A_ZIP_CONTENT",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc.docx",
        )
    assert "missing ZIP/PK header" in str(exc.value)


def test_empty_document_raises():
    extractor = DocumentExtractor()
    with pytest.raises(Exception):
        extractor.extract(b"", "text/plain", "empty.txt")


def test_chunker_preserves_page_references():
    chunker = DocumentChunker()
    pages = [
        ExtractedPage(page_num=1, text="Page 1: Typography rules.\n\nHeading 1\n\nUse 16px body.", char_count=50),
        ExtractedPage(page_num=2, text="Page 2: Color rules.\n\nPrimary action must be #0052CC.", char_count=55),
    ]
    chunks = chunker.chunk(pages, chunk_size=40, overlap=10, min_chunk=10)
    assert len(chunks) >= 2
    assert chunks[0].page_start == 1
    assert any(c.page_start == 2 for c in chunks)


def test_chunker_detects_headings():
    chunker = DocumentChunker()
    pages = [
        ExtractedPage(
            page_num=1,
            text="# COMPONENT STANDARDS\n\nAll buttons must have 8px border radius.\n\n# TYPOGRAPHY HIERARCHY\n\nHeadings must use font-weight 600.",
            char_count=120,
        )
    ]
    chunks = chunker.chunk(pages, chunk_size=300, min_chunk=20)
    assert len(chunks) >= 1
    assert chunks[0].section_heading is not None


def test_deterministic_embedding_provider():
    provider = DeterministicEmbeddingProvider(dimensions=768)
    texts = ["Primary button styling", "Primary button styling", "Different text"]
    embs = provider.embed(texts)
    assert len(embs) == 3
    assert len(embs[0]) == 768

    # Same text produces identical embeddings
    sim_identical = cosine_similarity(embs[0], embs[1])
    assert abs(sim_identical - 1.0) < 1e-5

    # Different text produces distinct embeddings
    sim_diff = cosine_similarity(embs[0], embs[2])
    assert sim_diff < 0.99


# ---------------------------------------------------------------------------
# API Integration Tests: Global Knowledge
# ---------------------------------------------------------------------------


def test_global_txt_upload_and_complete(client: TestClient, auth_headers, mock_storage, tenant_and_user):
    content = b"# DESIGN TOKENS\n\nPrimary color: #0052CC\n\nBorder radius: 8px for cards and buttons. Spacing base is 8px across containers."
    sha256 = hashlib.sha256(content).hexdigest()

    # 1. Upload intent
    upload_res = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={
            "filename": "design_tokens.md",
            "content_type": "text/markdown",
            "size": len(content),
            "scope": "global",
            "category": "Design Tokens",
        },
    )
    assert upload_res.status_code == 200
    intent = upload_res.json()
    doc_id = intent["document_id"]
    version_id = intent["version_id"]

    # 2. Put bytes into storage
    mock_storage.put_object(intent["object_key"], content, "text/markdown")

    # 3. Complete upload
    comp_res = client.post(
        f"/api/v1/knowledge/{doc_id}/complete",
        headers=auth_headers,
        json={"version_id": version_id, "sha256": sha256},
    )
    assert comp_res.status_code == 200
    doc_data = comp_res.json()
    assert doc_data["status"] == "ready"
    assert doc_data["scope"] == "global"
    assert doc_data["chunk_count"] >= 1
    assert doc_data["version_number"] == 1


def test_global_pdf_upload_and_complete(client: TestClient, auth_headers, mock_storage, tenant_and_user):
    pdf_bytes = create_minimal_pdf_bytes("Button hierarchy standards for design")
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    upload_res = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={
            "filename": "brand_guide.pdf",
            "content_type": "application/pdf",
            "size": len(pdf_bytes),
            "scope": "global",
            "category": "Brand",
        },
    )
    assert upload_res.status_code == 200
    intent = upload_res.json()
    mock_storage.put_object(intent["object_key"], pdf_bytes, "application/pdf")

    comp_res = client.post(
        f"/api/v1/knowledge/{intent['document_id']}/complete",
        headers=auth_headers,
        json={"version_id": intent["version_id"], "sha256": sha256},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "ready"


def test_file_too_large_rejected(client: TestClient, auth_headers, tenant_and_user):
    res = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={
            "filename": "huge.pdf",
            "content_type": "application/pdf",
            "size": 30 * 1024 * 1024,  # 30MB > 20MB limit
            "scope": "global",
        },
    )
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "file_too_large"


def test_unsupported_media_type_rejected(client: TestClient, auth_headers, tenant_and_user):
    res = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={
            "filename": "image.png",
            "content_type": "image/png",
            "size": 1024,
            "scope": "global",
        },
    )
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "unsupported_media_type"


def test_duplicate_document_name_conflict(client: TestClient, auth_headers, mock_storage, tenant_and_user):
    content = b"Sample text for duplicate filename test with enough length."
    client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={
            "filename": "unique_name.txt",
            "content_type": "text/plain",
            "size": len(content),
            "scope": "global",
        },
    )
    # Attempting to upload same filename in same scope gives 409
    res = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={
            "filename": "unique_name.txt",
            "content_type": "text/plain",
            "size": len(content),
            "scope": "global",
        },
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "duplicate_document_name"


def test_duplicate_content_sha256_conflict(client: TestClient, auth_headers, mock_storage, tenant_and_user):
    content = b"Unique content for duplicate testing: buttons must be 48px height across all surfaces."
    sha256 = hashlib.sha256(content).hexdigest()

    # Upload Doc 1
    res1 = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={"filename": "doc1.txt", "content_type": "text/plain", "size": len(content), "scope": "global"},
    )
    intent1 = res1.json()
    mock_storage.put_object(intent1["object_key"], content, "text/plain")
    c1 = client.post(
        f"/api/v1/knowledge/{intent1['document_id']}/complete",
        headers=auth_headers,
        json={"version_id": intent1["version_id"], "sha256": sha256},
    )
    assert c1.status_code == 200

    # Upload Doc 2 with different name but identical content
    res2 = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={"filename": "doc2.txt", "content_type": "text/plain", "size": len(content), "scope": "global"},
    )
    intent2 = res2.json()
    mock_storage.put_object(intent2["object_key"], content, "text/plain")
    comp_res2 = client.post(
        f"/api/v1/knowledge/{intent2['document_id']}/complete",
        headers=auth_headers,
        json={"version_id": intent2["version_id"], "sha256": sha256},
    )
    assert comp_res2.status_code == 409
    assert comp_res2.json()["error"]["code"] == "duplicate_document"


def test_global_knowledge_replace_version(client: TestClient, auth_headers, mock_storage, tenant_and_user):
    content_v1 = b"Version 1: Button border radius is 4px across all standard layouts."
    sha_v1 = hashlib.sha256(content_v1).hexdigest()

    res = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={"filename": "buttons.txt", "content_type": "text/plain", "size": len(content_v1), "scope": "global"},
    )
    intent = res.json()
    doc_id = intent["document_id"]
    mock_storage.put_object(intent["object_key"], content_v1, "text/plain")
    c1 = client.post(
        f"/api/v1/knowledge/{doc_id}/complete",
        headers=auth_headers,
        json={"version_id": intent["version_id"], "sha256": sha_v1},
    )
    assert c1.status_code == 200

    # Replace with Version 2
    content_v2 = b"Version 2: Updated Button border radius to 8px pill style globally."
    sha_v2 = hashlib.sha256(content_v2).hexdigest()

    replace_res = client.post(
        f"/api/v1/knowledge/{doc_id}/replace",
        headers=auth_headers,
        json={"filename": "buttons_v2.txt", "content_type": "text/plain", "size": len(content_v2), "scope": "global"},
    )
    assert replace_res.status_code == 200
    replace_intent = replace_res.json()
    assert replace_intent["version_number"] == 2

    mock_storage.put_object(replace_intent["object_key"], content_v2, "text/plain")
    complete_v2 = client.post(
        f"/api/v1/knowledge/{doc_id}/complete",
        headers=auth_headers,
        json={"version_id": replace_intent["version_id"], "sha256": sha_v2},
    )
    assert complete_v2.status_code == 200
    doc_data = complete_v2.json()
    assert doc_data["version_number"] == 2
    assert len(doc_data["versions"]) == 2


def test_global_knowledge_delete(client: TestClient, auth_headers, mock_storage, tenant_and_user, db_session):
    content = b"To be deleted: temporary design notes that will be removed soon."
    sha = hashlib.sha256(content).hexdigest()

    res = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={"filename": "temp_delete.txt", "content_type": "text/plain", "size": len(content), "scope": "global"},
    )
    intent = res.json()
    doc_id = intent["document_id"]
    mock_storage.put_object(intent["object_key"], content, "text/plain")
    comp = client.post(
        f"/api/v1/knowledge/{doc_id}/complete",
        headers=auth_headers,
        json={"version_id": intent["version_id"], "sha256": sha},
    )
    assert comp.status_code == 200

    # Verify chunks exist
    chunks_before = db_session.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == UUID(doc_id)).count()
    assert chunks_before >= 1

    # Delete
    del_res = client.delete(f"/api/v1/knowledge/{doc_id}", headers=auth_headers)
    assert del_res.status_code == 204

    # Verify chunks removed
    chunks_after = db_session.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == UUID(doc_id)).count()
    assert chunks_after == 0

    # Verify deletion task recorded
    task = db_session.query(DeletionTask).filter(DeletionTask.document_id == UUID(doc_id)).first()
    assert task is not None
    assert task.status == "completed"

    # Verify document no longer appears in list
    list_res = client.get("/api/v1/knowledge", headers=auth_headers)
    doc_ids = [d["id"] for d in list_res.json()]
    assert doc_id not in doc_ids


# ---------------------------------------------------------------------------
# Multi-Tenant & Cross-Project Isolation Tests
# ---------------------------------------------------------------------------


def test_cross_tenant_isolation(client: TestClient, auth_headers, mock_storage, db_session, tenant_and_user):
    tenant_a_id, user_a_id = tenant_and_user

    # Create Tenant B and User B
    tenant_b = Tenant(id=uuid4(), name="Tenant B", plan="personal")
    user_b = User(id=uuid4(), oidc_issuer="https://other.auth", oidc_subject="user-b", email="b@other.com")
    db_session.add_all([tenant_b, user_b])
    db_session.flush()
    db_session.add(Membership(tenant_id=tenant_b.id, user_id=user_b.id, role="owner"))

    # Upload document under Tenant B directly
    doc_b = KnowledgeDocument(
        id=uuid4(),
        tenant_id=tenant_b.id,
        scope="global",
        display_name="tenant_b_secret.txt",
        uploaded_by=user_b.id,
        status="ready",
    )
    db_session.add(doc_b)
    db_session.commit()

    # User A requests global knowledge list
    res = client.get("/api/v1/knowledge", headers=auth_headers)
    assert res.status_code == 200
    retrieved_ids = [d["id"] for d in res.json()]
    assert str(doc_b.id) not in retrieved_ids

    # User A requests Tenant B document detail -> 404
    detail_res = client.get(f"/api/v1/knowledge/{doc_b.id}", headers=auth_headers)
    assert detail_res.status_code == 404

    # User A tries to delete Tenant B document -> 404
    del_res = client.delete(f"/api/v1/knowledge/{doc_b.id}", headers=auth_headers)
    assert del_res.status_code == 404


def test_project_knowledge_cross_project_isolation(
    client: TestClient, auth_headers, mock_storage, tenant_and_user, project_id, db_session
):
    tenant_id, user_id = tenant_and_user
    # Create Project 2
    proj_2 = Project(id=uuid4(), tenant_id=tenant_id, name="Project 2", created_by=user_id)
    db_session.add(proj_2)
    db_session.commit()

    # Upload doc to Project 1
    content = b"Project 1 specific checkout flow guidelines and standards."
    sha = hashlib.sha256(content).hexdigest()
    res = client.post(
        f"/api/v1/projects/{project_id}/knowledge/upload",
        headers=auth_headers,
        json={"filename": "p1_guide.txt", "content_type": "text/plain", "size": len(content), "scope": "project"},
    )
    intent = res.json()
    mock_storage.put_object(intent["object_key"], content, "text/plain")
    c_res = client.post(
        f"/api/v1/projects/{project_id}/knowledge/{intent['document_id']}/complete",
        headers=auth_headers,
        json={"version_id": intent["version_id"], "sha256": sha},
    )
    assert c_res.status_code == 200

    # List Project 2 knowledge -> doc should NOT appear
    p2_res = client.get(f"/api/v1/projects/{proj_2.id}/knowledge", headers=auth_headers)
    assert p2_res.status_code == 200
    p2_doc_ids = [d["id"] for d in p2_res.json()]
    assert intent["document_id"] not in p2_doc_ids

    # Querying Project 1 doc with Project 2 path -> 404
    mismatch_res = client.get(
        f"/api/v1/projects/{proj_2.id}/knowledge/{intent['document_id']}",
        headers=auth_headers,
    )
    assert mismatch_res.status_code == 404


# ---------------------------------------------------------------------------
# Retrieval & Semantic Search Tests
# ---------------------------------------------------------------------------


def test_semantic_retrieval_and_search(client: TestClient, auth_headers, mock_storage, tenant_and_user):
    content = (
        "Button Visual Hierarchy and Sizing Guidelines.\n\n"
        "Primary action buttons should have a solid high-contrast background with 16px vertical padding.\n\n"
        "Secondary actions should use outline styles with 1px border. "
        "Never place two filled primary buttons in the same container."
    )
    sha = hashlib.sha256(content.encode()).hexdigest()

    res = client.post(
        "/api/v1/knowledge/upload",
        headers=auth_headers,
        json={
            "filename": "button_hierarchy.txt",
            "content_type": "text/plain",
            "size": len(content),
            "scope": "global",
            "category": "Buttons",
        },
    )
    intent = res.json()
    mock_storage.put_object(intent["object_key"], content.encode(), "text/plain")
    client.post(
        f"/api/v1/knowledge/{intent['document_id']}/complete",
        headers=auth_headers,
        json={"version_id": intent["version_id"], "sha256": sha},
    )

    # Search for button hierarchy
    search_res = client.post(
        "/api/v1/knowledge/search",
        headers=auth_headers,
        json={"query": "button visual hierarchy secondary actions", "top_k": 5},
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert "primary action buttons" in results[0]["text"].lower()
    assert results[0]["score"] > 0.2


def test_retrieval_excludes_unready_documents(client: TestClient, auth_headers, mock_storage, tenant_and_user, db_session):
    tenant_id, user_id = tenant_and_user
    # Insert a document stuck in 'extracting'
    doc = KnowledgeDocument(
        id=uuid4(),
        tenant_id=tenant_id,
        scope="global",
        display_name="unready_doc.txt",
        uploaded_by=user_id,
        status="extracting",
    )
    db_session.add(doc)
    db_session.commit()

    search_res = client.post(
        "/api/v1/knowledge/search",
        headers=auth_headers,
        json={"query": "unready", "top_k": 5},
    )
    assert search_res.status_code == 200
    doc_ids = [r["document_id"] for r in search_res.json()]
    assert str(doc.id) not in doc_ids


# ---------------------------------------------------------------------------
# RAG Integration Tests: Phase 04 Analysis & Phase 05 Prompt Generation
# ---------------------------------------------------------------------------


def test_audit_analysis_generates_citations(
    client: TestClient, auth_headers, mock_storage, tenant_and_user, project_id, db_session
):
    tenant_id, user_id = tenant_and_user

    # 1. Ingest a knowledge document
    content = b"Typography and visual hierarchy guidelines: Ensure clear contrast and headings across containers."
    sha = hashlib.sha256(content).hexdigest()
    res = client.post(
        f"/api/v1/projects/{project_id}/knowledge/upload",
        headers=auth_headers,
        json={"filename": "typography.txt", "content_type": "text/plain", "size": len(content), "scope": "project"},
    )
    intent = res.json()
    mock_storage.put_object(intent["object_key"], content, "text/plain")
    c_res = client.post(
        f"/api/v1/projects/{project_id}/knowledge/{intent['document_id']}/complete",
        headers=auth_headers,
        json={"version_id": intent["version_id"], "sha256": sha},
    )
    assert c_res.status_code == 200

    # 2. Setup screen asset and single-screen audit
    asset_id = uuid4()
    asset_key = f"{tenant_id}/{project_id}/screens/{asset_id}/original"
    img = Image.new("RGB", (1280, 800), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    mock_storage.put_object(asset_key, buf.getvalue(), "image/png")

    asset = ScreenAsset(
        id=asset_id,
        tenant_id=tenant_id,
        project_id=project_id,
        uploaded_by=user_id,
        object_key=asset_key,
        original_filename="screen.png",
        declared_content_type="image/png",
        declared_size=len(buf.getvalue()),
        idempotency_key=str(uuid4()),
        status="uploaded_verified",
        width_px=1280,
        height_px=800,
    )
    audit = Audit(
        id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        created_by=user_id,
        name="Checkout Audit",
        mode="single",
        status="draft",
    )
    db_session.add_all([asset, audit])
    db_session.flush()

    audit_screen = AuditScreen(
        id=uuid4(),
        tenant_id=tenant_id,
        audit_id=audit.id,
        screen_asset_id=asset.id,
        sequence_index=0,
    )
    db_session.add(audit_screen)
    db_session.commit()

    # 3. Trigger analysis
    analyze_res = client.post(
        f"/api/v1/projects/{project_id}/audits/{audit.id}/analyze",
        headers=auth_headers,
    )
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    findings = data["findings"]
    assert len(findings) >= 1

    # Check that finding evidence sources are populated from retrieved knowledge
    has_evidence = any(len(f.get("evidence_sources", [])) > 0 for f in findings)
    assert has_evidence, "At least one finding should have evidence sources attached from RAG retrieval"


def test_prompt_generation_includes_knowledge_references(
    client: TestClient, auth_headers, mock_storage, tenant_and_user, project_id, db_session
):
    tenant_id, user_id = tenant_and_user

    # 1. Ingest a knowledge document
    content = b"Design Token System: Use 8pt harmonic grid and #0052CC for primary actions."
    sha = hashlib.sha256(content).hexdigest()
    res = client.post(
        f"/api/v1/projects/{project_id}/knowledge/upload",
        headers=auth_headers,
        json={"filename": "tokens.txt", "content_type": "text/plain", "size": len(content), "scope": "project"},
    )
    intent = res.json()
    mock_storage.put_object(intent["object_key"], content, "text/plain")
    c_res = client.post(
        f"/api/v1/projects/{project_id}/knowledge/{intent['document_id']}/complete",
        headers=auth_headers,
        json={"version_id": intent["version_id"], "sha256": sha},
    )
    assert c_res.status_code == 200

    # 2. Setup screen asset and single-screen audit
    asset_id = uuid4()
    asset_key = f"{tenant_id}/{project_id}/screens/{asset_id}/original"
    img = Image.new("RGB", (1440, 900), color="navy")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    mock_storage.put_object(asset_key, buf.getvalue(), "image/png")

    asset = ScreenAsset(
        id=asset_id,
        tenant_id=tenant_id,
        project_id=project_id,
        uploaded_by=user_id,
        object_key=asset_key,
        original_filename="screen.png",
        declared_content_type="image/png",
        declared_size=len(buf.getvalue()),
        idempotency_key=str(uuid4()),
        status="uploaded_verified",
        width_px=1440,
        height_px=900,
    )
    audit = Audit(
        id=uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        created_by=user_id,
        name="Checkout Audit",
        mode="single",
        status="draft",
    )
    db_session.add_all([asset, audit])
    db_session.flush()

    audit_screen = AuditScreen(
        id=uuid4(),
        tenant_id=tenant_id,
        audit_id=audit.id,
        screen_asset_id=asset.id,
        sequence_index=0,
    )
    db_session.add(audit_screen)
    db_session.commit()

    # 3. Analyze screen
    analyze_res = client.post(
        f"/api/v1/projects/{project_id}/audits/{audit.id}/analyze",
        headers=auth_headers,
    )
    assert analyze_res.status_code == 200
    findings = analyze_res.json()["findings"]
    assert len(findings) >= 1
    selected_id = findings[0]["id"]

    # 4. Generate Stitch prompt
    prompt_res = client.post(
        f"/api/v1/projects/{project_id}/audits/{audit.id}/prompt",
        headers=auth_headers,
        json={"selected_finding_ids": [selected_id]},
    )
    assert prompt_res.status_code == 201
    prompt_content = prompt_res.json()["content"]
    assert "Applied Design References (Knowledge Base)" in prompt_content
    assert "tokens.txt" in prompt_content
