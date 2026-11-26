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
    AnalysisComparisonRead,
    AnalysisVersionRead,
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
    ComponentPattern,
    DesignConsistencyIssue,
    DesignSystemExportCss,
    DesignSystemExportJson,
    DesignSystemPromptRequest,
    DesignSystemPromptResponse,
    DesignSystemReportRead,
    DevTokenRequest,
    DevTokenResponse,
    DocumentVersionRead,
    ExportJobCreate,
    ExportJobRead,
    ExtractedColor,
    ExtractedTypography,
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
    PaginatedAuditsResponse,
    DashboardAuditItem,
    DashboardProjectItem,
    DashboardSummaryResponse,
    ProjectActivityEventRead,
    ProjectCreate,
    ProjectRead,
    ProjectReadFull,
    ProjectUpdate,
    PromptGenerateRequest,
    PromptRead,
    PromptUpdateRequest,
    PromptVersionRead,
    ProposedDesignToken,
    ShapeSurfacePattern,
    SpacingLayoutPattern,
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
    DesignSystemAnalysis,
    DocumentVersion,
    ExportJob,
    Finding,
    FindingEvidence,
    KnowledgeChunk,
    KnowledgeDocument,
    Membership,
    Project,
    ProjectActivityEvent,
    PromptVersion,
    ScreenAsset,
)
from app.db.session import get_db
from app.services.ai_vision import AIVisionService, get_vision_service
from app.services.design_system import (
    DesignSystemExtractionService,
    export_design_system_json,
    export_tokens_to_css,
    get_design_system_service,
)
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
from app.services.export_service import generate_export_content

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


def _log_activity(
    db: Session,
    tenant_id: UUID,
    project_id: UUID,
    event_type: str,
    description: str,
    resource_id: UUID | None = None,
    resource_type: str | None = None,
) -> ProjectActivityEvent:
    event = ProjectActivityEvent(
        tenant_id=tenant_id,
        project_id=project_id,
        event_type=event_type,
        resource_id=resource_id,
        resource_type=resource_type,
        description=description[:500],
    )
    db.add(event)
    return event


