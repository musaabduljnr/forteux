# Local Development Setup Guide

This guide details how to run, configure, and manage the Forteux local development environment using Docker Compose or native services.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       Next.js Web Application         |
                      |        http://localhost:3000          |
                      +---------------------------------------+
                                          |
                      (Server-side same-origin API proxy /api/backend/*)
                                          |
                                          v
                      +---------------------------------------+
                      |            FastAPI Backend            |
                      |        http://localhost:8000          |
                      +---------------------------------------+
                                     /         \
                 (SQLAlchemy / psycopg)       (boto3 / S3 v4 Signature)
                                   /             \
                                  v               v
            +---------------------------+   +---------------------------+
            |      PostgreSQL 16        |   |       MinIO (S3 API)      |
            |   localhost:5432 (app data)|  |  localhost:9000 (private)  |
            +---------------------------+   |  localhost:9001 (console)  |
                                            +---------------------------+
```

---

## 1. Services & Ports

| Service | Port | Description | Health Check |
|---|---|---|---|
| **Frontend** | `3000` | Next.js 15 UI and NextAuth proxy | `curl -f http://localhost:3000/` |
| **Backend** | `8000` | FastAPI application (`/api/v1`) | `curl -f http://localhost:8000/health/live` |
| **PostgreSQL** | `5432` | Relational database (UUIDs, multi-tenant schema) | `pg_isready -U forteux -d forteux` |
| **MinIO API** | `9000` | S3-compatible private object store | `curl -f http://localhost:9000/minio/health/live` |
| **MinIO Console**| `9001` | MinIO web management UI | N/A |
| **MinIO Init** | N/A | Ephemeral job configuring private bucket `forteux-private-screenshots` | Runs on startup |

---

## 2. Environment Configuration

### Frontend (`.env.local`)
Create `.env.local` by copying `.env.local.example`:

```ini
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=local-dev-nextauth-secret-change-in-production-random-bytes

# Server-only FastAPI backend proxy destination
BACKEND_API_URL=http://127.0.0.1:8000/api/v1

# Development Authentication Adapter
DEV_AUTH_ENABLED=true
NEXT_PUBLIC_DEV_AUTH_ENABLED=true
NEXT_PUBLIC_OIDC_ENABLED=false
```

### Backend (`backend/.env`)
Create `backend/.env` by copying `backend/.env.example`:

```ini
APP_ENV=development
LOG_LEVEL=DEBUG
API_PREFIX=/api/v1

DATABASE_URL=postgresql+psycopg://forteux:forteux_dev_password@localhost:5432/forteux

# Development Authentication Adapter
DEV_AUTH_ENABLED=true
DEV_AUTH_SECRET=forteux-local-dev-jwt-signing-secret-key-32bytes

# MinIO Local Storage
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET=forteux-private-screenshots
S3_ENDPOINT_URL=http://localhost:9000
S3_UPLOAD_TTL_SECONDS=300
S3_DOWNLOAD_TTL_SECONDS=300
MAX_UPLOAD_BYTES=10485760

ALLOWED_ORIGINS=http://localhost:3000
```

---

## 3. Starting, Stopping, and Resetting

### Starting the Environment (Docker Compose)
When Docker Desktop / Docker Engine is installed and running:

```bash
docker compose up -d
```

To view logs across all services:
```bash
docker compose logs -f
```

To run database migrations inside the backend container (if not automated by entrypoint):
```bash
docker compose exec backend alembic upgrade head
```

### Stopping the Environment
To stop containers without deleting data:
```bash
docker compose down
```
> [!NOTE]
> `docker compose down` preserves all database tables, users, projects, and MinIO files stored in the named volumes `forteux_postgres_data` and `forteux_minio_data`.

### Resetting the Environment (Destructive)
> [!CAUTION]
> Running the command below **PERMANENTLY DELETES ALL LOCAL DATA**, including PostgreSQL databases, tables, users, projects, audits, and all uploaded screenshots in MinIO!

```bash
docker compose down -v
```

---

## 4. Development Authentication Strategy

### How Dev Auth Works
1. In development (`APP_ENV=development` and `DEV_AUTH_ENABLED=true`), the backend provides `/api/v1/auth/dev-token`.
2. NextAuth uses a development credentials provider that requests a signed JWT from this endpoint.
3. The token contains standard OIDC claims (`iss="forteux-dev-auth"`, `sub`, `email`, `name`, `token_use="access"`, `client_id="forteux-dev-client"`).
4. On arrival at protected endpoints, FastAPI verifies the token, resolves or provisions a `User`, creates a personal `Tenant`, and assigns an `owner` `Membership`.
5. Frontend requests **never** provide user IDs or tenant IDs; authorization is strictly derived from the verified token.

### Production Security Isolation
- In `APP_ENV=production`, `DEV_AUTH_ENABLED=true` triggers an immediate `RuntimeError` at application startup.
- Dev tokens (`iss="forteux-dev-auth"`) presented to a production backend are rejected with `401 Unauthorized`.
- `/api/v1/auth/dev-token` returns `403 Forbidden` if invoked in production.

### How to Switch to Amazon Cognito (Production / Staging)
To switch to Cognito:
1. In `backend/.env`:
   - Set `DEV_AUTH_ENABLED=false`
   - Set `OIDC_ISSUER=https://cognito-idp.<region>.amazonaws.com/<user_pool_id>`
   - Set `OIDC_CLIENT_ID=<app_client_id>`
   - Set `OIDC_JWKS_URL=https://cognito-idp.<region>.amazonaws.com/<user_pool_id>/.well-known/jwks.json`
2. In `.env.local`:
   - Set `DEV_AUTH_ENABLED=false`
   - Set `NEXT_PUBLIC_DEV_AUTH_ENABLED=false`
   - Set `NEXT_PUBLIC_OIDC_ENABLED=true`
   - Set `COGNITO_ISSUER=https://cognito-idp.<region>.amazonaws.com/<user_pool_id>`
   - Set `COGNITO_CLIENT_ID=<app_client_id>`
   - Set `COGNITO_CLIENT_SECRET=<app_client_secret>`
3. Restart frontend and backend. The application will authenticate exclusively against Cognito via RS256 JWKS verification.

---

## 5. File Storage Strategy (MinIO vs AWS S3)

- **Private by Default**: MinIO bucket `forteux-private-screenshots` is configured with `mc anonymous set none`. No direct public downloads or listings are possible.
- **Server-Controlled URLs**: The backend issues short-lived presigned PUT URLs for uploads (after validating filename, declared content-type, and size limit) and presigned GET URLs for downloads (forcing `Content-Disposition: attachment`).
- **Head Verification**: Upload completion (`POST /api/v1/projects/{project_id}/assets/{asset_id}/complete`) verifies the object exists in MinIO and matches declared size and MIME type.
- **Switching to AWS S3**: Remove `S3_ENDPOINT_URL` (or leave empty) and ensure standard AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET`) or an IAM instance role are available.

---

## 6. Native / Local Development (Without Docker)

If running without Docker on the host machine:

### Backend:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="."
$env:APP_ENV="development"
$env:DEV_AUTH_ENABLED="true"
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\uvicorn.exe app.main:app --port 8000 --reload
```

### Frontend:
```powershell
npm run dev
```
Accessible at `http://localhost:3000`.
