# Supabase Production Readiness Guide

**Target Environment:** Managed Supabase Project (PostgreSQL 15+, Supabase Auth, Supabase Storage, pgvector)

---

## 1. Executive Summary

This document verifies the production readiness of Supabase services for Forteux, establishing the schema migration path, Row Level Security policies, storage bucket configurations, and connection pooling rules.

---

## 2. Database Schema & Migration Strategy

### 2.1 Single Source of Truth
To prevent drift between Alembic and the Supabase CLI:
1. **Core Relational Schema:** Managed via Alembic migrations (`backend/migrations/versions/0001` through `0007_phase09_project_history_exports.py`).
2. **PostgreSQL Security & RLS Policies:** Applied via [backend/migrations/supabase_rls.sql](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/migrations/supabase_rls.sql).
3. **User Profiles & Auth Triggers:** Applied via [backend/migrations/create_user_profiles.sql](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/migrations/create_user_profiles.sql).

### 2.2 Execution Order for Production Setup
When provisioning or preparing the production Supabase database:
```bash
# Step 1: Run core schema migrations
cd backend
alembic upgrade head

# Step 2: Apply Supabase User Profiles & Triggers
psql "$DATABASE_URL" -f migrations/create_user_profiles.sql

# Step 3: Apply Row Level Security Policies
psql "$DATABASE_URL" -f migrations/supabase_rls.sql
```

---

## 3. Row Level Security (RLS) Verification

Every table exposed to client access or tenant data has RLS enabled:

| Table | RLS Status | Policy Summary |
|---|---|---|
| `public.profiles` | **Enabled** | Users can only `SELECT`, `INSERT`, `UPDATE` their own row (`id = auth.uid()`). Service role has full bypass. |
| `public.tenants` | **Enabled** | Enforces isolation by `current_tenant_id()`. |
| `public.memberships` | **Enabled** | Enforces user-tenant membership boundaries. |
| `public.projects` | **Enabled** | Access restricted to tenant owners and members. |
| `public.audits` | **Enabled** | Audits scoped strictly to tenant projects. |
| `public.audit_screens` | **Enabled** | Screens inherit audit access control. |
| `public.screen_assets` | **Enabled** | Assets bound to tenant screens. |
| `public.analysis_jobs` | **Enabled** | Jobs restricted to tenant ownership. |
| `public.findings` | **Enabled** | Findings viewable only by tenant members. |
| `public.design_system_analyses` | **Enabled** | Design system reports scoped to project tenant. |
| `public.export_jobs` | **Enabled** | Exports restricted to creating user/tenant. |
| `public.knowledge_documents` | **Enabled** | Scoped to tenant or marked as global platform knowledge. |
| `public.knowledge_chunks` | **Enabled** | Chunks inherit parent document visibility. |

---

## 4. Supabase Storage Configuration

### 4.1 Buckets Required
1. **`forteux-private-assets` (Private)**
   - Purpose: Interface screenshots, uploaded PDF/DOCX knowledge files, exported reports.
   - Public access: **Disabled (Private Bucket)**.
   - Access protocol: S3-compatible signed URLs with 300s TTL.

### 4.2 Storage RLS Policies
In the Supabase SQL editor:
```sql
-- Allow authenticated users to view objects in their tenant folder
CREATE POLICY "Tenant asset read"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'forteux-private-assets' AND (storage.foldername(name))[1] = auth.uid()::text);

-- Allow authenticated users to upload objects to their tenant folder
CREATE POLICY "Tenant asset insert"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'forteux-private-assets' AND (storage.foldername(name))[1] = auth.uid()::text);
```

---

## 5. Connection Pooling & Database Performance

1. **Transaction Pooler (Supavisor / PgBouncer):**
   - Use port `6543` for FastAPI SQLAlchemy engine:
     `postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require`
   - Set SQLAlchemy pool settings in `backend/app/db/session.py`:
     - `pool_size=10`
     - `max_overflow=20`
     - `pool_pre_ping=True`
     - `pool_recycle=300`
2. **Direct Connection:**
   - Use port `5432` only for running Alembic migrations (`alembic upgrade head`) because schema migrations with transaction DDL require a session-level connection.
3. **Database Extensions:**
   - `pgvector`: Required for RAG embedding similarity searches. Ensure enabled via `CREATE EXTENSION IF NOT EXISTS vector;`.
