import json
import re
from datetime import datetime, timezone
from pathlib import PurePath
from uuid import UUID, uuid4

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    AnalysisJobRead,
    AnalysisResponse,
    AssetDownloadRead,
    AssetRead,
    AuditContextUpdate,
    AuditCreate,
    AuditRead,
    AuditScreenCreate,
    AuditScreenRead,
    AuditScreenReorderRequest,
    AuditScreenUpdate,
    BoundingBoxRead,
    DevTokenRequest,
    DevTokenResponse,
    DocumentVersionRead,
    FindingEvidenceRead,
    FindingRead,
    FlowReportRead,
    FrictionPointRead,
    JourneyReportRead,
    JourneyStrengthRead,
    KnowledgeCompleteRequest,
    KnowledgeDocumentRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    KnowledgeUploadIntentRead,
    KnowledgeUploadIntentRequest,
    MultiScreenAnalysisResponse,
    MultiScreenBoundingBoxRead,
    MultiScreenFindingRead,
    ProjectCreate,
    ProjectRead,
    PromptGenerateRequest,
    PromptRead,
    PromptUpdateRequest,
    PromptVersionRead,
    UploadIntentRead,
    UploadRequest,
)
from app.core.auth import Principal, get_current_principal, issue_dev_token
from app.core.config import get_settings
from app.db.models import (
    AnalysisJob,
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
    PromptVersion,
    ScreenAsset,
)
from app.db.session import get_db
from app.services.ai_vision import AIVisionService, get_vision_service
from app.services.document_extractor import SUPPORTED_MIME_TYPES
from app.services.image import ImageValidationError, validate_and_process_image
from app.services.knowledge_pipeline import KnowledgePipeline
from app.services.knowledge_retrieval import KnowledgeRetrieval
from app.services.multi_screen_vision import (
    MultiScreenAIVisionService,
    ScreenContext,
    get_multi_screen_vision_service,
)
from app.services.prompt_generator import StitchPromptGenerator
from app.services.storage import S3Storage, get_storage

router = APIRouter()


@router.post("/auth/dev-token", response_model=DevTokenResponse)
def create_dev_token(body: DevTokenRequest) -> DevTokenResponse:
    settings = get_settings()
    if settings.app_env == "production" or not settings.dev_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "dev_auth_disabled", "message": "Development authentication is disabled"},
        )
    token, expires_in, subject = issue_dev_token(body.email, body.name, settings)
    return DevTokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=expires_in,
        user_id=subject,
        email=body.email.strip(),
        name=body.name.strip(),
    )


