# Forteux: Final System Architecture Document

**Version**: 1.0.0 (Production Release)  
**Date**: November 17, 2026  
**Target Environment**: Next.js 15 Frontend, FastAPI Backend, Supabase Infrastructure (PostgreSQL, Auth, Storage, RLS, pgvector)

---

## 1. System Overview & Component Responsibilities

Forteux is an enterprise AI-powered UI/UX design auditing, consistency evaluation, and redesign platform. The system architecture divides responsibilities across three primary tiers:

```mermaid
flowchart TD
    subgraph Client["Presentation Tier (Next.js 15 App Router)"]
        UI["Web App (React Server & Client Components)"]
        Canvas["Interactive Screenshot & Bounding Box Canvas"]
        State["Client State & Auth Session Management"]
    end

    subgraph Backend["Processing & Orchestration Tier (FastAPI)"]
        API["FastAPI REST Endpoints (/api/v1)"]
        AuthMiddleware["OIDC JWT Verification Middleware"]
        TenantGuard["Multi-Tenant Isolation Layer"]
        AIEngine["AI Orchestrator (Vision, LLM, Prompts)"]
        RAGEngine["Knowledge Pipeline (Extract, Chunk, Vector)"]
        ExportEngine["Multi-Format Exporter (JSON, MD, CSV, ZIP)"]
    end

    subgraph SupabaseInfra["Data & Cloud Infrastructure (Supabase)"]
        Postgres["Supabase PostgreSQL (Pooled / Direct)"]
        RLS["PostgreSQL Row Level Security (RLS) Engine"]
        PgVector["pgvector Extension (Embedding Indexing)"]
        GoTrue["Supabase Auth (OIDC / JWKS Provider)"]
        S3Storage["Supabase Storage (S3-Compatible Object Store)"]
    end

    subgraph ExternalAI["External AI Model Providers"]
        GeminiVision["Google Gemini 2.5 Flash (Vision & Reasoning)"]
        GeminiEmbed["text-embedding-004"]
    end

    UI --> API
    API --> AuthMiddleware
    AuthMiddleware -.->|Validate JWKS| GoTrue
    API --> TenantGuard
    TenantGuard --> Postgres
    Postgres --> RLS
    Postgres --> PgVector
    API --> S3Storage
    AIEngine --> GeminiVision
    RAGEngine --> GeminiEmbed
```

---

## 2. Key Data Flow Sequences

### 2.1 Single & Multi-Screen AI Vision Audit Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Designer / Auditor
    participant FE as Next.js 15 Frontend
    participant API as FastAPI Backend
    participant S3 as Supabase Storage
    participant AI as Gemini 2.5 Vision Engine
    participant DB as Supabase PostgreSQL

    User->>FE: Upload screenshot(s) & submit audit
    FE->>API: POST /api/v1/screenshots/presign-upload
    API-->>FE: Presigned S3 PUT URL (TTL 300s)
    FE->>S3: Upload raw image binary via PUT
    FE->>API: POST /api/v1/audits (create audit & run vision)
    API->>S3: Verify uploaded object & fetch bytes
    API->>AI: Send image bytes + structured Pydantic schema
    AI-->>API: Findings JSON with normalized bounding boxes [x, y, w, h]
    API->>DB: Persist audit, screens, and findings in transaction
    API-->>FE: Return complete audit payload
    FE->>User: Render interactive canvas overlay with bounding boxes
```

### 2.2 Knowledge Library RAG & Contextual Finding Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Designer
    participant FE as Next.js 15 Frontend
    participant API as FastAPI Backend
    participant RAG as RAG Pipeline
    participant DB as Supabase PostgreSQL

    User->>FE: Upload design standard (PDF/DOCX/MD)
    FE->>API: Ingest document
    API->>RAG: Extract text, detect headings & chunk pages
    RAG->>API: Embed chunks with text-embedding-004
    API->>DB: Store document_versions & knowledge_chunks
    Note over API,DB: During Subsequent UI Audits
    API->>DB: Retrieve nearest-neighbor chunks via cosine similarity
    API->>DB: Record finding_evidence citations linking findings to chunks
    API-->>FE: Findings displayed with clickable source guideline citations
```

