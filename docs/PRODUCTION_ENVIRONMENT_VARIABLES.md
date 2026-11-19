# Production Environment Variable Inventory & Configuration

This document specifies every environment variable used across the Forteux platform, its sensitivity classification, and its target environment.

---

## 1. Frontend Environment Variables (Vercel)

| Variable Name | Sensitivity | Required | Environments | Purpose / Example |
|---|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | **Public** | **Yes** | Local, Preview, Production | Supabase project API URL (e.g. `https://<ref>.supabase.co`). |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Public** | **Yes** | Local, Preview, Production | Supabase anonymous API key for client-side queries and auth. |
| `SUPABASE_SERVICE_ROLE_KEY` | **Secret** (Server-only) | Optional | Local, Preview, Production | Privileged key for server-only operations. Never expose with `NEXT_PUBLIC_`. |
| `BACKEND_API_URL` | **Secret** (Server-only) | **Yes** | Local, Preview, Production | URL of the FastAPI backend for the Next.js API proxy (`/api/backend/*`). Default: `http://127.0.0.1:8000/api/v1` (local) or `https://api.forteux.ai/api/v1` (prod). |
| `DEV_AUTH_ENABLED` | **Secret** | No | Local only | Set to `false` in Preview and Production. |
| `NEXT_PUBLIC_DEV_AUTH_ENABLED` | **Public** | No | Local only | Set to `false` in Preview and Production. |
| `NEXTAUTH_SECRET` | **Secret** | Optional | Local, Preview, Production | Random 32-byte secret for legacy NextAuth session encryption fallback. |
| `NEXTAUTH_URL` | **Public/Config** | Optional | Local, Preview, Production | Canonical URL of the Next.js frontend (e.g. `https://app.forteux.ai`). |

---

## 2. Backend Environment Variables (FastAPI Container)

| Variable Name | Sensitivity | Required | Environments | Purpose / Example |
|---|---|---|---|---|
| `APP_ENV` | Config | **Yes** | Local, Staging, Production | Application environment: `development`, `test`, or `production`. |
| `LOG_LEVEL` | Config | No | All | Logging verbosity: `INFO`, `DEBUG`, `WARNING`, `ERROR`. |
| `API_PREFIX` | Config | No | All | API path prefix: `/api/v1`. |
| `DATABASE_URL` | **Secret** | **Yes** | All | PostgreSQL connection string with SSL: `postgresql+psycopg://postgres.<ref>:<pass>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require` |
| `OIDC_ISSUER` | Config | **Yes** | All | Supabase Auth issuer: `https://<ref>.supabase.co/auth/v1`. |
| `OIDC_CLIENT_ID` | Config | **Yes** | All | Expected token audience: `authenticated`. |
| `OIDC_JWKS_URL` | Config | **Yes** | All | Supabase Auth JWKS: `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`. |
| `SUPABASE_URL` | Config | Optional | All | Supabase project URL. |
| `SUPABASE_JWT_SECRET` | **Secret** | Optional | All | Supabase JWT Secret for HS256 verification (found in Supabase API settings). |
| `DEV_AUTH_ENABLED` | **Secret** | **Yes** | All | Set to `false` in staging/production. (App throws error if true in production). |
| `DEV_AUTH_SECRET` | **Secret** | No | Local only | Secret for local mock tokens. Empty in production. |
| `AWS_REGION` | Config | **Yes** | All | Supabase S3 region: `us-east-1` (or your project's region). |
| `AWS_ACCESS_KEY_ID` | **Secret** | **Yes** | All | Supabase Storage S3 access key ID. |
| `AWS_SECRET_ACCESS_KEY` | **Secret** | **Yes** | All | Supabase Storage S3 secret access key. |
| `S3_BUCKET` | Config | **Yes** | All | Target private storage bucket name: `forteux-private-assets`. |
| `S3_ENDPOINT_URL` | Config | **Yes** | All | Supabase S3 API URL: `https://<ref>.supabase.co/storage/v1/s3`. |
| `S3_UPLOAD_TTL_SECONDS` | Config | No | All | Presigned upload URL lifetime (default: 300s). |
| `S3_DOWNLOAD_TTL_SECONDS` | Config | No | All | Presigned download URL lifetime (default: 300s). |
| `MAX_UPLOAD_BYTES` | Config | No | All | Screenshot upload limit (default: 10485760 bytes = 10MB). |
| `KNOWLEDGE_MAX_DOC_BYTES` | Config | No | All | Knowledge document limit (default: 20971520 bytes = 20MB). |
| `ALLOWED_ORIGINS` | Config | **Yes** | All | Comma-separated CORS allowed origins: `https://app.forteux.ai,https://forteux.ai`. |
| `GEMINI_API_KEY` | **Secret** | Optional | All | Google Gemini API key for live vision & prompt generation models. |

---

## 3. Environment Segregation Matrix

```
                      ┌──────────────────────────────────────────────┐
                      │             Vercel Frontend                  │
                      ├──────────────────────────────────────────────┤
                      │ Preview:                                     │
                      │  - NEXT_PUBLIC_SUPABASE_URL (Staging/Dev)    │
                      │  - NEXT_PUBLIC_SUPABASE_ANON_KEY (Staging)   │
                      │  - BACKEND_API_URL (Staging API)             │
                      │                                              │
                      │ Production:                                  │
                      │  - NEXT_PUBLIC_SUPABASE_URL (Prod)           │
                      │  - NEXT_PUBLIC_SUPABASE_ANON_KEY (Prod)      │
                      │  - BACKEND_API_URL (https://api.forteux.ai)  │
                      └──────────────────────┬───────────────────────┘
                                             │ HTTPS Proxy
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │             FastAPI Backend                  │
                      ├──────────────────────────────────────────────┤
                      │ Staging / Production:                        │
                      │  - APP_ENV=production                       │
                      │  - DATABASE_URL (Supabase Pooled :6543)      │
                      │  - DEV_AUTH_ENABLED=false                    │
                      │  - S3_ENDPOINT_URL (Supabase S3)             │
                      │  - GEMINI_API_KEY (Google AI Studio)         │
                      └──────────────────────────────────────────────┘
```