def _project_or_404(db: Session, project_id: UUID, principal: Principal) -> Project:
    project = db.scalar(
        select(Project)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(
            Project.id == project_id,
            Project.deleted_at.is_(None),
            Membership.user_id == principal.id,
            Membership.tenant_id == principal.tenant_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found", "message": "Project not found"})
    return project


def _safe_filename(filename: str) -> str:
    basename = PurePath(filename.replace("\\", "/")).name
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", basename).strip()
    if not cleaned or cleaned in {".", ".."}:
        raise HTTPException(status_code=422, detail={"code": "invalid_filename", "message": "Provide a valid filename"})
    return cleaned[:255]


@router.get("/me")
def read_current_user(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    from app.db.models import User

    user = db.get(User, principal.id)
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "user_not_found", "message": "User not found"})
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "tenant_id": principal.tenant_id}


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .join(Membership, Membership.tenant_id == Project.tenant_id)
            .where(
                Project.deleted_at.is_(None),
                Membership.user_id == principal.id,
                Membership.tenant_id == principal.tenant_id,
            )
            .order_by(Project.updated_at.desc())
        )
    )


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Project:
    project = Project(
        tenant_id=principal.tenant_id,
        name=body.name,
        description=body.description,
        created_by=principal.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Project:
    return _project_or_404(db, project_id, principal)


@router.post("/projects/{project_id}/audits", response_model=AuditRead, status_code=status.HTTP_201_CREATED)
def create_audit(
    project_id: UUID,
    body: AuditCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Audit:
    project = _project_or_404(db, project_id, principal)
    audit = Audit(
        tenant_id=principal.tenant_id,
        project_id=project.id,
        created_by=principal.id,
        name=body.name,
        mode=body.mode,
        status="draft",
        context_json=json.dumps(body.context),
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


@router.get("/projects/{project_id}/audits/{audit_id}", response_model=AuditRead)
def read_audit(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Audit:
    _project_or_404(db, project_id, principal)
    audit = db.scalar(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.project_id == project_id,
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
        )
    )
    if audit is None:
        raise HTTPException(status_code=404, detail={"code": "audit_not_found", "message": "Audit not found"})
    return audit


@router.get("/projects/{project_id}/audits", response_model=list[AuditRead])
def list_audits(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[Audit]:
    _project_or_404(db, project_id, principal)
    return list(
        db.scalars(
            select(Audit)
            .where(
                Audit.project_id == project_id,
                Audit.tenant_id == principal.tenant_id,
                Audit.deleted_at.is_(None),
            )
            .order_by(Audit.created_at.desc())
        )
    )


@router.post("/projects/{project_id}/uploads", response_model=UploadIntentRead, status_code=201)
def initiate_upload(
    project_id: UUID,
    body: UploadRequest,
    response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> UploadIntentRead:
    project = _project_or_404(db, project_id, principal)
    data = body
    settings = get_settings()
    if data.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail={"code": "upload_too_large", "message": "The screenshot exceeds the 10 MB limit"})

    filename = _safe_filename(data.filename)
    extension = PurePath(filename).suffix.lower()
    expected_extensions = {"image/png": {".png"}, "image/jpeg": {".jpg", ".jpeg"}}
    if extension not in expected_extensions[data.content_type]:
        raise HTTPException(status_code=415, detail={"code": "type_extension_mismatch", "message": "The file extension does not match the selected image type"})

    existing = db.scalar(
        select(ScreenAsset).where(
            ScreenAsset.uploaded_by == principal.id,
            ScreenAsset.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.project_id != project.id or existing.deleted_at is not None:
            raise HTTPException(status_code=409, detail={"code": "idempotency_conflict", "message": "This request key has already been used"})
        if (
            existing.original_filename != filename
            or existing.declared_content_type != data.content_type
            or existing.declared_size != data.size
        ):
            raise HTTPException(status_code=409, detail={"code": "idempotency_conflict", "message": "The request key does not match the original upload"})
        if existing.status != "pending_upload":
            raise HTTPException(status_code=409, detail={"code": "upload_already_completed", "message": "This upload has already been completed"})
        try:
            url = storage.presign_upload(existing.object_key, existing.declared_content_type, existing.declared_size)
        except (BotoCoreError, ClientError) as error:
            raise HTTPException(status_code=503, detail={"code": "storage_unavailable", "message": "Upload storage is temporarily unavailable"}) from error
        response.status_code = 200
        return UploadIntentRead(
            asset_id=existing.id,
            upload_url=url,
            required_headers={
                "Content-Type": existing.declared_content_type,
            },
            expires_in_seconds=settings.s3_upload_ttl_seconds,
        )

    asset_id = uuid4()
    object_key = f"{principal.tenant_id}/{project.id}/screens/{asset_id}/original"
    asset = ScreenAsset(
        id=asset_id,
        tenant_id=principal.tenant_id,
        project_id=project.id,
        uploaded_by=principal.id,
        object_key=object_key,
        original_filename=filename,
        declared_content_type=data.content_type,
        declared_size=data.size,
        idempotency_key=idempotency_key,
        status="pending_upload",
    )
    db.add(asset)
    try:
        db.flush()
        url = storage.presign_upload(object_key, data.content_type, data.size)
        db.commit()
    except (BotoCoreError, ClientError) as error:
        db.rollback()
        raise HTTPException(status_code=503, detail={"code": "storage_unavailable", "message": "Upload storage is temporarily unavailable"}) from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "idempotency_conflict", "message": "This upload request was already submitted"}) from error

    return UploadIntentRead(
        asset_id=asset_id,
        upload_url=url,
        required_headers={"Content-Type": data.content_type},
        expires_in_seconds=settings.s3_upload_ttl_seconds,
    )


@router.post("/projects/{project_id}/assets/{asset_id}/complete", response_model=AssetRead)
def complete_upload(
    project_id: UUID,
    asset_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> ScreenAsset:
    project = _project_or_404(db, project_id, principal)
    asset = db.scalar(
        select(ScreenAsset).where(
            ScreenAsset.id == asset_id,
            ScreenAsset.project_id == project.id,
            ScreenAsset.tenant_id == principal.tenant_id,
            ScreenAsset.deleted_at.is_(None),
        )
    )
    if asset is None:
        raise HTTPException(status_code=404, detail={"code": "asset_not_found", "message": "Screenshot asset not found"})
    if asset.status in {"uploaded_verified", "uploaded_unverified"}:
        return asset
    if asset.status != "pending_upload":
        raise HTTPException(status_code=409, detail={"code": "invalid_asset_state", "message": "This asset cannot be completed"})
    try:
        metadata = storage.head(asset.object_key)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code in {"404", "NoSuchKey", "NotFound"}:
            raise HTTPException(status_code=409, detail={"code": "upload_missing", "message": "The uploaded object was not found"}) from error
        raise HTTPException(status_code=503, detail={"code": "storage_unavailable", "message": "Upload storage is temporarily unavailable"}) from error
    except BotoCoreError as error:
        raise HTTPException(status_code=503, detail={"code": "storage_unavailable", "message": "Upload storage is temporarily unavailable"}) from error
    if metadata.get("ContentLength") != asset.declared_size:
        raise HTTPException(status_code=422, detail={"code": "upload_size_mismatch", "message": "Uploaded object size does not match the request"})
    if metadata.get("ContentType") != asset.declared_content_type:
        raise HTTPException(status_code=422, detail={"code": "upload_type_mismatch", "message": "Uploaded object type does not match the request"})

    # Download raw image bytes from storage to validate signatures, extract dimensions and orientation
    if hasattr(storage, "get_object"):
        try:
            raw_bytes = storage.get_object(asset.object_key)
            img_meta = validate_and_process_image(raw_bytes, asset.declared_content_type)
            if img_meta.normalized_bytes != raw_bytes and hasattr(storage, "put_object"):
                storage.put_object(asset.object_key, img_meta.normalized_bytes, asset.declared_content_type)
            asset.width_px = img_meta.width
            asset.height_px = img_meta.height
            asset.orientation = img_meta.orientation
            asset.sha256 = img_meta.sha256
            asset.verified_mime_type = img_meta.mime_type
            asset.status = "uploaded_verified"
        except ImageValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": error.code, "message": error.message},
            ) from error
        except Exception:
            asset.status = "uploaded_unverified"
    else:
        asset.status = "uploaded_unverified"

    asset.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/projects/{project_id}/assets", response_model=list[AssetRead])
def list_assets(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ScreenAsset]:
    _project_or_404(db, project_id, principal)
    return list(
        db.scalars(
            select(ScreenAsset)
            .where(
                ScreenAsset.project_id == project_id,
                ScreenAsset.tenant_id == principal.tenant_id,
                ScreenAsset.deleted_at.is_(None),
            )
            .order_by(ScreenAsset.created_at.desc())
        )
    )


@router.get("/projects/{project_id}/assets/{asset_id}/download", response_model=AssetDownloadRead)
def get_download_url(
    project_id: UUID,
    asset_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> AssetDownloadRead:
    project = _project_or_404(db, project_id, principal)
    asset = db.scalar(
        select(ScreenAsset).where(
            ScreenAsset.id == asset_id,
            ScreenAsset.project_id == project.id,
            ScreenAsset.tenant_id == principal.tenant_id,
            ScreenAsset.deleted_at.is_(None),
            ScreenAsset.status.in_(["uploaded_unverified", "uploaded_verified"]),
        )
    )
    if asset is None:
        raise HTTPException(status_code=404, detail={"code": "asset_not_found", "message": "Screenshot asset not found"})
    try:
        url = storage.presign_download(asset.object_key, asset.original_filename)
    except (BotoCoreError, ClientError) as error:
        raise HTTPException(status_code=503, detail={"code": "storage_unavailable", "message": "Upload storage is temporarily unavailable"}) from error
    return AssetDownloadRead(
        asset_id=asset.id,
        download_url=url,
        expires_in_seconds=get_settings().s3_download_ttl_seconds,
    )


@router.delete("/projects/{project_id}/assets/{asset_id}", status_code=204)
def delete_asset(
    project_id: UUID,
    asset_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
    storage: S3Storage = Depends(get_storage),
) -> Response:
    project = _project_or_404(db, project_id, principal)
    asset = db.scalar(
        select(ScreenAsset).where(
            ScreenAsset.id == asset_id,
            ScreenAsset.project_id == project.id,
            ScreenAsset.tenant_id == principal.tenant_id,
            ScreenAsset.deleted_at.is_(None),
        )
    )
    if asset is None:
        raise HTTPException(status_code=404, detail={"code": "asset_not_found", "message": "Screenshot asset not found"})
    asset.status = "deleting"
    db.commit()
    try:
        storage.delete(asset.object_key)
    except (BotoCoreError, ClientError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail={"code": "storage_delete_failed", "message": "The asset is inaccessible but cleanup must be retried"}) from error
    asset.status = "deleted"
    asset.deleted_at = datetime.now(timezone.utc)
    asset.updated_at = asset.deleted_at
    db.commit()
    return Response(status_code=204)


@router.post("/projects/{project_id}/audits/{audit_id}/screens", response_model=AuditScreenRead, status_code=status.HTTP_201_CREATED)
def attach_screen_to_audit(
    project_id: UUID,
    audit_id: UUID,
    body: AuditScreenCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> AuditScreenRead:
    _project_or_404(db, project_id, principal)
    audit = db.scalar(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.project_id == project_id,
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
        )
    )
    if audit is None:
        raise HTTPException(status_code=404, detail={"code": "audit_not_found", "message": "Audit not found"})

    asset = db.scalar(
        select(ScreenAsset).where(
            ScreenAsset.id == body.screen_asset_id,
            ScreenAsset.project_id == project_id,
            ScreenAsset.tenant_id == principal.tenant_id,
            ScreenAsset.deleted_at.is_(None),
        )
    )
    if asset is None:
        raise HTTPException(status_code=404, detail={"code": "asset_not_found", "message": "Screen asset not found"})

    if audit.mode == "single":
        existing = db.scalar(select(AuditScreen).where(AuditScreen.audit_id == audit.id))
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail={"code": "single_screen_limit", "message": "Single screen audits can only have one screenshot"},
            )

    screen = AuditScreen(
        tenant_id=principal.tenant_id,
        audit_id=audit.id,
        screen_asset_id=asset.id,
        sequence_index=body.sequence_index,
        screen_label=body.screen_label,
    )
    db.add(screen)
    db.commit()
    db.refresh(screen)

    download_url = None
    try:
        download_url = storage.presign_download(asset.object_key, asset.original_filename)
    except Exception:
        pass

    return AuditScreenRead(
        id=screen.id,
        audit_id=screen.audit_id,
        screen_asset_id=screen.screen_asset_id,
        sequence_index=screen.sequence_index,
        screen_label=screen.screen_label,
        screen_description=screen.screen_description,
        width_px=asset.width_px,
        height_px=asset.height_px,
        download_url=download_url,
        created_at=screen.created_at,
    )


@router.get("/projects/{project_id}/audits/{audit_id}/screens", response_model=list[AuditScreenRead])
def list_audit_screens(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> list[AuditScreenRead]:
    _project_or_404(db, project_id, principal)
    screens = list(
        db.scalars(
            select(AuditScreen)
            .where(AuditScreen.audit_id == audit_id, AuditScreen.tenant_id == principal.tenant_id)
            .order_by(AuditScreen.sequence_index.asc())
        )
    )
    results: list[AuditScreenRead] = []
    for s in screens:
        asset = db.get(ScreenAsset, s.screen_asset_id)
        download_url = None
        if asset:
            try:
                download_url = storage.presign_download(asset.object_key, asset.original_filename)
            except Exception:
                pass
        results.append(
            AuditScreenRead(
                id=s.id,
                audit_id=s.audit_id,
                screen_asset_id=s.screen_asset_id,
                sequence_index=s.sequence_index,
                screen_label=s.screen_label,
                screen_description=s.screen_description,
                width_px=asset.width_px if asset else None,
                height_px=asset.height_px if asset else None,
                download_url=download_url,
                created_at=s.created_at,
            )
        )
    return results


@router.post("/projects/{project_id}/audits/{audit_id}/analyze", response_model=AnalysisResponse)
def analyze_audit_screen(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
    vision: AIVisionService = Depends(get_vision_service),
) -> AnalysisResponse:
    _project_or_404(db, project_id, principal)
    audit = db.scalar(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.project_id == project_id,
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
        )
    )
    if audit is None:
        raise HTTPException(status_code=404, detail={"code": "audit_not_found", "message": "Audit not found"})

    if audit.mode != "single":
        raise HTTPException(
            status_code=400,
            detail={"code": "unsupported_audit_mode", "message": "This endpoint only supports single-screen audits"},
        )

    audit_screen = db.scalar(
        select(AuditScreen)
        .where(AuditScreen.audit_id == audit.id, AuditScreen.tenant_id == principal.tenant_id)
        .order_by(AuditScreen.sequence_index.asc())
    )
    if audit_screen is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "no_screenshot_attached", "message": "No screenshot attached to this audit"},
        )

    asset = db.get(ScreenAsset, audit_screen.screen_asset_id)
    if asset is None or asset.deleted_at is not None:
        raise HTTPException(
            status_code=404,
            detail={"code": "asset_not_found", "message": "Screen asset could not be found"},
        )

    try:
        image_bytes = storage.get_object(asset.object_key)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "storage_unavailable", "message": "Failed to retrieve screenshot from storage"},
        ) from error

    width = asset.width_px or 1280
    height = asset.height_px or 800
    if not asset.width_px or not asset.height_px:
        try:
            img_meta = validate_and_process_image(image_bytes, asset.declared_content_type)
            width = img_meta.width
            height = img_meta.height
            asset.width_px = width
            asset.height_px = height
            db.commit()
        except Exception:
            pass

    job = AnalysisJob(
        tenant_id=principal.tenant_id,
        audit_id=audit.id,
        screen_asset_id=asset.id,
        status="processing",
        provider="forteux-vision-engine",
        model="deterministic-cv-v1",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    db.query(Finding).where(Finding.audit_id == audit.id).delete()

    try:
        context_dict = json.loads(audit.context_json or "{}") if audit.context_json else {}
        analysis_result = vision.analyze_screenshot(
            image_bytes=image_bytes,
            mime_type=asset.declared_content_type,
            width=width,
            height=height,
            context=context_dict,
        )

        # RAG Knowledge integration for audit analysis
        retrieval = KnowledgeRetrieval()
        retrieved_knowledge = retrieval.retrieve(
            query=f"{audit.name} visual design usability layout typography accessibility",
            tenant_id=principal.tenant_id,
            project_id=project_id,
            include_global=True,
            include_project=True,
            top_k=4,
            db=db,
        )

        persisted_findings: list[Finding] = []
        for f in analysis_result.findings:
            boxes_json = json.dumps([b.model_dump() for b in f.bounding_boxes])
            db_finding = Finding(
                tenant_id=principal.tenant_id,
                audit_id=audit.id,
                screen_asset_id=asset.id,
                analysis_job_id=job.id,
                category=f.category,
                title=f.title,
                description=f.description,
                why_it_matters=f.why_it_matters,
                recommended_fix=f.recommended_fix,
                design_principle=f.design_principle,
                severity=f.severity,
                confidence=f.confidence,
                evidence_type=f.evidence_type,
                evidence=f.evidence,
                bounding_boxes_json=boxes_json,
                limitations=f.limitations,
            )
            db.add(db_finding)
            persisted_findings.append(db_finding)

        db.flush()

        # Link citations if relevant knowledge was retrieved
        if retrieved_knowledge:
            for pf in persisted_findings:
                for rank, chunk in enumerate(retrieved_knowledge[:2], start=1):
                    evidence = FindingEvidence(
                        id=uuid4(),
                        tenant_id=principal.tenant_id,
                        finding_id=pf.id,
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        document_display_name=chunk.document_name,
                        quote_or_paraphrase=chunk.text[:250],
                        page_number_snapshot=chunk.page_start,
                        section_heading_snapshot=chunk.section_heading,
                        retrieval_score=chunk.score,
                        retrieval_rank=rank,
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(evidence)

        job.status = "completed"
        job.summary = analysis_result.summary
        job.provider = analysis_result.provider
        job.model = analysis_result.model
        job.completed_at = datetime.now(timezone.utc)
        audit.status = "completed"
        db.commit()
        db.refresh(job)

        return AnalysisResponse(
            job=AnalysisJobRead.model_validate(job),
            findings=_populate_finding_reads(persisted_findings, db),
        )
    except Exception as error:
        db.rollback()
        job.status = "failed"
        job.error_message = str(error)
        job.completed_at = datetime.now(timezone.utc)
        audit.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail={"code": "analysis_failed", "message": f"Vision analysis failed: {error}"},
        )


def _populate_finding_reads(findings: list[Finding], db: Session) -> list[FindingRead]:
    if not findings:
        return []
    finding_ids = [f.id for f in findings]
    evidence_rows = list(
        db.scalars(
            select(FindingEvidence)
            .where(FindingEvidence.finding_id.in_(finding_ids))
            .order_by(FindingEvidence.retrieval_rank.asc())
        )
    )
    evidence_map: dict[UUID, list[FindingEvidenceRead]] = {}
    for ev in evidence_rows:
        evidence_map.setdefault(ev.finding_id, []).append(FindingEvidenceRead.model_validate(ev))

    result = []
    for f in findings:
        boxes_raw = json.loads(f.bounding_boxes_json or "[]")
        boxes = [
            BoundingBoxRead(
                x=float(b.get("x", 0.0)),
                y=float(b.get("y", 0.0)),
                width=float(b.get("width", 0.0)),
                height=float(b.get("height", 0.0)),
            )
            for b in boxes_raw
        ]
        scope = getattr(f, "scope", "screen_level") or "screen_level"
        affected = json.loads(getattr(f, "affected_screen_ids_json", None) or "[]")
        result.append(
            FindingRead(
                id=f.id,
                audit_id=f.audit_id,
                scope=scope,
                affected_screen_ids=affected,
                category=f.category,
                title=f.title,
                description=f.description,
                why_it_matters=f.why_it_matters,
                recommended_fix=f.recommended_fix,
                design_principle=f.design_principle,
                severity=f.severity,
                confidence=f.confidence,
                evidence_type=f.evidence_type,
                evidence=f.evidence,
                bounding_boxes=boxes,
                evidence_sources=evidence_map.get(f.id, []),
                limitations=f.limitations,
                created_at=f.created_at,
            )
        )
    return result


def _populate_multi_screen_finding_reads(findings: list[Finding], db: Session) -> list[MultiScreenFindingRead]:
    if not findings:
        return []
    finding_ids = [f.id for f in findings]
    evidence_rows = list(
        db.scalars(
            select(FindingEvidence)
            .where(FindingEvidence.finding_id.in_(finding_ids))
            .order_by(FindingEvidence.retrieval_rank.asc())
        )
    )
    evidence_map: dict[UUID, list[FindingEvidenceRead]] = {}
    for ev in evidence_rows:
        evidence_map.setdefault(ev.finding_id, []).append(FindingEvidenceRead.model_validate(ev))

    result = []
    for f in findings:
        boxes_raw = json.loads(f.bounding_boxes_json or "[]")
        boxes = [
            MultiScreenBoundingBoxRead(
                screen_id=str(b.get("screen_id", "")),
                x=float(b.get("x", 0.0)),
                y=float(b.get("y", 0.0)),
                width=float(b.get("width", 0.0)),
                height=float(b.get("height", 0.0)),
            )
            for b in boxes_raw
        ]
        affected = json.loads(getattr(f, "affected_screen_ids_json", None) or "[]")
        scope = getattr(f, "scope", "screen_level") or "screen_level"
        result.append(
            MultiScreenFindingRead(
                id=f.id,
                audit_id=f.audit_id,
                scope=scope,
                affected_screen_ids=affected,
                category=f.category,
                title=f.title,
                description=f.description,
                why_it_matters=f.why_it_matters,
                recommended_fix=f.recommended_fix,
                design_principle=f.design_principle,
                severity=f.severity,
                confidence=f.confidence,
                evidence_type=f.evidence_type,
                evidence=f.evidence,
                bounding_boxes=boxes,
                evidence_sources=evidence_map.get(f.id, []),
                limitations=f.limitations,
                created_at=f.created_at,
            )
        )
    return result


@router.get("/projects/{project_id}/audits/{audit_id}/findings", response_model=list[FindingRead])
def list_audit_findings(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[FindingRead]:
    _project_or_404(db, project_id, principal)
    findings = list(
        db.scalars(
            select(Finding)
            .where(Finding.audit_id == audit_id, Finding.tenant_id == principal.tenant_id)
            .order_by(Finding.created_at.asc())
        )
    )
    return _populate_finding_reads(findings, db)


def _prompt_to_read(prompt: AuditPrompt, db: Session) -> PromptRead:
    versions = list(
        db.scalars(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt.id)
            .order_by(PromptVersion.version_number.desc())
        )
    )
    version_reads = [
        PromptVersionRead(
            id=v.id,
            version_number=v.version_number,
            content=v.content,
            selected_finding_ids=[UUID(fid) for fid in json.loads(v.selected_finding_ids_json)],
            user_instructions=v.user_instructions,
            created_at=v.created_at,
        )
        for v in versions
    ]
    selected_ids = [UUID(fid) for fid in json.loads(prompt.selected_finding_ids_json)]
    return PromptRead(
        id=prompt.id,
        audit_id=prompt.audit_id,
        screen_asset_id=prompt.screen_asset_id,
        content=prompt.content,
        original_generated_content=prompt.original_generated_content,
        selected_finding_ids=selected_ids,
        user_instructions=prompt.user_instructions,
        provider=prompt.provider,
        model=prompt.model,
        template_version=prompt.template_version,
        version_number=prompt.version_number,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        versions=version_reads,
    )


@router.post("/projects/{project_id}/audits/{audit_id}/prompt", response_model=PromptRead, status_code=status.HTTP_201_CREATED)
def generate_audit_prompt(
    project_id: UUID,
    audit_id: UUID,
    payload: PromptGenerateRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> PromptRead:
    _project_or_404(db, project_id, principal)
    audit = db.scalar(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.project_id == project_id,
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
        )
    )
    if audit is None:
        raise HTTPException(status_code=404, detail={"code": "audit_not_found", "message": "Audit not found"})

    if not payload.selected_finding_ids:
        raise HTTPException(
            status_code=400,
            detail={"code": "empty_selection", "message": "At least one finding must be selected to generate a prompt."},
        )

    # Validate findings belong to this audit and tenant
    found_findings = list(
        db.scalars(
            select(Finding).where(
                Finding.id.in_(payload.selected_finding_ids),
                Finding.audit_id == audit.id,
                Finding.tenant_id == principal.tenant_id,
            )
        )
    )
    if len(found_findings) != len(payload.selected_finding_ids):
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_findings", "message": "One or more selected finding IDs are invalid or belong to a different audit."},
        )

    # Fetch associated screen asset
    audit_screen = db.scalar(select(AuditScreen).where(AuditScreen.audit_id == audit.id).order_by(AuditScreen.sequence_index.asc()))
    screen_asset = None
    if audit_screen and audit_screen.screen_asset_id:
        screen_asset = db.get(ScreenAsset, audit_screen.screen_asset_id)

    # Retrieve relevant knowledge to ground Google Stitch prompt
    retrieval = KnowledgeRetrieval()
    prompt_query = f"{audit.name} " + " ".join(f.title for f in found_findings)
    retrieved_knowledge = retrieval.retrieve(
        query=prompt_query,
        tenant_id=principal.tenant_id,
        project_id=project_id,
        include_global=True,
        include_project=True,
        top_k=5,
        db=db,
    )

    # Generate Google Stitch prompt
    generator = StitchPromptGenerator()
    if audit.mode == "multi":
        screens_db = list(
            db.scalars(
                select(AuditScreen)
                .where(AuditScreen.audit_id == audit.id, AuditScreen.tenant_id == principal.tenant_id)
                .order_by(AuditScreen.sequence_index.asc())
            )
        )
        screens_with_assets = [(s, db.get(ScreenAsset, s.screen_asset_id)) for s in screens_db]
        latest_job = db.scalar(
            select(AnalysisJob)
            .where(
                AnalysisJob.audit_id == audit.id,
                AnalysisJob.tenant_id == principal.tenant_id,
                AnalysisJob.status == "completed",
            )
            .order_by(AnalysisJob.created_at.desc())
        )
        flow_report_dict = json.loads(latest_job.flow_report_json) if latest_job and latest_job.flow_report_json else {}
        generated_content = generator.generate_multi_screen_prompt(
            audit=audit,
            screens=screens_with_assets,
            selected_findings=found_findings,
            journey_report=flow_report_dict,
            user_instructions=payload.user_instructions,
            retrieved_knowledge=retrieved_knowledge,
        )
    else:
        generated_content = generator.generate_prompt(
            audit=audit,
            screen=screen_asset,
            selected_findings=found_findings,
            user_instructions=payload.user_instructions,
            retrieved_knowledge=retrieved_knowledge,
        )

    selected_ids_json = json.dumps([str(fid) for fid in payload.selected_finding_ids])
    existing_prompt = db.scalar(
        select(AuditPrompt).where(
            AuditPrompt.audit_id == audit.id,
            AuditPrompt.tenant_id == principal.tenant_id,
        )
    )

    if existing_prompt is not None:
        # Update prompt with new generation
        existing_prompt.version_number += 1
        existing_prompt.content = generated_content
        existing_prompt.original_generated_content = generated_content
        existing_prompt.selected_finding_ids_json = selected_ids_json
        existing_prompt.user_instructions = payload.user_instructions
        existing_prompt.screen_asset_id = screen_asset.id if screen_asset else None
        existing_prompt.updated_at = datetime.now(timezone.utc)

        # Record this new version in history
        new_version = PromptVersion(
            prompt_id=existing_prompt.id,
            version_number=existing_prompt.version_number,
            content=generated_content,
            selected_finding_ids_json=selected_ids_json,
            user_instructions=payload.user_instructions,
            created_at=existing_prompt.updated_at,
        )
        db.add(new_version)
        db.commit()
        db.refresh(existing_prompt)
        return _prompt_to_read(existing_prompt, db)

    # Initial prompt creation
    prompt = AuditPrompt(
        tenant_id=principal.tenant_id,
        audit_id=audit.id,
        screen_asset_id=screen_asset.id if screen_asset else None,
        content=generated_content,
        original_generated_content=generated_content,
        selected_finding_ids_json=selected_ids_json,
        user_instructions=payload.user_instructions,
        version_number=1,
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    initial_version = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        content=generated_content,
        selected_finding_ids_json=selected_ids_json,
        user_instructions=payload.user_instructions,
        created_at=prompt.created_at,
    )
    db.add(initial_version)
    db.commit()
    db.refresh(prompt)

    return _prompt_to_read(prompt, db)


