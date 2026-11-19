# Production Monitoring, Logging, Observability & Disaster Recovery Runbook

**Target Systems:** Vercel (Frontend), FastAPI Container (Backend), Supabase (PostgreSQL, Auth, Storage)

---

## 1. Observability & Health Monitoring

### 1.1 Health Check Endpoints
The FastAPI backend exposes two decoupled health probes in [backend/app/main.py](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/app/main.py):

1. **Liveness Probe: `GET /health/live`**
   - **Response:** `{"status": "live"}` (HTTP 200)
   - **Purpose:** Used by container orchestrators (e.g., Cloud Run, Kubernetes, ECS) to verify the process is alive. Does not depend on external services to prevent cascade restarts during database blips.
2. **Readiness Probe: `GET /health/ready`**
   - **Response:** `{"status": "ready", "checks": {"database": "ready", "authentication": "configured", "object_storage": "ready"}}` (HTTP 200 or 503)
   - **Checks:**
     - Executes `SELECT 1` against PostgreSQL via connection pool.
     - Verifies OIDC configuration and JWKS readiness.
     - Performs S3 bucket connectivity check via `S3Storage.healthcheck()`.

### 1.2 Structured Application Logging
- FastAPI logs adhere to standard production formatting:
  `%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s`
- The `request_id` is propagated from incoming `X-Request-ID` headers or auto-generated as a UUIDv4.
- Sensitive credentials (passwords, JWT secrets, bearer tokens) are filtered before logging.

---

## 2. Inspecting Production Logs

### 2.1 Vercel Deployment & Runtime Logs
1. Navigate to your project on the [Vercel Dashboard](https://vercel.com/dashboard).
2. Go to **Deployments** -> select active deployment -> **Runtime Logs**.
3. Filter by status (e.g. `5xx` or `4xx`) or search by `x-request-id`.

### 2.2 Supabase Database & Auth Logs
1. Open the [Supabase Dashboard](https://supabase.com/dashboard) -> Select Project.
2. Go to **Logs** -> **Postgres Logs** to inspect connection counts, slow queries, or RLS denials.
3. Go to **Logs** -> **Auth Logs** to inspect login failures, OAuth errors, or rate limits.

### 2.3 Backend Container Logs
- **Google Cloud Run / AWS CloudWatch / Railway:**
  View real-time stream logs with query:
  `resource.type="cloud_run_revision" textPayload=~"ERROR"`

---

## 3. Incident Recovery & Rollback Procedures

### 3.1 Instant Frontend Rollback (Vercel)
If a faulty frontend release is deployed:
1. Go to Vercel Dashboard -> **Deployments**.
2. Find the previous stable deployment.
3. Click the three dots (`...`) -> **Promote to Production**.
4. Traffic routes instantly to the previous build without rebuilding.

### 3.2 Database Backup & Point-in-Time Recovery (PITR)
Supabase automatically manages daily backups and physical WAL archiving:
1. In the Supabase dashboard, go to **Settings** -> **Database** -> **Backups**.
2. To restore:
   - For scheduled backups: select the snapshot date and click **Restore**.
   - For PITR (Point-in-Time Recovery): select the exact timestamp down to the minute prior to the incident.

### 3.3 Failed Job Recovery
If an analysis or export job is interrupted by a container restart:
1. The job record in `analysis_jobs` or `export_jobs` will display status `failed` or remain in `pending`.
2. Users can trigger a re-run from the UI (clicking **Re-analyze** on the audit or **Regenerate** in the exports center).
3. The backend executes idempotently without duplicate record creation.
