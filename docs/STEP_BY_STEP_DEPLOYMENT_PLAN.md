# Forteux Step-by-Step Production Deployment Plan

**Application:** Forteux — AI-Powered UI/UX Design Auditing & Intelligence Platform  
**Target Stack:**
- **Frontend:** Next.js 15 (App Router) on **Vercel**
- **Database & Auth & Storage:** **Supabase** (PostgreSQL + Auth + Storage + RLS)
- **AI Processing Backend:** **FastAPI** on Dedicated Container Service (**Railway**, **Google Cloud Run**, or **Render**)
- **AI Vision & LLM:** **Google Gemini API** (`gemini-1.5-flash` / `gemini-1.5-pro`)

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
   [ Container: FastAPI Backend ] (e.g. api.forteux.ai)
      ├── JWT Verification (Validates Supabase Bearer token against JWKS)
      ├── Business Logic & AI Vision Analysis (Google Gemini API)
      ├── Async Background Tasks & Export Generation
      ├── Direct Storage Presigning (Supabase S3)
      └── Database Connection Pool (SQLAlchemy + asyncpg/psycopg)
          │
          ▼ SSL (Port 6543 / 5432)
   [ Supabase Cloud ]
      ├── PostgreSQL 15+ (With RLS Policies & Profiles Sync Trigger)
      ├── Auth Engine (Email/Password, Google OAuth 2.0 PKCE)
      └── S3 Storage (`forteux-private-assets` Bucket)
```

---

## Pre-Deployment Checklist & Accounts Required

Before starting, ensure you have active accounts for:
1. **GitHub:** Repository access (`https://github.com/musaabduljnr/forteux`)
2. **Supabase Cloud:** `https://supabase.com`
3. **Google Cloud Console:** `https://console.cloud.google.com` (for Google OAuth credentials & Gemini API key from AI Studio)
4. **FastAPI Container Host:** **Railway** (`https://railway.app`) or **Google Cloud Run**
5. **Vercel:** `https://vercel.com`

---

## Phase 1: Supabase Configuration

### Step 1.1: Create New Supabase Project
1. Log in to [Supabase Dashboard](https://supabase.com/dashboard).
2. Click **New Project**.
3. Select your Organization, name the project `forteux-prod`, and choose a database region closest to your primary user base (e.g., `us-east-1` Washington D.C. or `eu-central-1` Frankfurt).
4. Save the **Database Password** in a secure password manager.

### Step 1.2: Retrieve Project Credentials
Go to **Project Settings** -> **API** and copy:
- `Project URL` (e.g., `https://abcdefghijklm.supabase.co`)
- `Project Reference ID` (e.g., `abcdefghijklm`)
- `anon public` key
- `service_role secret` key
- `JWT Secret`

Go to **Project Settings** -> **Database** and copy:
- **Connection Pooling String (Transaction mode, port 6543)**:
  `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`

### Step 1.3: Run Database Migrations & Schemas
Open **Supabase Dashboard** -> **SQL Editor** and execute the following scripts in order:

1. **Alembic Base Schema:**
   Run migrations from your local repository to create the core tables:
   ```bash
   cd backend
   # Set DATABASE_URL to your Supabase connection string
   $env:DATABASE_URL="postgresql+psycopg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require"
   alembic upgrade head
   ```
2. **User Profiles Table & Auto-Sync Trigger:**
   Run the contents of [backend/migrations/create_user_profiles.sql](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/migrations/create_user_profiles.sql) in Supabase SQL Editor.
   *(This automatically creates a row in `public.profiles` whenever a user registers via email or Google OAuth).*
3. **Row Level Security (RLS) Policies:**
   Run the contents of [backend/migrations/supabase_rls.sql](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/migrations/supabase_rls.sql) in Supabase SQL Editor.
   *(This guarantees tenant data isolation on projects, screens, audits, and findings).*

### Step 1.4: Configure Storage Bucket & S3 Credentials
1. Go to **Storage** in the Supabase sidebar.
2. Click **New Bucket**:
   - Name: `forteux-private-assets`
   - Public bucket: **Disabled (Private)**
   - Allowed MIME types: `image/png, image/jpeg, image/webp, application/pdf`
   - Max file size: `25MB`
3. Generate S3 Access Keys for FastAPI:
   - Go to **Project Settings** -> **Storage** -> **S3 Access Keys**.
   - Click **Generate New Key**.
   - Copy `Access Key ID` and `Secret Access Key`.

### Step 1.5: Configure Google OAuth 2.0
1. Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials).
2. Configure **OAuth consent screen** (App name: Forteux, Support email, User type: External).
3. Create an **OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Authorized redirect URIs:
     - `https://<your-project-ref>.supabase.co/auth/v1/callback`
4. Copy `Client ID` and `Client Secret`.
5. Back in **Supabase Dashboard** -> **Authentication** -> **Providers** -> **Google**:
   - Enable Google provider.
   - Paste `Client ID` and `Client Secret`.
   - Save.
6. In **Authentication** -> **URL Configuration**:
   - **Site URL:** `https://app.forteux.ai` (or your production Vercel URL)
   - **Redirect URLs:** Add:
     - `https://app.forteux.ai/auth/callback`
     - `https://*.vercel.app/auth/callback` (for branch previews)
     - `http://localhost:3000/auth/callback` (for local development)

---

## Phase 2: FastAPI Backend Deployment (Dedicated Container)

> **Recommended Platform:** Railway, Google Cloud Run, or Render.  
> The repository already contains a production-ready [backend/Dockerfile](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/Dockerfile).