@router.get("/projects/{project_id}/audits/{audit_id}/prompt", response_model=PromptRead)
def get_audit_prompt(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> PromptRead:
    _project_or_404(db, project_id, principal)
    prompt = db.scalar(
        select(AuditPrompt).where(
            AuditPrompt.audit_id == audit_id,
            AuditPrompt.tenant_id == principal.tenant_id,
        )
    )
    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "prompt_not_found", "message": "No prompt has been generated for this audit yet."},
        )
    return _prompt_to_read(prompt, db)


@router.patch("/projects/{project_id}/audits/{audit_id}/prompt/{prompt_id}", response_model=PromptRead)
def update_audit_prompt(
    project_id: UUID,
    audit_id: UUID,
    prompt_id: UUID,
    payload: PromptUpdateRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> PromptRead:
    _project_or_404(db, project_id, principal)
    prompt = db.scalar(
        select(AuditPrompt).where(
            AuditPrompt.id == prompt_id,
            AuditPrompt.audit_id == audit_id,
            AuditPrompt.tenant_id == principal.tenant_id,
        )
    )
    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "prompt_not_found", "message": "Prompt not found."},
        )

    prompt.content = payload.content
    prompt.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prompt)
    return _prompt_to_read(prompt, db)


@router.post("/projects/{project_id}/audits/{audit_id}/prompt/{prompt_id}/restore-original", response_model=PromptRead)
def restore_original_prompt(
    project_id: UUID,
    audit_id: UUID,
    prompt_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> PromptRead:
    _project_or_404(db, project_id, principal)
    prompt = db.scalar(
        select(AuditPrompt).where(
            AuditPrompt.id == prompt_id,
            AuditPrompt.audit_id == audit_id,
            AuditPrompt.tenant_id == principal.tenant_id,
        )
    )
    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "prompt_not_found", "message": "Prompt not found."},
        )

    prompt.content = prompt.original_generated_content
    prompt.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prompt)
    return _prompt_to_read(prompt, db)