def _populate_project_full(project: Project, db: Session) -> ProjectReadFull:
    from sqlalchemy import func

    audit_count = (
        db.scalar(
            select(func.count(Audit.id)).where(
                Audit.project_id == project.id,
                Audit.tenant_id == project.tenant_id,
                Audit.deleted_at.is_(None),
            )
        )
        or 0
    )
    screen_count = (
        db.scalar(
            select(func.count(AuditScreen.id))
            .join(Audit, Audit.id == AuditScreen.audit_id)
            .where(
                Audit.project_id == project.id,
                Audit.tenant_id == project.tenant_id,
                Audit.deleted_at.is_(None),
            )
        )
        or 0
    )
    design_system_count = (
        db.scalar(
            select(func.count(DesignSystemAnalysis.id)).where(
                DesignSystemAnalysis.project_id == project.id,
                DesignSystemAnalysis.tenant_id == project.tenant_id,
                DesignSystemAnalysis.status == "completed",
            )
        )
        or 0
    )

    return ProjectReadFull(
        id=project.id,
        name=project.name,
        description=project.description,
        category=project.category,
        platform_type=project.platform_type,
        thumbnail_url=project.thumbnail_url,
        context_text=project.context_text,
        archived_at=project.archived_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
        audit_count=audit_count,
        screen_count=screen_count,
        design_system_count=design_system_count,
    )


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


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    from sqlalchemy import func

    total_projects = (
        db.scalar(
            select(func.count(func.distinct(Project.id)))
            .join(Membership, Membership.tenant_id == Project.tenant_id)
            .where(
                Project.deleted_at.is_(None),
                Membership.user_id == principal.id,
                Membership.tenant_id == principal.tenant_id,
            )
        )
        or 0
    )

    total_audits = (
        db.scalar(
            select(func.count(func.distinct(Audit.id)))
            .join(Project, Project.id == Audit.project_id)
            .join(Membership, Membership.tenant_id == Project.tenant_id)
            .where(
                Audit.tenant_id == principal.tenant_id,
                Audit.deleted_at.is_(None),
                Project.deleted_at.is_(None),
                Membership.user_id == principal.id,
                Membership.tenant_id == principal.tenant_id,
            )
        )
        or 0
    )

    screens_analysed = (
        db.scalar(
            select(func.count(func.distinct(AuditScreen.id)))
            .join(Audit, Audit.id == AuditScreen.audit_id)
            .join(Project, Project.id == Audit.project_id)
            .join(Membership, Membership.tenant_id == Project.tenant_id)
            .where(
                Audit.tenant_id == principal.tenant_id,
                Audit.deleted_at.is_(None),
                Audit.status == "completed",
                Project.deleted_at.is_(None),
                Membership.user_id == principal.id,
                Membership.tenant_id == principal.tenant_id,
            )
        )
        or 0
    )

    issues_identified = (
        db.scalar(
            select(func.count(func.distinct(Finding.id)))
            .join(AnalysisJob, AnalysisJob.id == Finding.analysis_job_id)
            .join(Audit, Audit.id == Finding.audit_id)
            .join(Project, Project.id == Audit.project_id)
            .join(Membership, Membership.tenant_id == Project.tenant_id)
            .where(
                Finding.tenant_id == principal.tenant_id,
                AnalysisJob.status == "completed",
                Audit.deleted_at.is_(None),
                Audit.status == "completed",
                Project.deleted_at.is_(None),
                Membership.user_id == principal.id,
                Membership.tenant_id == principal.tenant_id,
            )
        )
        or 0
    )

    recent_audit_rows = db.execute(
        select(Audit, Project.name)
        .join(Project, Project.id == Audit.project_id)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
            Project.deleted_at.is_(None),
            Membership.user_id == principal.id,
            Membership.tenant_id == principal.tenant_id,
        )
        .order_by(Audit.created_at.desc())
        .limit(4)
    ).all()

    recent_audits: list[DashboardAuditItem] = []
    for audit, project_name in recent_audit_rows:
        screen_count = (
            db.scalar(
                select(func.count(func.distinct(AuditScreen.id))).where(
                    AuditScreen.audit_id == audit.id,
                    AuditScreen.tenant_id == principal.tenant_id,
                )
            )
            or 0
        )
        finding_count = (
            db.scalar(
                select(func.count(func.distinct(Finding.id)))
                .join(AnalysisJob, AnalysisJob.id == Finding.analysis_job_id)
                .where(
                    Finding.audit_id == audit.id,
                    Finding.tenant_id == principal.tenant_id,
                    AnalysisJob.status == "completed",
                )
            )
            or 0
        )
        recent_audits.append(
            DashboardAuditItem(
                id=audit.id,
                project_id=audit.project_id,
                project_name=project_name,
                name=audit.name,
                mode=audit.mode,
                status=audit.status,
                created_at=audit.created_at,
                screen_count=screen_count,
                finding_count=finding_count,
            )
        )

    recent_project_rows = list(
        db.scalars(
            select(Project)
            .join(Membership, Membership.tenant_id == Project.tenant_id)
            .where(
                Project.deleted_at.is_(None),
                Membership.user_id == principal.id,
                Membership.tenant_id == principal.tenant_id,
            )
            .order_by(Project.updated_at.desc())
            .limit(3)
        )
    )

    recent_projects: list[DashboardProjectItem] = []
    for project in recent_project_rows:
        p_audit_count = (
            db.scalar(
                select(func.count(func.distinct(Audit.id))).where(
                    Audit.project_id == project.id,
                    Audit.tenant_id == principal.tenant_id,
                    Audit.deleted_at.is_(None),
                )
            )
            or 0
        )
        p_screen_count = (
            db.scalar(
                select(func.count(func.distinct(AuditScreen.id)))
                .join(Audit, Audit.id == AuditScreen.audit_id)
                .where(
                    Audit.project_id == project.id,
                    Audit.tenant_id == principal.tenant_id,
                    Audit.deleted_at.is_(None),
                )
            )
            or 0
        )
        recent_projects.append(
            DashboardProjectItem(
                id=project.id,
                name=project.name,
                description=project.description,
                archived_at=project.archived_at,
                updated_at=project.updated_at,
                audit_count=p_audit_count,
                screen_count=p_screen_count,
            )
        )

    return DashboardSummaryResponse(
        total_audits=total_audits,
        screens_analysed=screens_analysed,
        issues_identified=issues_identified,
        total_projects=total_projects,
        recent_audits=recent_audits,
        recent_projects=recent_projects,
    )


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
        category=body.category,
        platform_type=body.platform_type,
        thumbnail_url=body.thumbnail_url,
        context_text=body.context_text,
        created_by=principal.id,
    )
    db.add(project)
    db.flush()
    _log_activity(
        db,
        principal.tenant_id,
        project.id,
        "project_created",
        f"Project '{project.name}' created",
        project.id,
        "project",
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects/history", response_model=PaginatedAuditsResponse)
def get_cross_project_audit_history(
    page: int = 1,
    page_size: int = 20,
    mode: str = "all",
    status: str = "all",
    sort: str = "newest",
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> PaginatedAuditsResponse:
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    from sqlalchemy import func

    query = (
        select(Audit)
        .join(Project, Project.id == Audit.project_id)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(
            Audit.tenant_id == principal.tenant_id,
            Audit.deleted_at.is_(None),
            Project.deleted_at.is_(None),
            Membership.user_id == principal.id,
            Membership.tenant_id == principal.tenant_id,
        )
    )

    if mode in ("single", "multi"):
        query = query.where(Audit.mode == mode)

    if status != "all":
        query = query.where(Audit.status == status)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    if sort == "oldest":
        query = query.order_by(Audit.created_at.asc())
    else:
        query = query.order_by(Audit.created_at.desc())

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    items = list(db.scalars(query))

    return PaginatedAuditsResponse(
        items=[AuditRead.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


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
    db.flush()
    _log_activity(
        db,
        principal.tenant_id,
        project.id,
        "audit_created",
        f"Audit '{audit.name}' ({audit.mode}-screen) created",
        audit.id,
        "audit",
    )
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


# ============================================================================
# Phase 08: Design System Extraction & Cross-Screen Consistency Endpoints
# ============================================================================

def _populate_design_system_read(
    ds: DesignSystemAnalysis,
    screen_count: int = 0,
) -> DesignSystemReportRead:
    def _parse_json(val: str | None, default: Any) -> Any:
        if not val:
            return default
        try:
            return json.loads(val)
        except Exception:
            return default

    score_breakdown = _parse_json(ds.score_breakdown_json, {})
    raw_colors = _parse_json(ds.color_palette_json, [])
    raw_type = _parse_json(ds.typography_json, [])
    raw_spacing = _parse_json(ds.spacing_layout_json, {})
    raw_shapes = _parse_json(ds.shapes_surfaces_json, {})
    raw_components = _parse_json(ds.components_json, [])
    raw_tokens = _parse_json(ds.tokens_json, [])
    raw_issues = _parse_json(ds.consistency_issues_json, [])
    recommendations = _parse_json(ds.recommendations_json, [])
    limitations = _parse_json(ds.limitations_json, [])

    colors = [ExtractedColor(**c) for c in raw_colors]
    typography = [ExtractedTypography(**t) for t in raw_type]
    spacing_layout = SpacingLayoutPattern(**raw_spacing)
    shapes_surfaces = ShapeSurfacePattern(**raw_shapes)
    components = [ComponentPattern(**comp) for comp in raw_components]
    tokens = [ProposedDesignToken(**tok) for tok in raw_tokens]
    issues = [DesignConsistencyIssue(**iss) for iss in raw_issues]

    return DesignSystemReportRead(
        id=ds.id,
        project_id=ds.project_id,
        audit_id=ds.audit_id,
        status=ds.status,
        consistency_score=ds.consistency_score,
        score_breakdown=score_breakdown,
        extraction_coverage=ds.extraction_coverage,
        confidence=ds.confidence,
        summary=ds.summary,
        screens_analyzed=screen_count,
        color_palette=colors,
        typography=typography,
        spacing_layout=spacing_layout,
        shapes_surfaces=shapes_surfaces,
        components=components,
        tokens=tokens,
        consistency_issues=issues,
        recommendations=recommendations,
        limitations=limitations,
        stitch_prompt=ds.stitch_prompt,
        provider=ds.provider,
        model=ds.model,
        error_message=ds.error_message,
        created_at=ds.created_at,
        completed_at=ds.completed_at,
    )


@router.post(
    "/projects/{project_id}/audits/{audit_id}/design-system/extract",
    response_model=DesignSystemReportRead,
    status_code=status.HTTP_200_OK,
)
def extract_audit_design_system(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
    storage: S3Storage = Depends(get_storage),
    service: DesignSystemExtractionService = Depends(get_design_system_service),
) -> DesignSystemReportRead:
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

    screens = list(
        db.scalars(
            select(AuditScreen)
            .where(AuditScreen.audit_id == audit.id, AuditScreen.tenant_id == principal.tenant_id)
            .order_by(AuditScreen.sequence_index.asc())
        )
    )
    if not screens:
        raise HTTPException(
            status_code=400,
            detail={"code": "no_screens_found", "message": "Design system extraction requires at least 1 uploaded screenshot in the audit"},
        )

    # Load screen bytes
    screen_inputs: list[tuple[bytes, str, ScreenContext]] = []
    for s in screens:
        asset = db.get(ScreenAsset, s.screen_asset_id)
        if asset is None or asset.deleted_at is not None:
            raise HTTPException(
                status_code=404,
                detail={"code": "asset_not_found", "message": f"Screen asset {s.screen_asset_id} not found"},
            )
        try:
            image_bytes = storage.get_object(asset.object_key)
        except Exception as error:
            raise HTTPException(
                status_code=503,
                detail={"code": "storage_unavailable", "message": f"Failed to retrieve screenshot {asset.original_filename} from storage"},
            ) from error

        width = asset.width_px or 1280
        height = asset.height_px or 800
        s_ctx = ScreenContext(
            screen_id=str(s.id),
            screen_label=s.screen_label or f"Screen {s.sequence_index + 1}",
            sequence_index=s.sequence_index,
            width_px=width,
            height_px=height,
            description=s.screen_description,
        )
        screen_inputs.append((image_bytes, asset.declared_content_type, s_ctx))

    # Retrieve optional design guidelines context from Knowledge Library
    rag_context = None
    try:
        retrieval = KnowledgeRetrieval()
        doc_chunks = retrieval.retrieve(
            query="design system brand typography colors spacing components buttons tokens",
            tenant_id=principal.tenant_id,
            project_id=project_id,
            top_k=3,
            db=db,
        )
        if doc_chunks:
            rag_context = "\n\n".join([f"[{c.document_name}]: {c.text}" for c in doc_chunks])
    except Exception:
        pass

    # Extract design system
    raw_result, score, breakdown, coverage = service.extract_design_system(
        screens=screen_inputs,
        audit_name=audit.name,
        rag_context=rag_context,
    )

    # Generate Google Stitch design system refinement brief
    generator = StitchPromptGenerator()
    stitch_prompt = generator.generate_design_system_refinement_prompt(
        audit_name=audit.name,
        screen_count=len(screens),
        consistency_score=score,
        colors=[c.model_dump() for c in raw_result.colors],
        typography=[t.model_dump() for t in raw_result.typography],
        spacing_layout=raw_result.spacing_layout.model_dump(),
        shapes_surfaces=raw_result.shapes_surfaces.model_dump(),
        components=[comp.model_dump() for comp in raw_result.components],
        tokens=[tok.model_dump() for tok in raw_result.tokens],
        consistency_issues=[iss.model_dump() for iss in raw_result.consistency_issues],
        recommendations=raw_result.recommendations,
    )

    # Upsert DesignSystemAnalysis
    existing = db.scalar(
        select(DesignSystemAnalysis).where(
            DesignSystemAnalysis.audit_id == audit.id,
            DesignSystemAnalysis.tenant_id == principal.tenant_id,
        )
    )
    now = datetime.now(timezone.utc)
    if existing is not None:
        existing.status = "completed"
        existing.consistency_score = score
        existing.score_breakdown_json = json.dumps(breakdown)
        existing.extraction_coverage = coverage
        existing.confidence = raw_result.confidence
        existing.summary = raw_result.summary
        existing.color_palette_json = json.dumps([c.model_dump() for c in raw_result.colors])
        existing.typography_json = json.dumps([t.model_dump() for t in raw_result.typography])
        existing.spacing_layout_json = json.dumps(raw_result.spacing_layout.model_dump())
        existing.shapes_surfaces_json = json.dumps(raw_result.shapes_surfaces.model_dump())
        existing.components_json = json.dumps([comp.model_dump() for comp in raw_result.components])
        existing.tokens_json = json.dumps([tok.model_dump() for tok in raw_result.tokens])
        existing.consistency_issues_json = json.dumps([iss.model_dump() for iss in raw_result.consistency_issues])
        existing.recommendations_json = json.dumps(raw_result.recommendations)
        existing.limitations_json = json.dumps(raw_result.limitations)
        existing.stitch_prompt = stitch_prompt
        existing.provider = raw_result.provider
        existing.model = raw_result.model
        existing.updated_at = now
        existing.completed_at = now
        ds = existing
    else:
        ds = DesignSystemAnalysis(
            tenant_id=principal.tenant_id,
            project_id=project_id,
            audit_id=audit.id,
            status="completed",
            consistency_score=score,
            score_breakdown_json=json.dumps(breakdown),
            extraction_coverage=coverage,
            confidence=raw_result.confidence,
            summary=raw_result.summary,
            color_palette_json=json.dumps([c.model_dump() for c in raw_result.colors]),
            typography_json=json.dumps([t.model_dump() for t in raw_result.typography]),
            spacing_layout_json=json.dumps(raw_result.spacing_layout.model_dump()),
            shapes_surfaces_json=json.dumps(raw_result.shapes_surfaces.model_dump()),
            components_json=json.dumps([comp.model_dump() for comp in raw_result.components]),
            tokens_json=json.dumps([tok.model_dump() for tok in raw_result.tokens]),
            consistency_issues_json=json.dumps([iss.model_dump() for iss in raw_result.consistency_issues]),
            recommendations_json=json.dumps(raw_result.recommendations),
            limitations_json=json.dumps(raw_result.limitations),
            stitch_prompt=stitch_prompt,
            provider=raw_result.provider,
            model=raw_result.model,
            created_at=now,
            updated_at=now,
            completed_at=now,
        )
        db.add(ds)

    db.commit()
    db.refresh(ds)
    return _populate_design_system_read(ds, screen_count=len(screens))


@router.get(
    "/projects/{project_id}/audits/{audit_id}/design-system",
    response_model=DesignSystemReportRead,
)
def read_audit_design_system(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DesignSystemReportRead:
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

    ds = db.scalar(
        select(DesignSystemAnalysis).where(
            DesignSystemAnalysis.audit_id == audit.id,
            DesignSystemAnalysis.tenant_id == principal.tenant_id,
        )
    )
    if ds is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "design_system_not_found", "message": "No design system analysis found for this audit. Run extraction first."},
        )

    screen_count = len(
        list(
            db.scalars(
                select(AuditScreen).where(
                    AuditScreen.audit_id == audit.id,
                    AuditScreen.tenant_id == principal.tenant_id,
                )
            )
        )
    )
    return _populate_design_system_read(ds, screen_count=screen_count)


@router.get(
    "/projects/{project_id}/audits/{audit_id}/design-system/export/json",
    response_model=DesignSystemExportJson,
)
def export_design_system_json_endpoint(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DesignSystemExportJson:
    _project_or_404(db, project_id, principal)
    ds = db.scalar(
        select(DesignSystemAnalysis).where(
            DesignSystemAnalysis.audit_id == audit_id,
            DesignSystemAnalysis.project_id == project_id,
            DesignSystemAnalysis.tenant_id == principal.tenant_id,
        )
    )
    if ds is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "design_system_not_found", "message": "Design system analysis not found for export"},
        )

    read_rep = _populate_design_system_read(ds)
    exported = export_design_system_json(
        analysis_id=str(ds.id),
        audit_id=str(audit_id),
        project_id=str(project_id),
        consistency_score=ds.consistency_score,
        tokens=read_rep.tokens,
        colors=read_rep.color_palette,
        typography=read_rep.typography,
        components=read_rep.components,
    )
    return DesignSystemExportJson(
        design_system_id=exported["design_system_id"],
        audit_id=exported["audit_id"],
        project_id=exported["project_id"],
        consistency_score=exported["consistency_score"],
        generated_at=datetime.now(timezone.utc).isoformat(),
        tokens=exported["tokens"],
        colors=read_rep.color_palette,
        typography=read_rep.typography,
        components=read_rep.components,
    )


@router.get(
    "/projects/{project_id}/audits/{audit_id}/design-system/export/css",
    response_model=DesignSystemExportCss,
)
def export_design_system_css_endpoint(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DesignSystemExportCss:
    _project_or_404(db, project_id, principal)
    ds = db.scalar(
        select(DesignSystemAnalysis).where(
            DesignSystemAnalysis.audit_id == audit_id,
            DesignSystemAnalysis.project_id == project_id,
            DesignSystemAnalysis.tenant_id == principal.tenant_id,
        )
    )
    if ds is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "design_system_not_found", "message": "Design system analysis not found for export"},
        )

    read_rep = _populate_design_system_read(ds)
    css_content = export_tokens_to_css(read_rep.tokens)
    return DesignSystemExportCss(
        css_content=css_content,
        token_count=len(read_rep.tokens),
    )


@router.post(
    "/projects/{project_id}/audits/{audit_id}/design-system/stitch-prompt",
    response_model=DesignSystemPromptResponse,
)
def generate_design_system_stitch_prompt_endpoint(
    project_id: UUID,
    audit_id: UUID,
    body: DesignSystemPromptRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DesignSystemPromptResponse:
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

    ds = db.scalar(
        select(DesignSystemAnalysis).where(
            DesignSystemAnalysis.audit_id == audit.id,
            DesignSystemAnalysis.tenant_id == principal.tenant_id,
        )
    )
    if ds is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "design_system_not_found", "message": "Run design system extraction before generating a Stitch prompt"},
        )

    screens = list(
        db.scalars(
            select(AuditScreen).where(
                AuditScreen.audit_id == audit.id,
                AuditScreen.tenant_id == principal.tenant_id,
            )
        )
    )

    read_rep = _populate_design_system_read(ds, screen_count=len(screens))
    generator = StitchPromptGenerator()

    # Regenerate prompt with optional user instructions
    new_prompt = generator.generate_design_system_refinement_prompt(
        audit_name=audit.name,
        screen_count=len(screens),
        consistency_score=ds.consistency_score,
        colors=[c.model_dump() for c in read_rep.color_palette],
        typography=[t.model_dump() for t in read_rep.typography],
        spacing_layout=read_rep.spacing_layout.model_dump(),
        shapes_surfaces=read_rep.shapes_surfaces.model_dump(),
        components=[comp.model_dump() for comp in read_rep.components],
        tokens=[tok.model_dump() for tok in read_rep.tokens] if body.include_tokens else [],
        consistency_issues=[iss.model_dump() for iss in read_rep.consistency_issues] if body.include_inconsistencies else [],
        recommendations=read_rep.recommendations,
        user_instructions=body.custom_instructions,
    )

    # Update in DB
    ds.stitch_prompt = new_prompt
    ds.updated_at = datetime.now(timezone.utc)
    db.commit()

    return DesignSystemPromptResponse(
        prompt=new_prompt,
        tokens_included=len(read_rep.tokens) if body.include_tokens else 0,
        issues_addressed=len(read_rep.consistency_issues) if body.include_inconsistencies else 0,
        screens_referenced=len(screens),
    )


