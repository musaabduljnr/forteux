# FastAPI Production Deployment Strategy: Vercel vs. Dedicated Container Hosting

**Document Objective:** Evaluate deployment options for the Forteux FastAPI backend and recommend the optimal hosting architecture for production AI workloads, background processing, and Supabase database interactions.

---

## 1. Executive Summary & Recommendation

| Criterion | Option A: FastAPI on Vercel Serverless | Option B: Dedicated Container (Cloud Run / Railway / Render / Fly.io) |
|---|---|---|
| **Max Execution Duration** | 10s (Hobby) / 60s–300s (Pro) | Unlimited / Configurable (e.g., 10–30 mins) |
| **Multi-Screen Vision Jobs** | **High Risk of 504 Timeout** (12 screens take 20–45s) | **Fully Supported** without duration pressure |
| **PDF Extraction & Chunking** | Can timeout on >20MB documents | Runs efficiently in persistent memory |
| **Background Processing** | **Incompatible** (Processes frozen on HTTP response) | **Supported** (Background threads / queue workers remain alive) |
| **Binary/Native Dependencies** | Bundling risk with `psycopg`, `pillow`, `pypdf` | Fully isolated in Linux container (`python:3.11-slim`) |
| **Cold Starts** | 2–6 seconds per cold invocation | 0s (Persistent instance or warm min-instances) |
| **Database Connections** | High connection churn on PostgreSQL | Persistent connection pool managed by SQLAlchemy |
| **Operational Simplicity** | Single Vercel dashboard | Dedicated backend URL (e.g., `api.forteux.ai`) |

### Recommended Decision: **Option B (Dedicated Container Hosting)**
We strongly recommend deploying the FastAPI backend as a dedicated container service (such as **Google Cloud Run**, **Railway**, **Render**, or **Fly.io**), paired with the Next.js frontend hosted on **Vercel**.

**Why?**
1. **Serverless Freezing Problem:** In serverless functions (like Vercel Python runtime), CPU execution is immediately frozen once the HTTP response is returned. In-process background tasks (`analysis_jobs`, async export generation) are terminated mid-flight.
2. **Workload Duration:** A multi-screen audit evaluating 12 screens against design consistency rules requires 20–45 seconds. On standard Vercel plans, this triggers a `504 Gateway Timeout`.
3. **Existing Docker Readiness:** The repository already includes a verified `backend/Dockerfile` with production health checks, multi-stage dependencies, and Alembic auto-migration on boot.

---

## 2. Technical Evaluation: Option A (FastAPI on Vercel)

If the team opts for single-platform hosting on Vercel:
- **Implementation Mechanism:** Expose FastAPI through `api/index.py` using `@vercel/python`.
- **API Rewrites:** In `vercel.json`:
  ```json
  {
    "rewrites": [
      { "source": "/api/v1/:path*", "destination": "/api/index.py" }
    ]
  }
  ```
- **Mandatory Requirements if Option A is chosen:**
  1. Vercel **Pro** plan is mandatory to configure `maxDuration: 60`.
  2. All long-running background tasks must be converted to an external queue (e.g., QStash / Inngest / Supabase Edge Functions) because FastAPI `BackgroundTasks` will fail.
  3. Supabase PgBouncer / Supavisor connection pooling must be used (`:6543`).

---

## 3. Technical Evaluation: Option B (Dedicated Container Hosting)

### 3.1 Recommended Deployment Targets
1. **Google Cloud Run:** Fully managed serverless container platform with automatic scale-to-zero, request concurrency up to 80 requests/container, and up to 60-minute timeout.
2. **Railway / Render:** Simple Git-based container deployment with automatic TLS and zero cold starts.
3. **AWS App Runner / ECS:** Enterprise-grade container hosting with direct VPC peering.

### 3.2 Production Run Configuration
- **Dockerfile:** `backend/Dockerfile`
  - Base: `python:3.11-slim`
  - Native tools: `gcc`, `libpq-dev`, `curl`
  - Command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Health Checks:**
  - Liveness probe: `GET /health/live` (status 200)
  - Readiness probe: `GET /health/ready` (checks PostgreSQL and Supabase Storage connectivity)

### 3.3 Frontend-to-Backend Routing
The Next.js frontend interacts with FastAPI via the internal proxy route [app/api/backend/[...path]/route.ts](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/app/api/backend/[...path]/route.ts).
- In production, set `BACKEND_API_URL=https://api.forteux.ai/api/v1` on Vercel.
- The browser only communicates with Vercel (`https://app.forteux.ai/api/backend/*`), completely eliminating CORS issues for client browsers.
- Server-to-server TLS secures all traffic between Vercel and the FastAPI container.