# ===========================================================================
# Phase 07: Multi-Screen & User Flow Endpoints
# ===========================================================================


@router.patch("/projects/{project_id}/audits/{audit_id}/screens/{screen_id}", response_model=AuditScreenRead)
def update_audit_screen(
    project_id: UUID,
    audit_id: UUID,
    screen_id: UUID,
    body: AuditScreenUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> AuditScreenRead:
    _project_or_404(db, project_id, principal)
    screen = db.scalar(
        select(AuditScreen).where(
            AuditScreen.id == screen_id,
            AuditScreen.audit_id == audit_id,
            AuditScreen.tenant_id == principal.tenant_id,
        )
    )
    if screen is None:
        raise HTTPException(status_code=404, detail={"code": "screen_not_found", "message": "Audit screen not found"})

    if body.screen_label is not None:
        screen.screen_label = body.screen_label
    if body.screen_description is not None:
        screen.screen_description = body.screen_description
    if body.sequence_index is not None and body.sequence_index != screen.sequence_index:
        conflict = db.scalar(
            select(AuditScreen).where(
                AuditScreen.audit_id == audit_id,
                AuditScreen.tenant_id == principal.tenant_id,
                AuditScreen.sequence_index == body.sequence_index,
                AuditScreen.id != screen.id,
            )
        )
        if conflict:
            temp_idx = -9999
            conflict.sequence_index = temp_idx
            db.flush()
            conflict.sequence_index = screen.sequence_index
            screen.sequence_index = body.sequence_index
        else:
            screen.sequence_index = body.sequence_index

    db.commit()
    db.refresh(screen)

    asset = db.get(ScreenAsset, screen.screen_asset_id)
    download_url = None
    if asset:
        try:
            download_url = storage.presign_download(asset.object_key, asset.original_filename)
        except Exception:
            pass

    return AuditScreenRead(
        id=screen.id,
        audit_id=screen.audit_id,
        screen_asset_id=screen.screen_asset_id,
        sequence_index=screen.sequence_index,
        screen_label=screen.screen_label,
        screen_description=screen.screen_description,
        width_px=asset.width_px if asset else None,
        height_px=asset.height_px if asset else None,
        download_url=download_url,
        created_at=screen.created_at,
    )


@router.delete("/projects/{project_id}/audits/{audit_id}/screens/{screen_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_screen_from_audit(
    project_id: UUID,
    audit_id: UUID,
    screen_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Response:
    _project_or_404(db, project_id, principal)
    audit = db.scalar(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.project_id == project_id,
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
        )
    )
    if audit is None:
        raise HTTPException(status_code=404, detail={"code": "audit_not_found", "message": "Audit not found"})

    if audit.mode == "single":
        raise HTTPException(
            status_code=400,
            detail={"code": "single_screen_limit", "message": "Cannot remove screenshot from single-screen audit"},
        )

    screen = db.scalar(
        select(AuditScreen).where(
            AuditScreen.id == screen_id,
            AuditScreen.audit_id == audit_id,
            AuditScreen.tenant_id == principal.tenant_id,
        )
    )
    if screen is None:
        raise HTTPException(status_code=404, detail={"code": "screen_not_found", "message": "Audit screen not found"})

    db.delete(screen)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/projects/{project_id}/audits/{audit_id}/screens/reorder", response_model=list[AuditScreenRead])
def reorder_audit_screens(
    project_id: UUID,
    audit_id: UUID,
    payload: AuditScreenReorderRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> list[AuditScreenRead]:
    _project_or_404(db, project_id, principal)
    audit = db.scalar(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.project_id == project_id,
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
        )
    )
    if audit is None:
        raise HTTPException(status_code=404, detail={"code": "audit_not_found", "message": "Audit not found"})

    indices = [item.sequence_index for item in payload.screens]
    if len(indices) != len(set(indices)):
        raise HTTPException(
            status_code=400,
            detail={"code": "duplicate_sequence_index", "message": "Duplicate sequence indices in reorder request"},
        )

    existing_screens = {
        s.id: s
        for s in db.scalars(
            select(AuditScreen).where(
                AuditScreen.audit_id == audit_id,
                AuditScreen.tenant_id == principal.tenant_id,
            )
        )
    }

    for item in payload.screens:
        if item.screen_id not in existing_screens:
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_screen_id", "message": f"Screen {item.screen_id} not found in this audit"},
            )

    for idx, item in enumerate(payload.screens):
        existing_screens[item.screen_id].sequence_index = -(idx + 1)
    db.flush()

    for item in payload.screens:
        existing_screens[item.screen_id].sequence_index = item.sequence_index
    db.commit()

    updated = list(
        db.scalars(
            select(AuditScreen)
            .where(AuditScreen.audit_id == audit_id, AuditScreen.tenant_id == principal.tenant_id)
            .order_by(AuditScreen.sequence_index.asc())
        )
    )
    results = []
    for s in updated:
        asset = db.get(ScreenAsset, s.screen_asset_id)
        download_url = None
        if asset:
            try:
                download_url = storage.presign_download(asset.object_key, asset.original_filename)
            except Exception:
                pass
        results.append(
            AuditScreenRead(
                id=s.id,
                audit_id=s.audit_id,
                screen_asset_id=s.screen_asset_id,
                sequence_index=s.sequence_index,
                screen_label=s.screen_label,
                screen_description=s.screen_description,
                width_px=asset.width_px if asset else None,
                height_px=asset.height_px if asset else None,
                download_url=download_url,
                created_at=s.created_at,
            )
        )
    return results