@router.get(
    "/projects/{project_id}/design-systems",
    response_model=list[DesignSystemReportRead],
)
def list_project_design_systems(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[DesignSystemReportRead]:
    _project_or_404(db, project_id, principal)
    analyses = list(
        db.scalars(
            select(DesignSystemAnalysis)
            .where(
                DesignSystemAnalysis.project_id == project_id,
                DesignSystemAnalysis.tenant_id == principal.tenant_id,
            )
            .order_by(DesignSystemAnalysis.updated_at.desc())
        )
    )
    return [_populate_design_system_read(a) for a in analyses]


# ===========================================================================
# Phase 09: Project History, Versions & Export Endpoints
# ===========================================================================


@router.patch("/projects/{project_id}", response_model=ProjectReadFull)
def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProjectReadFull:
    project = _project_or_404(db, project_id, principal)

    if body.name is not None:
        trimmed = body.name.strip()
        if not trimmed:
            raise HTTPException(status_code=422, detail={"code": "invalid_name", "message": "Project name cannot be blank"})
        project.name = trimmed
    if body.description is not None:
        project.description = body.description
    if body.category is not None:
        project.category = body.category
    if body.platform_type is not None:
        project.platform_type = body.platform_type
    if body.thumbnail_url is not None:
        project.thumbnail_url = body.thumbnail_url
    if body.context_text is not None:
        project.context_text = body.context_text

    project.updated_at = datetime.now(timezone.utc)
    _log_activity(
        db,
        principal.tenant_id,
        project.id,
        "project_updated",
        f"Project '{project.name}' details updated",
        project.id,
        "project",
    )
    db.commit()
    db.refresh(project)
    return _populate_project_full(project, db)


@router.post("/projects/{project_id}/archive", response_model=ProjectReadFull)
def archive_project(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProjectReadFull:
    project = _project_or_404(db, project_id, principal)
    project.archived_at = datetime.now(timezone.utc)
    project.updated_at = datetime.now(timezone.utc)
    _log_activity(
        db,
        principal.tenant_id,
        project.id,
        "project_archived",
        f"Project '{project.name}' moved to archive",
        project.id,
        "project",
    )
    db.commit()
    db.refresh(project)
    return _populate_project_full(project, db)


@router.post("/projects/{project_id}/restore", response_model=ProjectReadFull)
def restore_project(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProjectReadFull:
    project = _project_or_404(db, project_id, principal)
    project.archived_at = None
    project.updated_at = datetime.now(timezone.utc)
    _log_activity(
        db,
        principal.tenant_id,
        project.id,
        "project_restored",
        f"Project '{project.name}' restored from archive",
        project.id,
        "project",
    )
    db.commit()
    db.refresh(project)
    return _populate_project_full(project, db)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Response:
    project = _project_or_404(db, project_id, principal)
    project.deleted_at = datetime.now(timezone.utc)
    project.updated_at = datetime.now(timezone.utc)
    _log_activity(
        db,
        principal.tenant_id,
        project.id,
        "project_deleted",
        f"Project '{project.name}' deleted",
        project.id,
        "project",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/projects/{project_id}/stats", response_model=ProjectReadFull)
def get_project_stats(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ProjectReadFull:
    project = _project_or_404(db, project_id, principal)
    return _populate_project_full(project, db)


@router.get("/projects/{project_id}/activity", response_model=list[ProjectActivityEventRead])
def list_project_activity(
    project_id: UUID,
    limit: int = 50,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ProjectActivityEvent]:
    _project_or_404(db, project_id, principal)
    return list(
        db.scalars(
            select(ProjectActivityEvent)
            .where(
                ProjectActivityEvent.project_id == project_id,
                ProjectActivityEvent.tenant_id == principal.tenant_id,
            )
            .order_by(ProjectActivityEvent.created_at.desc())
            .limit(min(limit, 100))
        )
    )


@router.get(
    "/projects/{project_id}/audits/{audit_id}/versions",
    response_model=list[AnalysisVersionRead],
)
def list_audit_versions(
    project_id: UUID,
    audit_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[AnalysisVersionRead]:
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

    from sqlalchemy import func

    jobs = list(
        db.scalars(
            select(AnalysisJob)
            .where(
                AnalysisJob.audit_id == audit.id,
                AnalysisJob.tenant_id == principal.tenant_id,
            )
            .order_by(AnalysisJob.created_at.asc())
        )
    )
    results: list[AnalysisVersionRead] = []
    for idx, job in enumerate(jobs, start=1):
        count = (
            db.scalar(
                select(func.count(Finding.id)).where(Finding.analysis_job_id == job.id)
            )
            or 0
        )
        results.append(
            AnalysisVersionRead(
                job_id=job.id,
                audit_id=job.audit_id,
                version_number=idx,
                status=job.status,
                provider=job.provider,
                model=job.model,
                finding_count=count,
                summary=job.summary,
                created_at=job.created_at,
                completed_at=job.completed_at,
            )
        )
    return results


@router.get(
    "/projects/{project_id}/audits/{audit_id}/versions/compare",
    response_model=AnalysisComparisonRead,
)
def compare_audit_versions(
    project_id: UUID,
    audit_id: UUID,
    earlier_job_id: UUID,
    later_job_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> AnalysisComparisonRead:
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

    earlier_job = db.get(AnalysisJob, earlier_job_id)
    later_job = db.get(AnalysisJob, later_job_id)

    if not earlier_job or not later_job:
        raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "One or both analysis jobs not found"})

    if earlier_job.tenant_id != principal.tenant_id or later_job.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "One or both analysis jobs not found"})

    if earlier_job.audit_id != audit.id or later_job.audit_id != audit.id:
        raise HTTPException(status_code=400, detail={"code": "cross_audit_comparison", "message": "Cannot compare analysis jobs from different audits"})

    earlier_findings = list(db.scalars(select(Finding).where(Finding.analysis_job_id == earlier_job.id)))
    later_findings = list(db.scalars(select(Finding).where(Finding.analysis_job_id == later_job.id)))

    earlier_reads = _populate_finding_reads(earlier_findings, db)
    later_reads = _populate_finding_reads(later_findings, db)

    def finding_key(f: FindingRead) -> str:
        return f"{f.category.lower().strip()}:{f.title.lower().strip()}"

    earlier_map = {finding_key(f): f for f in earlier_reads}
    later_map = {finding_key(f): f for f in later_reads}

    persistent: list[FindingRead] = []
    changed_severity: list[FindingRead] = []
    resolved: list[FindingRead] = []
    new_f: list[FindingRead] = []

    for k, lf in later_map.items():
        if k in earlier_map:
            ef = earlier_map[k]
            if lf.severity != ef.severity:
                changed_severity.append(lf)
            else:
                persistent.append(lf)
        else:
            new_f.append(lf)

    for k, ef in earlier_map.items():
        if k not in later_map:
            resolved.append(ef)

    comparison_type = "multi_screen" if audit.mode == "multi" else "single_screen"
    limitations = [
        "Finding equivalence is based on title and category heuristic matching.",
        "A finding marked 'resolved' may indicate the vision model did not detect it in this run rather than a verified fix.",
        "Changes in bounding box coordinates or wording are not classified as severity changes.",
    ]

    return AnalysisComparisonRead(
        earlier_job_id=earlier_job.id,
        later_job_id=later_job.id,
        audit_id=audit.id,
        comparison_type=comparison_type,
        new_findings=new_f,
        resolved_findings=resolved,
        persistent_findings=persistent,
        changed_severity_findings=changed_severity,
        earlier_finding_count=len(earlier_reads),
        later_finding_count=len(later_reads),
        limitations=limitations,
    )


@router.post(
    "/projects/{project_id}/exports",
    response_model=ExportJobRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project_export(
    project_id: UUID,
    body: ExportJobCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ExportJobRead:
    project = _project_or_404(db, project_id, principal)

    audit: Audit | None = None
    if body.export_type in ("single_audit", "multi_audit") and not body.audit_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "missing_audit_id", "message": "audit_id is required for audit exports"},
        )

    if body.audit_id is not None:
        audit = db.scalar(
            select(Audit).where(
                Audit.id == body.audit_id,
                Audit.project_id == project.id,
                Audit.tenant_id == principal.tenant_id,
                Audit.deleted_at.is_(None),
            )
        )
        if audit is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "audit_not_found", "message": "Audit not found for this export"},
            )

    job = ExportJob(
        tenant_id=principal.tenant_id,
        project_id=project.id,
        audit_id=body.audit_id,
        created_by=principal.id,
        export_type=body.export_type,
        format=body.format,
        status="pending",
    )
    db.add(job)
    db.flush()

    try:
        content, _, _ = generate_export_content(db, job, project, audit)
        job.file_content = content
        job.file_size = len(content.encode("utf-8"))
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        _log_activity(
            db,
            principal.tenant_id,
            project.id,
            "export_generated",
            f"Export generated: {body.export_type} ({body.format})",
            job.id,
            "export",
        )
        db.commit()
        db.refresh(job)
    except Exception as error:
        db.rollback()
        job.status = "failed"
        job.error_message = str(error)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)

    read = ExportJobRead.model_validate(job)
    read.download_available = job.status == "completed" and bool(job.file_content)
    return read


