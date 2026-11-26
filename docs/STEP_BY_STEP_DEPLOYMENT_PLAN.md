# Forteux Step-by-Step Production Deployment Plan

**Application:** Forteux — AI-Powered UI/UX Design Auditing & Intelligence Platform  
**Target Stack:**
- **Frontend:** Next.js 15 (App Router) on **Vercel**
- **Database & Auth & Storage:** **Supabase** (PostgreSQL + Auth + Storage + RLS)
- **AI Processing Backend:** **FastAPI** on Dedicated Container Service (**Railway**, **Google Cloud Run**, or **Render**)
- **AI Vision & LLM:** **Google Gemini API** (`gemini-1.5-flash` / `gemini-1.5-pro`)

---

## Deployment Status Tracker

| Phase | Description | Status | Details |
|---|---|---|---|
| **Phase 1** | Supabase Project, Schema & Auth | ✅ **COMPLETED** | Project `edlkpfrlsrgslcdwjykv` linked, 20 tables created, RLS enabled, `forteux-private-assets` bucket created, security hardening applied. |
| **Phase 2** | FastAPI Backend Deployment | ✅ **COMPLETED** | `forteux-api` deployed to Render (`srv-dc3tnbl9el5s739kfk4g`) via Blueprint sync. Live at https://forteux-api.onrender.com. Deploy `dep-dc3tnbt9el5s739kfldg` status: **live**. Deployed: 2026-11-26. |
| **Phase 3** | Vercel Frontend Deployment | ✅ **COMPLETED** | Deployed at https://forteux-app-musaabduljnr-gmailcoms-projects.vercel.app (SMOKE-01 verified: `/`, `/login`, `/register` HTTP 200; `/dashboard` HTTP 307; `/api/backend/projects` HTTP 401). |
| **Phase 4** | Production Smoke Testing | ⏳ **PENDING** | Verify user registration, Google OAuth, onboarding, audit analysis, bounding boxes, and exports. |
| **Phase 5** | Production Monitoring & Alerting | ⏳ **PENDING** | Uptime monitoring on `/health/live` and Vercel Analytics setup. |

---

## Architecture Flow

```
   [ User Browser ]
          │
          │ HTTPS (Requests to / & /api/backend/*)
          ▼
   [ Vercel: Next.js Frontend ]
      ├── Static & SSR Pages (Landing, Auth, Dashboard, Audits)
      ├── Supabase SSR Client (Cookie-based Sessions)
      └── Reverse Proxy (/api/backend/* ──► FastAPI backend with Authorization header)
          │
          ▼ HTTPS
   [ Container: FastAPI Backend ] (e.g. api.forteux.ai on Railway / Cloud Run)
      ├── JWT Verification (Validates Supabase Bearer token against JWKS)
      ├── Business Logic & AI Vision Analysis (Google Gemini API)
      ├── Async Background Tasks & Export Generation
      ├── Direct Storage Presigning (Supabase S3)
      └── Database Connection Pool (SQLAlchemy + asyncpg/psycopg)
          │
          ▼ SSL (Port 6543)
   [ Supabase Cloud ] (Project: edlkpfrlsrgslcdwjykv)
      ├── PostgreSQL 15+ (With RLS Policies & Profiles Sync Trigger)
      ├── Auth Engine (Email/Password, Google OAuth 2.0 PKCE)
      └── S3 Storage (`forteux-private-assets` Bucket)
```

---

## Phase 1: Supabase Configuration (COMPLETED ✅)

### 1.1 Project Information
- **Project Name:** `forteux-prod`
- **Project Reference ID:** `edlkpfrlsrgslcdwjykv`
- **Project URL:** `https://edlkpfrlsrgslcdwjykv.supabase.co`
- **Auth Endpoint:** `https://edlkpfrlsrgslcdwjykv.supabase.co/auth/v1`
- **Storage S3 Endpoint:** `https://edlkpfrlsrgslcdwjykv.supabase.co/storage/v1/s3`

### 1.2 Migrations & Schemas Applied
All schemas were pushed directly to the remote database and are tracked under [`supabase/migrations/`](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/supabase/migrations/):
1. **`20261119000001_core_schema.sql`**  
   ✅ 20 application tables created (`tenants`, `users`, `projects`, `audits`, `audit_screens`, `findings`, `knowledge_chunks`, `design_system_analyses`, `export_jobs`, etc.).  
   ✅ `alembic_version` stamped at head revision `0007_phase09_project_history_exports`.
2. **`20261119000002_user_profiles.sql`**  
   ✅ `public.profiles` created for user metadata, role, and onboarding steps.  
   ✅ `on_auth_user_created` trigger active on `auth.users` for automatic profile provisioning.