@router.patch("/projects/{project_id}/audits/{audit_id}/context", response_model=AuditRead)
def update_audit_context(
    project_id: UUID,
    audit_id: UUID,
    payload: AuditContextUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> AuditRead:
    _project_or_404(db, project_id, principal)
    audit = db.scalar(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.project_id == project_id,
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
        )
    )
    if audit is None:
        raise HTTPException(status_code=404, detail={"code": "audit_not_found", "message": "Audit not found"})

    audit.context_json = json.dumps(payload.context)
    audit.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(audit)
    return AuditRead.model_validate(audit)


@router.post("/projects/{project_id}/audits/{audit_id}/analyze-flow", response_model=MultiScreenAnalysisResponse)
def analyze_audit_flow(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
    vision: MultiScreenAIVisionService = Depends(get_multi_screen_vision_service),
) -> MultiScreenAnalysisResponse:
    _project_or_404(db, project_id, principal)
    audit = db.scalar(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.project_id == project_id,
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
        )
    )
    if audit is None:
        raise HTTPException(status_code=404, detail={"code": "audit_not_found", "message": "Audit not found"})

    if audit.mode != "multi":
        raise HTTPException(
            status_code=400,
            detail={"code": "unsupported_audit_mode", "message": "This endpoint only supports multi-screen audits"},
        )

    screens = list(
        db.scalars(
            select(AuditScreen)
            .where(AuditScreen.audit_id == audit.id, AuditScreen.tenant_id == principal.tenant_id)
            .order_by(AuditScreen.sequence_index.asc())
        )
    )
    if len(screens) < 2:
        raise HTTPException(
            status_code=400,
            detail={"code": "insufficient_screens", "message": "Multi-screen flow analysis requires at least 2 uploaded screenshots"},
        )

    screen_inputs: list[tuple[bytes, str, ScreenContext]] = []
    first_asset_id: UUID | None = None
    for s in screens:
        asset = db.get(ScreenAsset, s.screen_asset_id)
        if asset is None or asset.deleted_at is not None:
            raise HTTPException(
                status_code=404,
                detail={"code": "asset_not_found", "message": f"Screen asset {s.screen_asset_id} not found"},
            )
        if first_asset_id is None:
            first_asset_id = asset.id
        try:
            image_bytes = storage.get_object(asset.object_key)
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "storage_unavailable", "message": f"Failed to retrieve screenshot {asset.original_filename} from storage"},
            ) from error

        width = asset.width_px or 1280
        height = asset.height_px or 800
        if not asset.width_px or not asset.height_px:
            try:
                img_meta = validate_and_process_image(image_bytes, asset.declared_content_type)
                width = img_meta.width
                height = img_meta.height
                asset.width_px = width
                asset.height_px = height
                db.commit()
            except Exception:
                pass

        s_ctx = ScreenContext(
            screen_id=str(s.id),
            screen_label=s.screen_label or f"Screen {s.sequence_index + 1}",
            sequence_index=s.sequence_index,
            width_px=width,
            height_px=height,
            description=s.screen_description,
        )
        screen_inputs.append((image_bytes, asset.declared_content_type, s_ctx))

    job = AnalysisJob(
        tenant_id=principal.tenant_id,
        audit_id=audit.id,
        screen_asset_id=None,
        status="processing",
        provider="forteux-vision-engine",
        model="deterministic-multi-flow-v1",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    db.query(Finding).where(Finding.audit_id == audit.id).delete()

    try:
        context_dict = json.loads(audit.context_json or "{}") if audit.context_json else {}
        analysis_result = vision.analyze_flow(
            screens=screen_inputs,
            journey_context=context_dict,
        )

        retrieval = KnowledgeRetrieval()
        retrieved_knowledge = retrieval.retrieve(
            query=f"{audit.name} user flow progression navigation components consistency",
            tenant_id=principal.tenant_id,
            project_id=project_id,
            include_global=True,
            include_project=True,
            top_k=4,
            db=db,
        )

        persisted_findings: list[Finding] = []
        all_generated = analysis_result.screen_level_findings + analysis_result.cross_screen_findings
        for f in all_generated:
            boxes_json = json.dumps([b.model_dump() for b in f.bounding_boxes])
            affected_json = json.dumps(f.affected_screen_ids)
            db_finding = Finding(
                tenant_id=principal.tenant_id,
                audit_id=audit.id,
                screen_asset_id=first_asset_id if f.scope == "screen_level" else None,
                analysis_job_id=job.id,
                scope=f.scope,
                affected_screen_ids_json=affected_json,
                category=f.category,
                title=f.title,
                description=f.description,
                why_it_matters=f.why_it_matters,
                recommended_fix=f.recommended_fix,
                design_principle=f.design_principle,
                severity=f.severity,
                confidence=f.confidence,
                evidence_type=f.evidence_type,
                evidence=f.evidence,
                bounding_boxes_json=boxes_json,
                limitations=f.limitations,
            )
            db.add(db_finding)
            persisted_findings.append(db_finding)

        db.flush()

        if retrieved_knowledge:
            for pf in persisted_findings:
                for rank, chunk in enumerate(retrieved_knowledge[:2], start=1):
                    evidence = FindingEvidence(
                        id=uuid4(),
                        tenant_id=principal.tenant_id,
                        finding_id=pf.id,
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        document_display_name=chunk.document_name,
                        quote_or_paraphrase=chunk.text[:250],
                        page_number_snapshot=chunk.page_start,
                        section_heading_snapshot=chunk.section_heading,
                        retrieval_score=chunk.score,
                        retrieval_rank=rank,
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(evidence)

        flow_report_data = analysis_result.journey_report.model_dump()
        job.status = "completed"
        job.summary = analysis_result.journey_report.journey_summary
        job.flow_report_json = json.dumps(flow_report_data)
        job.provider = analysis_result.provider
        job.model = analysis_result.model
        job.completed_at = datetime.now(timezone.utc)
        audit.status = "completed"
        db.commit()
        db.refresh(job)

        screen_level = [f for f in persisted_findings if f.scope == "screen_level"]
        cross_screen = [f for f in persisted_findings if f.scope == "cross_screen"]

        return MultiScreenAnalysisResponse(
            job=AnalysisJobRead.model_validate(job),
            journey_report=JourneyReportRead(**flow_report_data),
            screen_level_findings=_populate_multi_screen_finding_reads(screen_level, db),
            cross_screen_findings=_populate_multi_screen_finding_reads(cross_screen, db),
        )
    except Exception as error:
        db.rollback()
        job.status = "failed"
        job.error_message = str(error)
        job.completed_at = datetime.now(timezone.utc)
        audit.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail={"code": "analysis_failed", "message": f"Multi-screen flow analysis failed: {error}"},
        )


@router.get("/projects/{project_id}/audits/{audit_id}/flow-report", response_model=FlowReportRead)
def get_audit_flow_report(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> FlowReportRead:
    _project_or_404(db, project_id, principal)
    audit = db.scalar(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.project_id == project_id,
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
        )
    )
    if audit is None:
        raise HTTPException(status_code=404, detail={"code": "audit_not_found", "message": "Audit not found"})

    if audit.mode != "multi":
        raise HTTPException(
            status_code=400,
            detail={"code": "unsupported_audit_mode", "message": "This endpoint only supports multi-screen audits"},
        )

    job = db.scalar(
        select(AnalysisJob)
        .where(
            AnalysisJob.audit_id == audit_id,
            AnalysisJob.tenant_id == principal.tenant_id,
            AnalysisJob.status == "completed",
        )
        .order_by(AnalysisJob.created_at.desc())
    )
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "no_flow_report", "message": "No completed flow analysis found for this audit"},
        )

    findings = list(
        db.scalars(
            select(Finding)
            .where(Finding.audit_id == audit_id, Finding.tenant_id == principal.tenant_id)
            .order_by(Finding.created_at.asc())
        )
    )

    journey_report = None
    if job.flow_report_json:
        try:
            journey_report = JourneyReportRead(**json.loads(job.flow_report_json))
        except Exception:
            pass

    screen_level = [f for f in findings if f.scope == "screen_level"]
    cross_screen = [f for f in findings if f.scope == "cross_screen"]

    return FlowReportRead(
        job_id=job.id,
        status=job.status,
        journey_report=journey_report,
        screen_level_findings=_populate_multi_screen_finding_reads(screen_level, db),
        cross_screen_findings=_populate_multi_screen_finding_reads(cross_screen, db),
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


# ===========================================================================
# Phase 06: Knowledge Library & Document Intelligence Endpoints
# ===========================================================================


def _document_to_read(doc: KnowledgeDocument, db: Session, storage: S3Storage | None = None) -> KnowledgeDocumentRead:
    versions = list(
        db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version_number.desc())
        )
    )
    version_reads = [DocumentVersionRead.model_validate(v) for v in versions]

    active_v: DocumentVersion | None = None
    if doc.active_version_id:
        active_v = db.get(DocumentVersion, doc.active_version_id)
    if active_v is None and versions:
        active_v = versions[0]

    download_url = None
    if active_v and storage:
        try:
            download_url = storage.presign_download(active_v.object_key, active_v.original_filename)
        except Exception:
            pass

    return KnowledgeDocumentRead(
        id=doc.id,
        tenant_id=doc.tenant_id,
        project_id=doc.project_id,
        scope=doc.scope,
        display_name=doc.display_name,
        category=doc.category,
        description=doc.description,
        status=doc.status,
        error_message=doc.error_message,
        active_version_id=doc.active_version_id,
        page_count=active_v.page_count if active_v else None,
        chunk_count=active_v.chunk_count if active_v else None,
        byte_size=active_v.byte_size if active_v else 0,
        mime_type=active_v.mime_type if active_v else "application/octet-stream",
        version_number=active_v.version_number if active_v else 1,
        embedding_model=active_v.embedding_model if active_v else None,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        download_url=download_url,
        versions=version_reads,
    )