@router.get("/projects/{project_id}/exports", response_model=list[ExportJobRead])
def list_project_exports(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[ExportJobRead]:
    _project_or_404(db, project_id, principal)
    jobs = list(
        db.scalars(
            select(ExportJob)
            .where(
                ExportJob.project_id == project_id,
                ExportJob.tenant_id == principal.tenant_id,
            )
            .order_by(ExportJob.created_at.desc())
        )
    )
    results: list[ExportJobRead] = []
    for j in jobs:
        read = ExportJobRead.model_validate(j)
        read.download_available = j.status == "completed" and bool(j.file_content)
        results.append(read)
    return results


@router.get("/projects/{project_id}/exports/{export_id}", response_model=ExportJobRead)
def get_project_export(
    project_id: UUID,
    export_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ExportJobRead:
    _project_or_404(db, project_id, principal)
    job = db.scalar(
        select(ExportJob).where(
            ExportJob.id == export_id,
            ExportJob.project_id == project_id,
            ExportJob.tenant_id == principal.tenant_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "export_not_found", "message": "Export job not found"})
    read = ExportJobRead.model_validate(job)
    read.download_available = job.status == "completed" and bool(job.file_content)
    return read


@router.get("/projects/{project_id}/exports/{export_id}/download")
def download_project_export(
    project_id: UUID,
    export_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Response:
    project = _project_or_404(db, project_id, principal)
    job = db.scalar(
        select(ExportJob).where(
            ExportJob.id == export_id,
            ExportJob.project_id == project_id,
            ExportJob.tenant_id == principal.tenant_id,
        )
    )
    if job is None or job.status != "completed" or not job.file_content:
        raise HTTPException(status_code=404, detail={"code": "export_not_found", "message": "Export not ready or not found"})

    safe_title = "".join(c if c.isalnum() else "_" for c in project.name)[:30]
    ext_map = {"json": "json", "markdown": "md", "csv": "csv", "zip": "json"}
    ext = ext_map.get(job.format, "txt")
    media_map = {
        "json": "application/json",
        "markdown": "text/markdown; charset=utf-8",
        "csv": "text/csv; charset=utf-8",
        "zip": "application/json",
    }
    media_type = media_map.get(job.format, "text/plain")
    filename = f"{job.export_type}_{safe_title}_{job.id}.{ext}"

    return Response(
        content=job.file_content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



