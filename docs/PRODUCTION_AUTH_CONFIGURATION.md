# Production Authentication & Google OAuth Configuration Guide

**Provider:** Supabase Auth (GoTrue)  
**Client SDK:** `@supabase/ssr` (Next.js 15 App Router)  
**Backend Validator:** FastAPI PyJWT / PyJWKClient

---

## 1. Supabase Auth Dashboard Settings

In your Supabase project under **Authentication** -> **URL Configuration**:

### 1.1 Site URL
- **Production Site URL:** `https://app.forteux.ai` (or your chosen production domain)

### 1.2 Allowed Redirect URLs
Configure the following redirect URLs to support development, preview deployments, and production:
```
http://localhost:3000/auth/callback
https://app.forteux.ai/auth/callback
https://*.vercel.app/auth/callback
```

---

## 2. Google OAuth Production Setup

### 2.1 Google Cloud Console Configuration
1. Navigate to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials).
2. Edit your **OAuth 2.0 Client ID** (Web application).
3. **Authorized JavaScript origins:**
   - `http://localhost:3000` (Local dev)
   - `https://app.forteux.ai` (Production)
   - `https://your-team.vercel.app` (Preview)
4. **Authorized redirect URIs (Exact Supabase URI):**
   ```
   https://<YOUR_SUPABASE_PROJECT_REF>.supabase.co/auth/v1/callback
   ```
   *(Note: The browser redirects from Google directly to Supabase, which then completes the callback to your application's `/auth/callback`)*

### 2.2 Supabase Dashboard Provider Settings
1. Navigate to **Authentication** -> **Providers** -> **Google**.
2. Enable Google.
3. Paste:
   - **Client ID** (from Google Cloud Console)
   - **Client Secret** (from Google Cloud Console)
4. Save configuration.

---

## 3. Account Security & Verification

### 3.1 Token Validation in FastAPI
When Next.js proxies API requests to FastAPI, the Bearer token is strictly verified in [backend/app/core/auth.py](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/app/core/auth.py):
1. **Issuer (`iss`):** Must match `https://<project-ref>.supabase.co/auth/v1`.
2. **Audience (`aud`):** Must be `"authenticated"`.
3. **Signature:** Verified against Supabase public JWKS (`https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`) or symmetric `SUPABASE_JWT_SECRET`.
4. **Expiration (`exp`):** Verified automatically by PyJWT; expired tokens reject with HTTP 401.

### 3.2 Automated Profile Creation (Idempotent Trigger)
On user registration (either via email or Google OAuth), the database trigger `on_auth_user_created` defined in [backend/migrations/create_user_profiles.sql](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/migrations/create_user_profiles.sql) executes:
```sql
INSERT INTO public.profiles (id, full_name, email, avatar_url, onboarding_completed)
VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'full_name', ''), NEW.email, NEW.raw_user_meta_data->>'avatar_url', FALSE)
ON CONFLICT (id) DO UPDATE SET
    full_name = EXCLUDED.full_name,
    avatar_url = COALESCE(EXCLUDED.avatar_url, profiles.avatar_url),
    updated_at = NOW();
```
This guarantees user profiles are created idempotently without race conditions.

### 3.3 Disabling Development Auth in Production
The setting `DEV_AUTH_ENABLED` is safeguarded in [backend/app/core/config.py](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/backend/app/core/config.py):
```python
if self.app_env == "production" and self.dev_auth_enabled:
    raise RuntimeError("DEV_AUTH_ENABLED cannot be enabled in production environment")
```
If `DEV_AUTH_ENABLED=true` is set when `APP_ENV=production`, the FastAPI application refuses to start, preventing accidental backdoor exposure.