def _validate_doc_upload_data(data: KnowledgeUploadIntentRequest, settings) -> tuple[str, str]:
    if data.size > settings.knowledge_max_doc_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "code": "file_too_large",
                "message": f"Document size exceeds maximum limit of {settings.knowledge_max_doc_bytes // (1024 * 1024)}MB",
            },
        )
    clean_mime = data.content_type.strip().lower().split(";")[0].strip()
    if clean_mime not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "unsupported_media_type",
                "message": f"Unsupported format '{data.content_type}'. Allowed formats: PDF, DOCX, TXT, Markdown.",
            },
        )
    filename = _safe_filename(data.filename)
    return filename, clean_mime


# ---------------------------------------------------------------------------
# Global Knowledge Library Routes
# ---------------------------------------------------------------------------


@router.post("/knowledge/upload", response_model=KnowledgeUploadIntentRead)
def request_global_knowledge_upload(
    data: KnowledgeUploadIntentRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeUploadIntentRead:
    settings = get_settings()
    filename, clean_mime = _validate_doc_upload_data(data, settings)

    # Check duplicate active document by name in global scope
    existing_doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id.is_(None),
            KnowledgeDocument.display_name == filename,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if existing_doc is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_document_name",
                "message": f"A document named '{filename}' already exists in the global library. Use replace instead.",
            },
        )

    doc_id = uuid4()
    version_id = uuid4()
    object_key = f"{principal.tenant_id}/knowledge/{doc_id}/{version_id}/original"

    doc = KnowledgeDocument(
        id=doc_id,
        tenant_id=principal.tenant_id,
        project_id=None,
        scope="global",
        display_name=filename,
        category=data.category,
        description=data.description,
        uploaded_by=principal.id,
        status="uploaded",
    )
    version = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=1,
        object_key=object_key,
        original_filename=filename,
        mime_type=clean_mime,
        byte_size=data.size,
        sha256="",
        status="uploaded",
    )
    db.add(doc)
    db.add(version)
    db.flush()

    try:
        upload_url = storage.presign_upload(object_key, clean_mime, data.size)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail={"code": "storage_unavailable", "message": "Storage unavailable for upload"},
        ) from exc

    return KnowledgeUploadIntentRead(
        document_id=doc_id,
        version_id=version_id,
        version_number=1,
        object_key=object_key,
        upload_url=upload_url,
        expires_in_seconds=settings.s3_upload_ttl_seconds,
    )


