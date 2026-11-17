# Backend Architecture

**Status:** Foundation implemented; cloud deployment not verified.

## Service structure

```text
backend/
  app/
    api/v1/routes.py       Protected identity, project, audit, asset routes
    api/v1/schemas.py      Pydantic request/response contracts
    core/config.py        Environment-backed settings and production guards
    core/auth.py          Cognito access-token verification and identity mapping
    db/base.py            SQLAlchemy declarative base
    db/models.py          User, tenant, membership, project, audit, asset models
    db/session.py         SQLAlchemy engine/session dependencies
    services/storage.py   S3 client, presigning, metadata check, deletion
    main.py               FastAPI app, health routes, middleware, errors
  migrations/              Alembic environment and versioned migrations
  tests/                   Isolated unit/integration tests
```

The API is a modular monolith. Long-running AI analysis, document ingestion, and durable background jobs are deliberately absent. This avoids introducing an unselected queue and avoids reporting success for work that is not implemented.

## Request path

The Next.js server route at `/api/backend/*` accepts same-origin JSON requests, validates the path/method/body limit, obtains the access token from the encrypted NextAuth JWT session, and forwards the request to FastAPI. It does not forward arbitrary browser headers or expose the upstream backend URL. FastAPI independently verifies the bearer token and authorizes project membership.

Large screenshot bytes bypass both application servers: the authenticated API returns a narrowly scoped, short-lived S3 PUT URL, and the browser transfers the file directly to the private bucket. The API later checks object metadata. The current endpoint only accepts declared PNG/JPEG uploads; it does not decode or inspect image bytes.

## Routes

| Route | Access | Current behavior |
|---|---|---|
| `GET /health/live` | Public | Process liveness |
| `GET /health/ready` | Public | Checks PostgreSQL connectivity, OIDC configuration, and S3 access; returns 503 when any are unavailable |
| `GET /api/v1/me` | Bearer token | Returns identity mapped from verified issuer and subject |
| `GET/POST /api/v1/projects` | Bearer token | Lists visible projects / creates a project in the caller's tenant |
| `GET /api/v1/projects/{project_id}` | Bearer token | Reads a membership-authorized project |
| `GET/POST /api/v1/projects/{project_id}/audits` | Bearer token | Lists/creates foundation audit records |
| `GET /api/v1/projects/{project_id}/audits/{audit_id}` | Bearer token | Reads an authorized audit |
| `POST /api/v1/projects/{project_id}/uploads` | Bearer token | Creates a pending asset and returns a presigned upload target |
| `POST /api/v1/projects/{project_id}/assets/{asset_id}/complete` | Bearer token | Verifies S3 presence, declared size, and content type |
| `GET /api/v1/projects/{project_id}/assets` | Bearer token | Lists non-deleted assets |
| `GET /api/v1/projects/{project_id}/assets/{asset_id}/download` | Bearer token | Returns a short-lived attachment URL |
| `DELETE /api/v1/projects/{project_id}/assets/{asset_id}` | Bearer token | Revokes access and deletes the object |

Responses use stable error codes, safe messages, request IDs, and explicit status codes. Unexpected server failures are logged without returning internal exception text. Readiness logs identify the dependency and exception class but do not disclose credentials or connection strings.

## Database and migrations

SQLAlchemy sessions are request-scoped. Alembic imports the same model metadata used by the application; the initial reversible migration creates the ownership and asset foundation. Run migrations as a release/deployment operation rather than from each API process.

## Configuration and operation

Backend configuration is read from environment variables (or `backend/.env` for local development). Production mode requires a PostgreSQL connection URL and HTTPS OIDC issuer; S3 region and bucket are required for storage operations. `/health/live` intentionally remains available when dependencies are absent, while `/health/ready` returns 503.

Use the instructions in [ENVIRONMENT_CONFIGURATION.md](./ENVIRONMENT_CONFIGURATION.md). Do not use SQLite or a local filesystem as production persistence.

## Deferred responsibilities

No queue/worker, image parser, screenshot transformation, audit analysis, knowledge processing, request rate limiter, or metrics exporter is included. Select and implement those only in a later approved phase. Add health/metrics integration, deployment networking, secrets manager, database backup/recovery, and operational alerting before launch.
