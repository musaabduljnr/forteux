# Forteux Production Release Checklist & Operational Runbook

**Version**: 1.0.0  
**Target Release**: Production Launch  
**Platform**: Forteux (FastAPI + Next.js + Supabase)

---

## 1. Pre-Deployment Verification Checklist

- [x] **Automated Regression Suite**: 159 / 159 backend tests passing (`pytest tests/`).
- [x] **Static Type Check**: Zero TypeScript errors (`npx tsc --noEmit`).
- [x] **Frontend Route Health**: Next.js App Router responds with HTTP 200 on all primary routes.
- [x] **Database Migrations Tested**: Alembic migrations `0001` through `0007` execute cleanly.
- [x] **Row Level Security DDL Ready**: `backend/migrations/supabase_rls.sql` verified for all tables.
- [x] **Production Guards Active**: `DEV_AUTH_ENABLED=false` enforced when `APP_ENV=production`.
- [x] **TLS Enforced**: Database URLs validate `sslmode=require`.
- [x] **Storage S3 Compatibility**: Presigned upload and download flows verified against Supabase S3 API.
- [x] **AI Model Fallback**: Deterministic fallbacks verified if external AI APIs encounter rate limits.

---

## 2. Production Deployment Execution Sequence

### Step 1: Provision & Configure Supabase Project
1. Log in to [Supabase Console](https://supabase.com).
2. Create project `forteux-production` in the desired region.
3. In Project Settings $\to$ Database:
   - Note the **Connection Pooling URI** (`aws-0-<region>.pooler.supabase.com:6543`).
4. In Project Settings $\to$ API:
   - Note the Project URL (`https://<ref>.supabase.co`).
   - Note the Public Anon Key and Secret Service Role Key.
5. In Storage $\to$ Buckets:
   - Create a private bucket: `forteux-private-assets`.
   - In Storage Settings $\to$ S3 Credentials, generate an S3 Access Key ID and Secret Key.

### Step 2: Apply Database Schema & RLS Policies
1. In local deployment shell or CI/CD runner:
   ```bash
   cd backend
   export DATABASE_URL="postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require"
   alembic upgrade head
   ```
2. In Supabase SQL Editor:
   - Open and execute `backend/migrations/supabase_rls.sql`.
   - Verify `CREATE EXTENSION IF NOT EXISTS vector;` executes successfully.

### Step 3: Deploy Backend (FastAPI on Google Cloud Run or AWS ECS)
1. Build and push production container:
   ```bash
   docker build -t gcr.io/forteux-prod/backend:v1.0.0 ./backend
   ```
2. Deploy container setting environment variables matching `backend/.env.supabase.example`.
3. Set minimum instances to 1, CPU allocation to always allocated, and timeout to 300s.

### Step 4: Deploy Frontend (Next.js 15 on Google Cloud Run / Vercel)
1. Configure frontend build environment:
   ```env
   BACKEND_API_URL=https://api.forteux.ai/api/v1
   NEXTAUTH_URL=https://app.forteux.ai
   NEXTAUTH_SECRET=<generated-secret>
   NEXT_PUBLIC_DEV_AUTH_ENABLED=false
   NEXT_PUBLIC_OIDC_ENABLED=true
   ```
2. Build and deploy frontend.

---

## 3. Post-Deployment Smoke Tests

Execute these verification checks immediately following release:

1. **Liveness & Readiness Health Probes**:
   ```bash
   curl -f https://api.forteux.ai/health/live
   curl -f https://api.forteux.ai/health/ready
   ```
2. **User Authentication Flow**:
   - Log in using Supabase Auth on `https://app.forteux.ai`.
   - Verify JWT token contains valid `sub` and `tenant_id`.
3. **Screenshot Intake & Bounding Box Rendering**:
   - Create a new project and submit a test audit.
   - Verify presigned S3 upload completes without CORS or authorization errors.
   - Verify interactive bounding box canvas renders on the audit detail page.
4. **Export Generation**:
   - Generate a JSON and Markdown export from `/projects/[projectId]`.
   - Verify export job downloads cleanly from `/exports`.

---

## 4. Rollback Procedure

If a critical failure occurs during deployment:
1. **Frontend Rollback**:
   - Switch active traffic to previous deployment revision in Cloud Run / Vercel.
2. **Backend Rollback**:
   - Route traffic back to the prior stable backend container tag.
3. **Database Schema Rollback**:
   - If a migration caused failures:
     ```bash
     cd backend
     alembic downgrade -1
     ```

---

## 5. Operational Runbook & Alerting

- **Error Monitoring**: Connect Sentry or Google Cloud Error Reporting for exception capture.
- **Uptime Monitoring**: Configure synthetic HTTP checks on `https://api.forteux.ai/health/live` every 60 seconds.
- **Database Connection Alerts**: Alert if Supavisor pooled connection utilization exceeds $80\%$.
- **AI Outage Protocol**: The backend automatically falls back to deterministic heuristics if Gemini APIs return 429 or 503 errors.