### Option A: Deploying on Railway (Easiest & Fastest)
1. Log in to [Railway.app](https://railway.app).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select `musaabduljnr/forteux`.
4. In Settings:
   - **Root Directory:** `/backend`
   - **Builder:** Dockerfile (`/backend/Dockerfile`)
5. In **Variables**, add the following environment variables:

| Variable | Value |
|---|---|
| `APP_ENV` | `production` |
| `LOG_LEVEL` | `INFO` |
| `API_PREFIX` | `/api/v1` |
| `DATABASE_URL` | `postgresql+psycopg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require` |
| `OIDC_ISSUER` | `https://<ref>.supabase.co/auth/v1` |
| `OIDC_CLIENT_ID` | `authenticated` |
| `OIDC_JWKS_URL` | `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `SUPABASE_JWT_SECRET` | `<your-supabase-jwt-secret>` |
| `DEV_AUTH_ENABLED` | `false` |
| `AWS_REGION` | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | `<supabase-s3-access-key-id>` |
| `AWS_SECRET_ACCESS_KEY` | `<supabase-s3-secret-access-key>` |
| `S3_BUCKET` | `forteux-private-assets` |
| `S3_ENDPOINT_URL` | `https://<ref>.supabase.co/storage/v1/s3` |
| `ALLOWED_ORIGINS` | `https://app.forteux.ai,https://forteux.ai,https://*.vercel.app` |
| `GEMINI_API_KEY` | `<your-google-ai-studio-gemini-key>` |

6. In **Settings** -> **Networking**, click **Generate Domain** or assign custom domain `api.forteux.ai`.
7. **Verify deployment:**
   Send a GET request to:
   `https://api.forteux.ai/health/ready`
   Should return: `{"status": "ready", "database": "connected", "storage": "connected"}`.

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

### Step 3.2: Set Environment Variables on Vercel
Under **Settings** -> **Environment Variables**, configure:

| Variable Name | Environments | Value |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Production, Preview | `https://<your-project-ref>.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production, Preview | `<your-supabase-anon-key>` |
| `SUPABASE_SERVICE_ROLE_KEY` | Production, Preview | `<your-supabase-service-role-key>` |
| `BACKEND_API_URL` | Production | `https://api.forteux.ai/api/v1` |
| `BACKEND_API_URL` | Preview | `https://api.forteux.ai/api/v1` |
| `NEXTAUTH_URL` | Production | `https://app.forteux.ai` |
| `NEXTAUTH_URL` | Preview | `https://${VERCEL_URL}` |
| `NEXTAUTH_SECRET` | Production, Preview | `<generate-32-byte-hex-string>` |
| `DEV_AUTH_ENABLED` | Production, Preview | `false` |
| `NEXT_PUBLIC_DEV_AUTH_ENABLED` | Production, Preview | `false` |

*(To generate a 32-byte secret in PowerShell: `[Convert]::ToHexString((1..32 | ForEach-Object { Get-Random -Maximum 256 }))`)*

### Step 3.3: Deploy & Configure Domains
1. Click **Deploy**. Vercel will install dependencies and compile the Next.js App Router routes.
2. In **Settings** -> **Domains**:
   - Add your apex domain: `forteux.ai`
   - Add your app subdomain: `app.forteux.ai`
3. Configure your DNS provider (e.g. Cloudflare, Namecheap, Route 53):
   - `CNAME` for `app` -> `cname.vercel-dns.com`
   - `A` record for `@` -> `76.76.21.21`

---

## Phase 4: Production Verification & Smoke Testing

Once both services are deployed, perform the following end-to-end verification tests:

| Step | Test Description | Expected Result |
|---|---|---|
| **1** | Navigate to `https://forteux.ai` | Landing page renders with responsive styling, navigation, and features |
| **2** | Click **Get Started** or visit `/register` | Registration form renders without hydration errors |
| **3** | Register a new user with email & password | User profile created in Supabase `profiles` table; redirects to `/onboarding` |
| **4** | Complete 4-step onboarding | Onboarding marks profile complete; redirects to `/dashboard` with dynamic greeting |
| **5** | Log out and click **Sign in with Google** | Google OAuth consent loads; redirects back to `/dashboard` successfully |
| **6** | Create a Project | Project row stored in Supabase with user's UUID |
| **7** | Upload screenshot & run audit | Image presigned to Supabase Storage; FastAPI triggers Gemini vision audit; findings with bounding boxes display |
| **8** | Check RLS Isolation | In Supabase, create a 2nd user; verify 2nd user cannot view 1st user's projects or audits |
| **9** | Test Export Feature | Download PDF/JSON report of audit findings; file downloads successfully |

---

## Phase 5: Monitoring, Alerting & Rollback Strategy

1. **Vercel Web Analytics & Speed Insights:**
   Enable under Vercel Dashboard -> **Analytics** to monitor Core Web Vitals and 5xx errors.
2. **FastAPI Health Monitoring:**
   Configure an uptime monitor (e.g. BetterStack, UptimeRobot) pinging:
   - `https://api.forteux.ai/health/live` every 60 seconds
3. **Rollback Plan:**
   - **Frontend:** In Vercel Deployments tab, click `...` next to the previous healthy deployment and select **Instant Rollback**.
   - **Backend:** In Railway/Cloud Run, select the prior deployment revision and click **Rollback**.
4. **Database Backups:**
   Supabase automatically takes daily WAL backups. Before any schema alterations, take a manual backup in **Supabase Dashboard** -> **Database** -> **Backups**.