3. **`20261119000003_supabase_rls.sql`**  
   ✅ Row Level Security enabled across all tables with tenant isolation policies and `service_role` backend bypass.
4. **`20261119000004_storage_bucket.sql`**  
   ✅ Private bucket **`forteux-private-assets`** created (25MB file limit, restricted to images and PDFs) with folder-level user RLS.
5. **`20261119000005_security_hardening.sql`**  
   ✅ Security definer functions hardened with fixed `search_path`, public execution revoked on internal RPCs, and RLS initPlan subquery optimization applied.

### 1.3 Google OAuth & Auth URLs in Supabase Dashboard
To finalize Google OAuth in the Supabase Dashboard:
1. Go to **Authentication** -> **Providers** -> **Google**:
   - Toggle **Enable Google provider**.
   - **Client ID:** `1064517195987-3v6krdvapnhsaes5qe6thmqg8rf591qj.apps.googleusercontent.com`
   - **Client Secret:** Paste your Google Client Secret (`GOCSPX-...`).
   - Click **Save**.
2. Go to **Google Cloud Console** -> **Credentials** -> Your OAuth Client:
   - Ensure **Authorized redirect URI** contains:
     ```
     https://edlkpfrlsrgslcdwjykv.supabase.co/auth/v1/callback
     ```
3. In Supabase Dashboard -> **Authentication** -> **URL Configuration**:
   - **Site URL:** `https://app.forteux.ai` (or your initial Vercel domain)
   - **Redirect URLs:**
     - `https://app.forteux.ai/auth/callback`
     - `https://*.vercel.app/auth/callback`
     - `http://localhost:3000/auth/callback`

---

## Phase 2: FastAPI Backend Deployment (Dedicated Container)

> **Recommended Platform:** Railway, Google Cloud Run, or Render.  
> The repository already includes a verified, production-ready [backend/Dockerfile](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/Dockerfile).

