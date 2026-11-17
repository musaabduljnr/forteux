import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.db.session import make_engine
from app.services.storage import S3Storage

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger("forteux.api")
app = FastAPI(
    title="Forteux API",
    version="1.0.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.app_env != "production" else None,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    supplied = request.headers.get("X-Request-ID", "")
    request_id = supplied if supplied and len(supplied) <= 128 else str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def handle_http_error(request: Request, error: HTTPException) -> JSONResponse:
    detail = error.detail
    if not isinstance(detail, dict):
        detail = {"code": "request_failed", "message": str(detail)}
    return JSONResponse(
        status_code=error.status_code,
        content={"error": detail, "request_id": getattr(request.state, "request_id", None)},
        headers=error.headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    details = [
        {"location": item.get("loc"), "message": item.get("msg"), "code": item.get("type")}
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": "invalid_request", "message": "Request validation failed", "details": details},
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.error(
        "Unhandled request failure method=%s path=%s error_type=%s",
        request.method,
        request.url.path,
        type(error).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {"code": "internal_error", "message": "The request could not be completed"},
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready", response_model=None)
def health_ready() -> JSONResponse | dict[str, object]:
    checks: dict[str, str] = {}
    database_engine = None
    try:
        database_url = settings.require_database()
        database_engine = make_engine(database_url)
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "ready"
    except (RuntimeError, SQLAlchemyError, ValueError) as error:
        checks["database"] = "unavailable"
        logger.warning("Readiness check failed dependency=database error_type=%s", type(error).__name__)
    finally:
        if database_engine is not None:
            database_engine.dispose()

    try:
        settings.require_oidc()
        checks["authentication"] = "configured"
    except RuntimeError as error:
        checks["authentication"] = "unavailable"
        logger.warning("Readiness check failed dependency=authentication error_type=%s", type(error).__name__)
    try:
        S3Storage(settings).healthcheck()
        checks["object_storage"] = "ready"
    except (RuntimeError, BotoCoreError, ClientError) as error:
        checks["object_storage"] = "unavailable"
        logger.warning("Readiness check failed dependency=object_storage error_type=%s", type(error).__name__)

    ready = all(value in {"ready", "configured"} for value in checks.values())
    return JSONResponse(status_code=200 if ready else 503, content={"status": "ready" if ready else "not_ready", "checks": checks})


app.include_router(v1_router, prefix=settings.api_prefix)