---

## 3. Relational Entity-Relationship Diagram

```mermaid
erDiagram
    TENANTS ||--o{ USERS : contains
    TENANTS ||--o{ MEMBERSHIPS : manages
    USERS ||--o{ MEMBERSHIPS : holds
    TENANTS ||--o{ PROJECTS : owns
    PROJECTS ||--o{ PROJECT_ACTIVITY_EVENTS : records
    PROJECTS ||--o{ AUDITS : groups
    AUDITS ||--o{ AUDIT_SCREENS : contains
    AUDITS ||--o{ SCREEN_ASSETS : attaches
    AUDITS ||--o{ ANALYSIS_JOBS : executes
    AUDITS ||--o{ FINDINGS : discovers
    AUDITS ||--o{ AUDIT_PROMPTS : synthesizes
    AUDITS ||--o{ DESIGN_SYSTEM_ANALYSES : extracts
    PROJECTS ||--o{ EXPORT_JOBS : generates
    TENANTS ||--o{ KNOWLEDGE_DOCUMENTS : catalogs
    KNOWLEDGE_DOCUMENTS ||--o{ DOCUMENT_VERSIONS : tracks
    DOCUMENT_VERSIONS ||--o{ KNOWLEDGE_CHUNKS : splits
    FINDINGS ||--o{ FINDING_EVIDENCE : cites
    KNOWLEDGE_CHUNKS ||--o{ FINDING_EVIDENCE : sourced_by

    TENANTS {
        uuid id PK
        string name
        datetime created_at
    }
    PROJECTS {
        uuid id PK
        uuid tenant_id FK
        string name
        string product_category
        string platform_type
        datetime created_at
    }
    AUDITS {
        uuid id PK
        uuid tenant_id FK
        uuid project_id FK
        int version_number
        uuid parent_job_id FK
        string status
        datetime created_at
    }
    FINDINGS {
        uuid id PK
        uuid audit_id FK
        string category
        string severity
        float confidence
        json bounding_boxes
        string evidence
        string recommended_fix
    }
    KNOWLEDGE_DOCUMENTS {
        uuid id PK
        uuid tenant_id FK
        uuid project_id FK
        string scope
        string display_name
        string status
    }
    KNOWLEDGE_CHUNKS {
        uuid id PK
        uuid tenant_id FK
        uuid document_id FK
        text text
        text embedding_json
        int chunk_index
    }
```

---

## 4. Security Architecture & Threat Model

1. **Authentication Boundary**:
   - Asymmetric RSA256 signature verification via Supabase GoTrue JWKS endpoint.
   - Development token bypass strictly forbidden in production (`APP_ENV=production` guard).
2. **Tenancy & Data Isolation**:
   - All relational tables enforce tenant isolation at both the application layer (`tenant_id == principal.tenant_id`) and the database engine level via PostgreSQL Row Level Security (RLS) policies.
3. **Storage Security**:
   - Private Supabase Storage buckets.
   - Presigned time-limited URLs for asset upload and download.
   - Magic byte validation prevents executable uploads.
4. **Transport Encryption**:
   - Production PostgreSQL connections require TLS (`sslmode=require`).
   - All API endpoints communicate over HTTPS.

---

## 5. Deployment Topology

- **Frontend Tier**: Next.js 15 hosted on Google Cloud Run or Vercel edge runtime.
- **Backend Tier**: FastAPI container instances orchestrated with autoscaling ($1 \to 20$ pods).
- **Data Tier**: Managed Supabase PostgreSQL, Supabase Auth, and Supabase Storage in the designated cloud region.
