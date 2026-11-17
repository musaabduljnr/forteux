# Local Infrastructure Report

**Date:** 2026-11-16  
**Status:** Local development configuration complete; Docker runtime installation required on host.

---

## 1. Audit of Existing Implementation

Prior to this task, the repository contained:
- **Frontend**: Next.js 15 App Router application with existing UX routes (`/audits/*`, `/projects/*`, `/settings`, etc.), server-side authenticated proxy at `/api/backend/[...path]`, and Cognito NextAuth integration stub.
- **Backend Foundation**: FastAPI application with modular architecture (`api/v1`, `core`, `db`, `services`), SQLAlchemy 2 models (`User`, `Tenant`, `Membership`, `Project`, `Audit`, `ScreenAsset`), and an Alembic migration (`0001_foundation`).
- **Storage**: `S3Storage` service utilizing `boto3` to generate short-lived presigned PUT/GET URLs and perform `HeadObject` metadata verification.
- **Architecture & Security Boundaries**: Tenant-scoped authorization, non-trust of frontend-supplied user IDs, server-side session cookies, and separation of development/production environments.

**What was NOT changed**:
- Existing UI routes and design system components were preserved.
- No Phase 03 image processing, PIL/OpenCV decoding, or AI engine components were introduced.

---

## 2. Configured Local Development Services

The local development infrastructure is configured in `docker-compose.yml`:

```
+-------------------+      +-------------------+
|  Next.js Frontend | ---> |  FastAPI Backend  |
|   (Port 3000)     |      |   (Port 8000)     |
+-------------------+      +-------------------+
                             |               |
                             v               v
                   +-------------------+   +-------------------+
                   |   PostgreSQL 16   |   |   MinIO S3 Store  |
                   |    (Port 5432)    |   | (Port 9000/9001)  |
                   +-------------------+   +-------------------+
                                                     ^
                                                     |
                                           +-------------------+
                                           |    minio-init     |
                                           | (Bucket Config)   |
                                           +-------------------+
```

1. **PostgreSQL 16 (`postgres`)**:
   - Container: `forteux-postgres`
   - Named volume: `postgres_data` mapped to `/var/lib/postgresql/data` (ensures persistence across restarts).
   - Healthcheck: `pg_isready -U forteux -d forteux`.
2. **MinIO (`minio`)**:
   - Container: `forteux-minio`
   - Named volume: `minio_data` mapped to `/data` (ensures object persistence).
   - Healthcheck: `curl -f http://localhost:9000/minio/health/live`.
3. **MinIO Initializer (`minio-init`)**:
   - Creates the private bucket `forteux-private-screenshots`.
   - Explicitly sets bucket policy to private (`mc anonymous set none`).
4. **FastAPI Backend (`backend`)**:
   - Container: `forteux-backend`
   - Automatically runs `alembic upgrade head` before booting `uvicorn`.
   - Connected to `postgres` and `minio`.
   - Healthcheck: `curl -f http://localhost:8000/health/live`.
5. **Next.js Frontend (`frontend`)**:
   - Container: `forteux-frontend`
   - Connected to backend via server-side proxy (`BACKEND_API_URL=http://backend:8000/api/v1`).
   - Healthcheck: `curl -f http://localhost:3000/`.

---

## 3. Authentication Implementation

To enable local development without requiring live AWS Cognito infrastructure:
- **Development Auth Adapter**: Implemented in `backend/app/core/auth.py` and `lib/auth-options.ts`.
- **Backend Token Endpoint**: `POST /api/v1/auth/dev-token` issues signed HS256 tokens with standard OIDC claims.
- **Provider Independence**: Backend endpoints consume standard `Authorization: Bearer <token>` headers regardless of whether the token is issued by Cognito or the Dev Auth Adapter.
- **User Ownership & Multi-Tenancy**: The adapter automatically provisions the local `User`, a personal `Tenant`, and an `owner` `Membership` upon first verified token access. User isolation is strictly enforced.
- **Production Guard**: `DEV_AUTH_ENABLED=true` is strictly prohibited in `APP_ENV=production` and triggers an immediate application crash at startup. Dev tokens are rejected with `401 Unauthorized` in production.
- **Cognito Parity**: Switching to Cognito requires only setting environment variables without code modifications.

---

## 4. File Storage Configuration

- **Private Storage**: MinIO bucket is non-public.
- **Backend-Controlled URLs**: Opaque object keys generated server-side: `{tenant_id}/{project_id}/screens/{asset_id}/original`.
- **Upload Flow**: Presigned PUT URL generated after filename, MIME type (`image/png`, `image/jpeg`), and size check.
- **Download Flow**: Presigned GET URL generated with `Content-Disposition: attachment`.
- **Compatibility**: Configured via `boto3` path-style addressing; switching to AWS S3 requires only removing `S3_ENDPOINT_URL`.

---

## 5. Verification & Test Execution Results

All tests were executed against the codebase in this session:

| Test / Check | Command Executed | Result | Notes |
|---|---|---|---|
| **Frontend Typecheck** | `npm run typecheck` (`tsc --noEmit`) | **PASS** | 0 type errors |
| **Frontend Lint** | `npm run lint` (`eslint`) | **PASS** | 0 lint errors |
| **Frontend Build** | `npm run build` (`next build`) | **PASS** | Optimized production build generated successfully |
| **Backend Pytest Suite** | `python -m pytest backend/tests` | **PASS** | 22 tests passed (0 failed) |
| **Dev Auth Token Issuance** | `test_issue_and_verify_dev_token` | **PASS** | Verified standard claims and expiration |
| **Dev Auth Production Guard** | `test_dev_auth_strictly_forbidden_in_production` | **PASS** | Verifies RuntimeError and 401 in production |
| **Dev Auth Multi-Tenant Isolation** | `test_dev_user_lifecycle_and_tenant_isolation` | **PASS** | User A cannot view or access User B projects |
| **Database Migration Upgrade/Downgrade**| `test_migration_upgrade_and_downgrade` | **PASS** | Alembic schema upgrade and downgrade verified |
| **MinIO Endpoint Storage Support** | `test_s3_storage_supports_minio_endpoint` | **PASS** | S3Storage validates MinIO endpoint and presigning |
| **Health Liveness & Readiness** | `test_readiness_with_dev_auth_adapter` | **PASS** | Verifies readiness checks with dev auth adapter |
| **Host Docker Runtime Startup** | `docker compose up -d` | **BLOCKED** | Docker is not installed on the host machine |

---

## 6. Environment Blockers & Next Steps

### Identified Blocker
- **Docker Desktop is not installed on the host Windows system**:
  - `docker` is not recognized in the system path.
  - WSL2 distribution is not currently registered.
  - While all Dockerfile and docker-compose configurations are in place and all application/unit tests pass, the live containers cannot be started until Docker Desktop is installed.

### Native Execution Workaround
Both services can be run natively without Docker:
- Frontend dev server is already running on `http://localhost:3000`.
- Backend can run locally on port 8000 using Python virtual environment and local PostgreSQL/MinIO or SQLite for testing.