@router.post("/knowledge/{document_id}/complete", response_model=KnowledgeDocumentRead)
def complete_global_knowledge_upload(
    document_id: UUID,
    payload: KnowledgeCompleteRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeDocumentRead:
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id.is_(None),
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})

    version = db.get(DocumentVersion, payload.version_id)
    if version is None or version.document_id != doc.id:
        raise HTTPException(status_code=404, detail={"code": "version_not_found", "message": "Version not found"})

    # Download bytes from S3
    try:
        raw_bytes = storage.get_object(version.object_key)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "storage_unavailable", "message": f"Could not read uploaded object: {exc}"},
        ) from exc

    import hashlib
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    version.sha256 = actual_sha

    # Duplicate content check within same scope
    duplicate_version = db.scalar(
        select(DocumentVersion)
        .join(KnowledgeDocument, DocumentVersion.document_id == KnowledgeDocument.id)
        .where(
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id.is_(None),
            KnowledgeDocument.id != doc.id,
            KnowledgeDocument.deleted_at.is_(None),
            DocumentVersion.sha256 == actual_sha,
            DocumentVersion.status == "ready",
        )
    )
    if duplicate_version is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_document",
                "message": "A document with identical content already exists in the global knowledge library.",
            },
        )

    pipeline = KnowledgePipeline()
    try:
        pipeline.process_document(doc, version, raw_bytes, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "processing_failed", "message": str(exc)},
        ) from exc

    db.refresh(doc)
    return _document_to_read(doc, db, storage)


@router.get("/knowledge", response_model=list[KnowledgeDocumentRead])
def list_global_knowledge_documents(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> list[KnowledgeDocumentRead]:
    docs = list(
        db.scalars(
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.tenant_id == principal.tenant_id,
                KnowledgeDocument.project_id.is_(None),
                KnowledgeDocument.deleted_at.is_(None),
            )
            .order_by(KnowledgeDocument.created_at.desc())
        )
    )
    return [_document_to_read(d, db, storage) for d in docs]


@router.get("/knowledge/{document_id}", response_model=KnowledgeDocumentRead)
def get_global_knowledge_document(
    document_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeDocumentRead:
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id.is_(None),
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})
    return _document_to_read(doc, db, storage)


@router.delete("/knowledge/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_global_knowledge_document(
    document_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> None:
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id.is_(None),
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})

    pipeline = KnowledgePipeline()
    pipeline.delete_document_data(doc, db, storage)


@router.post("/knowledge/{document_id}/replace", response_model=KnowledgeUploadIntentRead)
def replace_global_knowledge_document(
    document_id: UUID,
    data: KnowledgeUploadIntentRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeUploadIntentRead:
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id.is_(None),
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})

    settings = get_settings()
    filename, clean_mime = _validate_doc_upload_data(data, settings)

    # Next version number
    current_max = db.scalar(
        select(DocumentVersion.version_number)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    ) or 0
    next_version_num = current_max + 1

    version_id = uuid4()
    object_key = f"{principal.tenant_id}/knowledge/{doc.id}/{version_id}/original"

    version = DocumentVersion(
        id=version_id,
        document_id=doc.id,
        version_number=next_version_num,
        object_key=object_key,
        original_filename=filename,
        mime_type=clean_mime,
        byte_size=data.size,
        sha256="",
        status="uploaded",
    )
    db.add(version)
    db.flush()

    try:
        upload_url = storage.presign_upload(object_key, clean_mime, data.size)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail={"code": "storage_unavailable", "message": "Storage unavailable for upload"},
        ) from exc

    return KnowledgeUploadIntentRead(
        document_id=doc.id,
        version_id=version_id,
        version_number=next_version_num,
        object_key=object_key,
        upload_url=upload_url,
        expires_in_seconds=settings.s3_upload_ttl_seconds,
    )


@router.post("/knowledge/{document_id}/retry", response_model=KnowledgeDocumentRead)
def retry_global_knowledge_document(
    document_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeDocumentRead:
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id.is_(None),
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})

    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    if version is None:
        raise HTTPException(status_code=404, detail={"code": "version_not_found", "message": "No document version found to retry"})

    try:
        raw_bytes = storage.get_object(version.object_key)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "storage_unavailable", "message": f"Could not retrieve document bytes: {exc}"},
        ) from exc

    pipeline = KnowledgePipeline()
    try:
        pipeline.process_document(doc, version, raw_bytes, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "processing_failed", "message": str(exc)},
        ) from exc

    db.refresh(doc)
    return _document_to_read(doc, db, storage)


