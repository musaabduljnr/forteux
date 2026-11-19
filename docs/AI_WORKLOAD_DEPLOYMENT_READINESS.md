# AI Workload & Background Processing Deployment Readiness

**Document Objective:** Analyze compute duration, resource limits, and job state persistence for Forteux AI workflows.

---

## 1. Operational Classification: Synchronous vs. Asynchronous Jobs

| Workload | Typical Duration | Processing Model | Persistence Mechanism | Serverless Risk |
|---|---|---|---|---|
| **Single-Screen Vision Audit** | 4s – 12s | Request-Response | Stored in `findings` & `analysis_jobs` | Low to Moderate (within 15s) |
| **Multi-Screen Journey Flow** (2–12 screens) | 15s – 45s | Synchronous Orchestration / Polled Status | Stored in `analysis_jobs` & `findings` | **High Risk of 504 on Serverless** |
| **Knowledge PDF/DOCX Ingestion** (up to 20MB) | 3s – 18s | Chunking & Embedding Generation | Stored in `knowledge_documents` & `knowledge_chunks` | Moderate |
| **RAG Vector Similarity Query** | 100ms – 400ms | Request-Response | In-memory similarity over `knowledge_chunks` / pgvector | None |
| **Design System Token Extraction** | 2s – 6s | Request-Response | Stored in `design_system_analyses` | None |
| **Google Stitch Prompt Generation** | 1s – 4s | Request-Response | Stored in `audit_prompts` | None |
| **Export Job Generation** (PDF / CSV / JSON) | 1s – 5s | Job-based with download URL | Stored in `export_jobs` & Supabase Storage | None |

---

## 2. Job State Persistence Guarantees

Every asynchronous or multi-step operation in Forteux satisfies production reliability criteria:

1. **Database-Backed Job Records:**
   - Analysis operations persist in the `analysis_jobs` table.
   - Export operations persist in the `export_jobs` table.
   - Knowledge indexing operations persist in the `knowledge_documents` table.
   - **Zero reliance on in-memory state.** If the backend process restarts, job records and completed findings remain fully intact in PostgreSQL.
2. **Tenant & User Ownership:**
   - Every job record enforces `tenant_id` and `user_id` foreign keys, preventing unauthorized job status snooping or resource modification.
3. **Failure State Capture:**
   - Any unhandled exception during image vision analysis or document extraction transitions the job status to `failed` and records the diagnostic code in `error_code` / `error_message`.
4. **Idempotency & Re-run Safety:**
   - Multi-screen audits and design system extractions update or create versioned entries cleanly without corrupting previous baseline comparisons.

---

## 3. Serverless vs. Container Recommendation for AI Jobs

- **The Problem with Serverless Background Tasks:**
  FastAPI's built-in `BackgroundTasks` cannot guarantee completion inside serverless functions (like AWS Lambda or Vercel Functions) because the container runtime is frozen immediately after the HTTP response stream closes.
- **The Container Advantage:**
  Running FastAPI in a container environment (such as Google Cloud Run, Railway, or AWS App Runner) allows background threads, active DB connections, and long-running Gemini API calls to complete without premature termination.
