# Authentication & System Security Report

## 1. Security Architecture & Threat Model

This report details the security safeguards, token validation rules, isolation guarantees, and cryptographic parameters applied to the Forteux authentication system.

---

## 2. Token Handling & Verification

### 2.1 Storage & Transmission
- **Web Storage**: Supabase Auth session tokens are stored in secure cookies managed by `@supabase/ssr`.
- **Backend Communication**: Client calls route through the internal Next.js API route (`/api/backend/[...path]`), which forwards the Supabase session access token via standard `Authorization: Bearer <token>` headers.
- **Service Keys**: The `SUPABASE_SERVICE_ROLE_KEY` is strictly confined to server-side environments and never exposed to client-side bundles (prefixed without `NEXT_PUBLIC_`).

### 2.2 FastAPI Token Validation
- FastAPI verifies incoming Bearer tokens using:
  1. **Asymmetric Verification**: Checks the Supabase JWKS endpoint (`https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`) for valid RS256/ES256 signatures.
  2. **Symmetric Verification**: Verifies tokens using `SUPABASE_JWT_SECRET` when HS256 is configured.
  3. **Claim Validation**: Strictly validates expiration (`exp`), issued-at (`iat`), subject (`sub`), and audience (`"aud": "authenticated"`).

---

## 3. Row Level Security (RLS) & Multi-Tenant Isolation

### 3.1 PostgreSQL Engine Enforcement
All tenant tables enforce Row Level Security via Supabase PostgreSQL policies (`backend/migrations/supabase_rls.sql`):
- `tenants`
- `users`
- `memberships`
- `projects`
- `audits`
- `audit_screens`
- `screen_assets`
- `analysis_jobs`
- `findings`
- `audit_prompts`
- `design_system_analyses`
- `export_jobs`
- `knowledge_documents`
- `profiles`

### 3.2 User Profile Isolation
Under `backend/migrations/create_user_profiles.sql`:
- Authenticated users can only read (`SELECT`), insert (`INSERT`), and update (`UPDATE`) rows where `id = auth.uid()`.
- Cross-user profile modifications are completely blocked at the database engine level.

---

## 4. Open Redirect Prevention

The login flow and auth callback strictly validate the `next` query parameter:
- Only relative paths starting with a single forward slash (`/`) are accepted (e.g., `/dashboard`, `/projects/123`).
- Protocol-relative URLs (e.g., `//evil.com`) and absolute external URLs (e.g., `https://evil.com`) are rejected, defaulting safely to `/dashboard`.

---

## 5. Account Enumeration & Brute-Force Safeguards

- The password recovery endpoint (`/forgot-password`) responds with a uniform success message regardless of whether an email exists in the database, preventing user enumeration attacks.
- Passwords are validated client-side against complexity rules and verified server-side with Supabase Auth bcrypt/argon2 hashing.
