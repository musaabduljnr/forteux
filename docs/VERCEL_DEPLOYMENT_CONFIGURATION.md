# Vercel Deployment Configuration Guide

**Application:** Forteux UI/UX Auditing Platform (Frontend)  
**Framework:** Next.js 15 (App Router)  
**Build Command:** `npm run build`  
**Root Directory:** `.` (Repository root)

---

## 1. Project Creation & Framework Detection

When importing the Forteux repository into Vercel:
1. **Framework Preset:** Select **Next.js** (automatically detected).
2. **Root Directory:** Keep as `./` (the repository root).
3. **Build & Development Settings:**
   - **Build Command:** `npm run build` (or leave default `next build`)
   - **Output Directory:** `.next` (Next.js default)
   - **Install Command:** `npm install`
   - **Node.js Version:** `20.x` or `22.x` (Configured in Vercel Project Settings -> General).

---

## 2. Serverless Function Region Alignment

To minimize latency between the Next.js server runtime (including middleware and the `/api/backend` proxy) and the Supabase PostgreSQL database:
- **Supabase in US East (`us-east-1`):** Set Vercel Function Region to **Washington, D.C., USA (`iad1`)**.
- **Supabase in US West (`us-west-1`):** Set Vercel Function Region to **San Francisco, USA (`sfo1`)**.
- **Supabase in Europe (`eu-central-1` / `eu-west-1`):** Set Vercel Function Region to **Frankfurt, Germany (`fra1`)** or **Dublin, Ireland (`dub1`)**.

---

## 3. Environment Variables Configuration (Vercel Dashboard)

Under **Project Settings** -> **Environment Variables**:

| Variable Name | Environment Scope | Value / Guidance |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Production & Preview | `https://<YOUR_PROJECT_REF>.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Production & Preview | `<YOUR_SUPABASE_ANON_KEY>` |
| `SUPABASE_SERVICE_ROLE_KEY` | Production & Preview | `<YOUR_SUPABASE_SERVICE_ROLE_KEY>` (Server-only) |
| `BACKEND_API_URL` | Production | `https://api.forteux.ai/api/v1` |
| `BACKEND_API_URL` | Preview | `https://api-staging.forteux.ai/api/v1` (or your staging endpoint) |
| `NEXTAUTH_URL` | Production | `https://app.forteux.ai` |
| `NEXTAUTH_URL` | Preview | `https://${VERCEL_URL}` |
| `NEXTAUTH_SECRET` | Production & Preview | `<32-byte-random-string>` |
| `DEV_AUTH_ENABLED` | Production & Preview | `false` |
| `NEXT_PUBLIC_DEV_AUTH_ENABLED` | Production & Preview | `false` |

---

## 4. Custom Domains & Routing

In Vercel **Settings** -> **Domains**:
1. Add `forteux.ai` (Root domain with automatic redirect to `www.` or `app.`).
2. Add `app.forteux.ai` (Primary authenticated application domain).
3. Vercel automatically issues and renews Let's Encrypt SSL/TLS certificates.

---

## 5. Preview & Branch Strategy

- **Production Branch:** `main` (automatically deploys to `app.forteux.ai`).
- **Preview Deployments:** Every Pull Request or push to non-main branches generates an isolated preview URL (e.g., `forteux-git-feature-preview.vercel.app`).
- **Wildcard Callback Handling:** Add `https://*.vercel.app/auth/callback` to Supabase allowed redirect URIs so preview branches can authenticate seamlessly.