@router.post("/knowledge/search", response_model=list[KnowledgeSearchResult])
def search_global_knowledge(
    payload: KnowledgeSearchRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[KnowledgeSearchResult]:
    retrieval = KnowledgeRetrieval()
    chunks = retrieval.retrieve(
        query=payload.query,
        tenant_id=principal.tenant_id,
        project_id=None,
        include_global=True,
        include_project=False,
        top_k=payload.top_k,
        db=db,
    )
    return [
        KnowledgeSearchResult(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_name=c.document_name,
            category=c.category,
            scope=c.scope,
            text=c.text,
            page_start=c.page_start,
            page_end=c.page_end,
            section_heading=c.section_heading,
            score=c.score,
            retrieval_rank=c.retrieval_rank,
        )
        for c in chunks
    ]


# ---------------------------------------------------------------------------
# Project-Specific Knowledge Library Routes
# ---------------------------------------------------------------------------


@router.post("/projects/{project_id}/knowledge/upload", response_model=KnowledgeUploadIntentRead)
def request_project_knowledge_upload(
    project_id: UUID,
    data: KnowledgeUploadIntentRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeUploadIntentRead:
    project = _project_or_404(db, project_id, principal)
    settings = get_settings()
    filename, clean_mime = _validate_doc_upload_data(data, settings)

    existing_doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id == project.id,
            KnowledgeDocument.display_name == filename,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if existing_doc is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_document_name",
                "message": f"A document named '{filename}' already exists in this project library. Use replace instead.",
            },
        )

    doc_id = uuid4()
    version_id = uuid4()
    object_key = f"{principal.tenant_id}/{project.id}/knowledge/{doc_id}/{version_id}/original"

    doc = KnowledgeDocument(
        id=doc_id,
        tenant_id=principal.tenant_id,
        project_id=project.id,
        scope="project",
        display_name=filename,
        category=data.category,
        description=data.description,
        uploaded_by=principal.id,
        status="uploaded",
    )
    version = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=1,
        object_key=object_key,
        original_filename=filename,
        mime_type=clean_mime,
        byte_size=data.size,
        sha256="",
        status="uploaded",
    )
    db.add(doc)
    db.add(version)
    db.flush()

    try:
        upload_url = storage.presign_upload(object_key, clean_mime, data.size)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail={"code": "storage_unavailable", "message": "Storage unavailable for upload"},
        ) from exc

    return KnowledgeUploadIntentRead(
        document_id=doc_id,
        version_id=version_id,
        version_number=1,
        object_key=object_key,
        upload_url=upload_url,
        expires_in_seconds=settings.s3_upload_ttl_seconds,
    )


@router.post("/projects/{project_id}/knowledge/{document_id}/complete", response_model=KnowledgeDocumentRead)
def complete_project_knowledge_upload(
    project_id: UUID,
    document_id: UUID,
    payload: KnowledgeCompleteRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeDocumentRead:
    project = _project_or_404(db, project_id, principal)
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id == project.id,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})

    version = db.get(DocumentVersion, payload.version_id)
    if version is None or version.document_id != doc.id:
        raise HTTPException(status_code=404, detail={"code": "version_not_found", "message": "Version not found"})

    try:
        raw_bytes = storage.get_object(version.object_key)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "storage_unavailable", "message": f"Could not read uploaded object: {exc}"},
        ) from exc

    import hashlib
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    version.sha256 = actual_sha

    duplicate_version = db.scalar(
        select(DocumentVersion)
        .join(KnowledgeDocument, DocumentVersion.document_id == KnowledgeDocument.id)
        .where(
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id == project.id,
            KnowledgeDocument.id != doc.id,
            KnowledgeDocument.deleted_at.is_(None),
            DocumentVersion.sha256 == actual_sha,
            DocumentVersion.status == "ready",
        )
    )
    if duplicate_version is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_document",
                "message": "A document with identical content already exists in this project knowledge library.",
            },
        )

    pipeline = KnowledgePipeline()
    try:
        pipeline.process_document(doc, version, raw_bytes, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "processing_failed", "message": str(exc)},
        ) from exc

    db.refresh(doc)
    return _document_to_read(doc, db, storage)


@router.get("/projects/{project_id}/knowledge", response_model=list[KnowledgeDocumentRead])
def list_project_knowledge_documents(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> list[KnowledgeDocumentRead]:
    project = _project_or_404(db, project_id, principal)
    docs = list(
        db.scalars(
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.tenant_id == principal.tenant_id,
                KnowledgeDocument.project_id == project.id,
                KnowledgeDocument.deleted_at.is_(None),
            )
            .order_by(KnowledgeDocument.created_at.desc())
        )
    )
    return [_document_to_read(d, db, storage) for d in docs]


@router.get("/projects/{project_id}/knowledge/{document_id}", response_model=KnowledgeDocumentRead)
def get_project_knowledge_document(
    project_id: UUID,
    document_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeDocumentRead:
    project = _project_or_404(db, project_id, principal)
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id == project.id,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})
    return _document_to_read(doc, db, storage)


@router.delete("/projects/{project_id}/knowledge/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_knowledge_document(
    project_id: UUID,
    document_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> None:
    project = _project_or_404(db, project_id, principal)
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id == project.id,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})

    pipeline = KnowledgePipeline()
    pipeline.delete_document_data(doc, db, storage)


@router.post("/projects/{project_id}/knowledge/{document_id}/replace", response_model=KnowledgeUploadIntentRead)
def replace_project_knowledge_document(
    project_id: UUID,
    document_id: UUID,
    data: KnowledgeUploadIntentRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeUploadIntentRead:
    project = _project_or_404(db, project_id, principal)
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id == project.id,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})

    settings = get_settings()
    filename, clean_mime = _validate_doc_upload_data(data, settings)

    current_max = db.scalar(
        select(DocumentVersion.version_number)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    ) or 0
    next_version_num = current_max + 1

    version_id = uuid4()
    object_key = f"{principal.tenant_id}/{project.id}/knowledge/{doc.id}/{version_id}/original"

    version = DocumentVersion(
        id=version_id,
        document_id=doc.id,
        version_number=next_version_num,
        object_key=object_key,
        original_filename=filename,
        mime_type=clean_mime,
        byte_size=data.size,
        sha256="",
        status="uploaded",
    )
    db.add(version)
    db.flush()

    try:
        upload_url = storage.presign_upload(object_key, clean_mime, data.size)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail={"code": "storage_unavailable", "message": "Storage unavailable for upload"},
        ) from exc

    return KnowledgeUploadIntentRead(
        document_id=doc.id,
        version_id=version_id,
        version_number=next_version_num,
        object_key=object_key,
        upload_url=upload_url,
        expires_in_seconds=settings.s3_upload_ttl_seconds,
    )


@router.post("/projects/{project_id}/knowledge/{document_id}/retry", response_model=KnowledgeDocumentRead)
def retry_project_knowledge_document(
    project_id: UUID,
    document_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
) -> KnowledgeDocumentRead:
    project = _project_or_404(db, project_id, principal)
    doc = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.tenant_id == principal.tenant_id,
            KnowledgeDocument.project_id == project.id,
            KnowledgeDocument.deleted_at.is_(None),
        )
    )
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "document_not_found", "message": "Document not found"})

    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    if version is None:
        raise HTTPException(status_code=404, detail={"code": "version_not_found", "message": "No document version found to retry"})

    try:
        raw_bytes = storage.get_object(version.object_key)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "storage_unavailable", "message": f"Could not retrieve document bytes: {exc}"},
        ) from exc

    pipeline = KnowledgePipeline()
    try:
        pipeline.process_document(doc, version, raw_bytes, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "processing_failed", "message": str(exc)},
        ) from exc

    db.refresh(doc)
    return _document_to_read(doc, db, storage)


@router.post("/projects/{project_id}/knowledge/search", response_model=list[KnowledgeSearchResult])
def search_project_knowledge(
    project_id: UUID,
    payload: KnowledgeSearchRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[KnowledgeSearchResult]:
    project = _project_or_404(db, project_id, principal)
    retrieval = KnowledgeRetrieval()
    chunks = retrieval.retrieve(
        query=payload.query,
        tenant_id=principal.tenant_id,
        project_id=project.id,
        include_global=payload.include_global,
        include_project=payload.include_project,
        top_k=payload.top_k,
        db=db,
    )
    return [
        KnowledgeSearchResult(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_name=c.document_name,
            category=c.category,
            scope=c.scope,
            text=c.text,
            page_start=c.page_start,
            page_end=c.page_end,
            section_heading=c.section_heading,
            score=c.score,
            retrieval_rank=c.retrieval_rank,
        )
        for c in chunks
    ]