### Step 2.1: Deploying on Railway (Recommended)
1. Log in to [Railway.app](https://railway.app).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select `musaabduljnr/forteux`.
4. In Settings:
   - **Root Directory:** `/backend`
   - **Builder:** Dockerfile (`/backend/Dockerfile`)
5. In **Variables**, add the following production environment variables:

| Variable | Value | Notes |
|---|---|---|
| `APP_ENV` | `production` | Enables strict production guards |
| `LOG_LEVEL` | `INFO` | Standard application logging |
| `API_PREFIX` | `/api/v1` | Base API prefix |
| `DATABASE_URL` | `postgresql+psycopg://postgres.edlkpfrlsrgslcdwjykv:<DB_PASSWORD>@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require` | Use Supabase Transaction Pooler (port 6543) |
| `OIDC_ISSUER` | `https://edlkpfrlsrgslcdwjykv.supabase.co/auth/v1` | Supabase Auth issuer |
| `OIDC_CLIENT_ID` | `authenticated` | Expected token audience |
| `OIDC_JWKS_URL` | `https://edlkpfrlsrgslcdwjykv.supabase.co/auth/v1/.well-known/jwks.json` | Public JWKS endpoint |
| `SUPABASE_URL` | `https://edlkpfrlsrgslcdwjykv.supabase.co` | Project URL |
| `SUPABASE_JWT_SECRET` | `<YOUR_SUPABASE_JWT_SECRET>` | Found in Supabase Settings -> API |
| `DEV_AUTH_ENABLED` | `false` | Must remain false in production |
| `AWS_REGION` | `eu-west-1` | Supabase project region |
| `AWS_ACCESS_KEY_ID` | `<SUPABASE_S3_ACCESS_KEY_ID>` | From Supabase Storage -> S3 Access Keys |
| `AWS_SECRET_ACCESS_KEY` | `<SUPABASE_S3_SECRET_ACCESS_KEY>` | From Supabase Storage -> S3 Access Keys |
| `S3_BUCKET` | `forteux-private-assets` | Target bucket name |
| `S3_ENDPOINT_URL` | `https://edlkpfrlsrgslcdwjykv.supabase.co/storage/v1/s3` | Storage S3 gateway |
| `ALLOWED_ORIGINS` | `https://app.forteux.ai,https://forteux.ai,https://*.vercel.app` | CORS origins |
| `GEMINI_API_KEY` | `<YOUR_GEMINI_API_KEY>` | Google AI Studio Gemini API key |

### Step 2.2: Networking & Health Check Verification
1. In Railway **Settings** -> **Networking**, click **Generate Domain** (e.g. `forteux-backend.up.railway.app`) or configure your custom domain `api.forteux.ai`.
2. Verify deployment readiness by visiting:
   ```
   https://<your-backend-url>/health/ready
   ```
   Expected response:
   ```json
   {
     "status": "ready",
     "database": "connected",
     "storage": "connected"
   }
   ```

---

## Phase 3: Vercel Frontend Deployment

### Step 3.1: Import Project into Vercel
1. Log in to [Vercel](https://vercel.com).
2. Click **Add New** -> **Project**.
3. Import the `musaabduljnr/forteux` repository.
4. Framework Preset: **Next.js** (auto-detected).
5. Root Directory: `./` (repository root).
6. Build Command: `npm run build`.
7. Output Directory: `.next`.

### Step 3.2: Configure Environment Variables on Vercel
Under **Settings** -> **Environment Variables**, add:

| Variable Name | Environments | Value |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Production, Preview | `https://edlkpfrlsrgslcdwjykv.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production, Preview | `<YOUR_SUPABASE_ANON_KEY>` |
| `SUPABASE_SERVICE_ROLE_KEY` | Production, Preview | `<YOUR_SUPABASE_SERVICE_ROLE_KEY>` |
| `BACKEND_API_URL` | Production | `https://<your-backend-url>/api/v1` |
| `BACKEND_API_URL` | Preview | `https://<your-backend-url>/api/v1` |
| `NEXTAUTH_URL` | Production | `https://app.forteux.ai` |
| `NEXTAUTH_URL` | Preview | `https://${VERCEL_URL}` |
| `NEXTAUTH_SECRET` | Production, Preview | `<GENERATE_32_BYTE_HEX_KEY>` |
| `DEV_AUTH_ENABLED` | Production, Preview | `false` |
| `NEXT_PUBLIC_DEV_AUTH_ENABLED` | Production, Preview | `false` |

*(To generate a random 32-byte secret in PowerShell: `[Convert]::ToHexString((1..32 | ForEach-Object { Get-Random -Maximum 256 }))`)*

### Step 3.3: Deploy & Configure Domains
1. Click **Deploy**. Vercel will install dependencies and compile all Next.js routes.
2. In **Settings** -> **Domains**:
   - Add apex domain: `forteux.ai`
   - Add app subdomain: `app.forteux.ai`
3. Point your DNS records to Vercel:
   - `CNAME` for `app` -> `cname.vercel-dns.com`
   - `A` record for `@` -> `76.76.21.21`

---

## Phase 4: Production Verification & Smoke Testing

Once both services are deployed, perform the following verification walkthrough:

| Test ID | Test Flow | Verification Step | Expected Result |
|---|---|---|---|
| **SMOKE-01** | Public Landing | Open `https://forteux.ai` | Landing page loads with responsive styles, navigation, and zero console errors. |
| **SMOKE-02** | Registration | Go to `/register` and submit email/password | User created in Supabase Auth; row inserted into `public.profiles`; redirects to `/onboarding`. |
| **SMOKE-03** | Onboarding | Complete 4-step wizard | Onboarding fields saved; `onboarding_completed=true`; redirects to `/dashboard`. |
| **SMOKE-04** | Google OAuth | Log out, click **Continue with Google** | Google consent screen displays; redirects to `/auth/callback` then `/dashboard`. |
| **SMOKE-05** | Project Creation | Click **New Project** in dashboard | Project stored in Supabase with authenticated user UUID. |
| **SMOKE-06** | Single Audit | Upload UI screenshot and run audit | Image presigned to Supabase Storage; FastAPI Gemini vision audit runs; findings and bounding boxes display. |
| **SMOKE-07** | Design System | Run extraction on audit | Design tokens, typography, and color palette extracted successfully. |
| **SMOKE-08** | Stitch Prompt | Select findings and generate prompt | Comprehensive Google Stitch redesign prompt generated. |
| **SMOKE-09** | Export | Download audit report (JSON/PDF) | Export file generated and downloaded cleanly. |
| **SMOKE-10** | Tenant Isolation | Log in as User B | User B cannot view User A's projects, audits, or screenshots (enforced by RLS). |

---

## Phase 5: Monitoring, Alerting & Rollback Strategy

1. **Uptime Monitoring:**  
   Configure uptime monitoring (BetterStack, UptimeRobot, or Cloudflare Health Checks) pinging:
   - Frontend: `https://app.forteux.ai` (every 5 minutes)
   - Backend: `https://<your-backend-url>/health/live` (every 60 seconds)
2. **Instant Rollback:**
   - **Frontend (Vercel):** Go to Deployments, find the previous stable deployment, and click **Rollback**.
   - **Backend (Railway):** Go to Deployments, select previous deployment revision, click **Redeploy**.
3. **Database Safeguards:**
   - Supabase automatically performs continuous daily WAL backups.
   - For major version upgrades or schema changes, take a manual backup in **Supabase Dashboard** -> **Database** -> **Backups**.
