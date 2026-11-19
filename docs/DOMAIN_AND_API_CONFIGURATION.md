# Domain, DNS, CORS & API Configuration Guide

**Platform:** Forteux  
**Frontend Host:** Vercel  
**Backend Host:** Container Service (Cloud Run / Railway / Render / AWS)  
**Database & Auth Host:** Supabase

---

## 1. Domain Architecture Overview

To maintain clear separation between public marketing/web application and backend services, the recommended domain structure is:

| Domain / Subdomain | Target Service | Purpose |
|---|---|---|
| `forteux.ai` | Vercel (Root Domain) | Public landing page (with auto-redirect to `app.` or canonical root). |
| `app.forteux.ai` | Vercel (Application) | Authenticated dashboard, project workspaces, and Next.js frontend. |
| `api.forteux.ai` | FastAPI Container | Private backend API endpoints (`/api/v1/*`, `/health/*`). |
| `<ref>.supabase.co` | Supabase | Managed PostgreSQL, Auth, and Storage. |

---

## 2. DNS Record Configuration

Configure the following DNS records in your domain registrar (e.g. Cloudflare, Google Domains, Route 53, Namecheap):

| Type | Name / Host | Target / Value | TTL | Note |
|---|---|---|---|---|
| **A** | `@` (or `forteux.ai`) | `76.76.21.21` | Auto / 300 | Vercel Anycast IP |
| **CNAME** | `www` | `cname.vercel-dns.com.` | Auto / 300 | Vercel canonical redirect |
| **CNAME** | `app` | `cname.vercel-dns.com.` | Auto / 300 | Vercel frontend application |
| **CNAME** | `api` | Provided by backend host (e.g. `cname.railway.app` or Google Cloud Run domain mapping) | Auto / 300 | FastAPI backend container |

---

## 3. CORS Configuration (FastAPI)

FastAPI enforces origin validation in [backend/app/main.py](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/app/main.py):

```python
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
```

### Production `ALLOWED_ORIGINS` Setting
Set in `backend/.env`:
```bash
ALLOWED_ORIGINS=https://app.forteux.ai,https://forteux.ai
```
**Security Requirement:** Never use `*` (wildcard) in `ALLOWED_ORIGINS` when `allow_credentials=True` is enabled, as doing so introduces cross-origin vulnerability and is rejected by modern browsers.

---

## 4. Reverse Proxy & Next.js API Route Routing

The Next.js route [app/api/backend/[...path]/route.ts](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/app/api/backend/[...path]/route.ts) functions as an authenticated server-to-server reverse proxy:

```
[Browser] ─── HTTPS /api/backend/projects ───► [Next.js Route Proxy on Vercel]
                                                         │
                                               Extracts Supabase JWT
                                               Attaches Authorization Bearer
                                               Validates Request Size (<128KB)
                                                         │
                                                         ▼
                                            [FastAPI Backend: api.forteux.ai]
```

### Benefits:
1. **Zero Client CORS Overhead:** Client browsers communicate only with their own origin (`app.forteux.ai`).
2. **Secure Token Passing:** Tokens are extracted from HTTP-only cookies and forwarded server-to-server.
3. **Payload Guard:** Enforces maximum body limit (128KB) to prevent denial-of-service on API endpoints.
