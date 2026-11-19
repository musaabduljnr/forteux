# Forteux Production Deployment Readiness Audit

**Target Stack:**
- **Frontend Hosting:** Vercel (Next.js 15 App Router)
- **Primary Backend Infrastructure:** Supabase (PostgreSQL, Auth, Storage, pgvector, RLS)
- **AI Processing Backend:** FastAPI
- **Background Processing:** Job persistence via PostgreSQL (`analysis_jobs`, `export_jobs`)

---

## 1. Executive Summary

This initial audit assesses the deployment readiness of the Forteux UI/UX design auditing platform across its frontend, backend, database, authentication, storage, and AI processing layers.

Forteux operates as a coordinated multi-tier platform:
1. **Next.js 15 Frontend** located at the repository root (`/`).
2. **FastAPI Backend** located in `/backend`.
3. **Supabase Managed Services** providing identity, PostgreSQL database, row-level security, and private object storage.

---

## 2. Component Inventory & Classification

| Component / Layer | Location | Current State | Deployment Status | Details / Actions Required |
|---|---|---|---|---|
| **Frontend Framework** | Root (`/app`, `/components`) | Next.js 15.5.29, React 19.1.1, App Router | **Ready** | Compiles cleanly (`tsc --noEmit` exit 0). Dynamic and static routes verified. |
| **Frontend Package Management** | `package.json`, `package-lock.json` | npm, 343 audited packages | **Ready** | Standard npm install and build commands. |
| **Frontend Routing & SSR** | `app/`, `middleware.ts` | App Router with Supabase `@supabase/ssr` middleware | **Ready** | Public landing page, auth routes, onboarding, and dashboard routing verified. |
| **FastAPI Backend** | `/backend` | Python 3.11+, FastAPI 0.122.0, Uvicorn | **Requires Configuration** | Clean architecture; requires hosting strategy decision (Vercel Serverless vs Container). |
| **Database Schema** | `backend/migrations/` | PostgreSQL with Alembic (0001–0007) + Supabase RLS | **Ready** | Schema migrations complete. Multi-tenant RLS policies verified. |
| **Authentication** | `lib/supabase/`, `app/(auth)/` | Supabase Auth (Email + Google OAuth) | **Requires External Credentials** | Fully implemented; requires Supabase project credentials and Google OAuth keys. |
| **Google OAuth** | `app/auth/callback/route.ts` | PKCE code exchange with auto-onboarding | **Requires External Credentials** | Redirect URIs documented; pending Google Cloud Console client configuration. |
| **File Storage** | `backend/app/services/storage.py` | S3-compatible protocol via `boto3` | **Requires Configuration** | Compatible with Supabase Storage S3 endpoint (`/storage/v1/s3`); bucket setup needed. |
| **AI Provider** | `backend/app/services/` | Gemini Vision & Language API | **Requires External Credentials** | Real API calls configured; fallback to deterministic benchmarks when key absent. |
| **Background Processing** | `analysis_jobs`, `export_jobs` | DB-backed status tracking | **Requires Architectural Decision** | Job records persisted; worker execution constraints evaluated in Task 4. |
| **API Proxy & Communication** | `app/api/backend/[...path]` | Next.js route proxy forwarding Supabase JWT | **Ready** | Handles CORS-free browser-to-backend communication. |
| **Automated Tests** | `backend/tests/` | 159 pytest tests | **Ready** | 100% passing (benchmarks, vision, RAG, RLS, auth). |
| **CI/CD** | `.github/workflows/` | None currently present | **Requires Implementation** | GitHub Actions workflow to be defined. |
| **Git Configuration** | `.git` | Remote: `musaabduljnr/forteux.git` | **Ready** | Clean branch topology. |

---

## 3. Directory Layout & Root Determination

- **Monorepo Topology:** Hybrid repository containing Next.js at the root and FastAPI inside `backend/`.
- **Vercel Root Directory:** The Vercel project root must be set to `.` (the repository root). Vercel natively detects `next.js` in `package.json`.
- **Backend Application Root:** `backend/` with entrypoint `app.main:app`.

---

## 4. Key Risks & Architectural Considerations

1. **AI Processing Function Duration:**
   - Multi-screen audits (up to 12 screens) and large document RAG chunking take between 5 to 45 seconds. Serverless function timeout limits (10s on Vercel Hobby, 60s on Pro) make containerized or persistent hosting for FastAPI strongly advisable if multi-screen audits are run synchronously.
2. **Database Pooling with Serverless:**
   - Supabase Supavisor / PgBouncer connection pooling (`:6543/postgres?sslmode=require`) must be used for SQLAlchemy to prevent connection pool exhaustion.
3. **Environment Segregation:**
   - Vercel Preview deployments must be isolated from production database tables and storage assets.
