# Google OAuth Setup Guide for Forteux

This guide outlines the step-by-step instructions for configuring Google OAuth integration with Supabase Auth for Forteux.

---

## 1. Google Cloud Console Configuration

1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Select your project or create a new project named **Forteux**.
3. Configure the **OAuth consent screen**:
   - **User Type**: External (or Internal if restricted to Google Workspace).
   - **App name**: Forteux
   - **User support email**: Your support or administrator email.
   - **App logo**: Optional.
   - **Application home page**: `https://your-domain.com` (or `http://localhost:3000` for development).
   - **Authorized domains**: Add `supabase.co` (and your production domain).
   - **Developer contact information**: Your technical contact email.
   - **Scopes**: Select `.../auth/userinfo.email`, `.../auth/userinfo.profile`, and `openid`.
4. Create **OAuth 2.0 Credentials**:
   - Go to **Credentials** -> **Create Credentials** -> **OAuth client ID**.
   - **Application type**: Web application.
   - **Name**: Forteux Web Client.
   - **Authorized JavaScript origins**:
     - `http://localhost:3000` (development)
     - `https://your-production-domain.com` (production)
   - **Authorized redirect URIs**:
     - `https://<YOUR_SUPABASE_PROJECT_REF>.supabase.co/auth/v1/callback`
5. Click **Create** and record:
   - **Client ID**
   - **Client Secret**

---

## 2. Supabase Dashboard Configuration

1. Open your [Supabase Dashboard](https://supabase.com/dashboard) and select your project.
2. Navigate to **Authentication** -> **Providers**.
3. Locate **Google** in the provider list and toggle **Enable Sign in with Google**.
4. Paste the **Client ID** and **Client Secret** obtained from Google Cloud Console.
5. In **Redirect URLs** (under **Authentication** -> **URL Configuration**):
   - Add `http://localhost:3000/auth/callback` (for local development)
   - Add `https://your-production-domain.com/auth/callback` (for production)
6. Click **Save**.

---

## 3. Environment Variables Configuration

In `.env.local` (and your production hosting environment):

```bash
NEXT_PUBLIC_SUPABASE_URL=https://<YOUR_SUPABASE_PROJECT_REF>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<YOUR_SUPABASE_ANON_KEY>
SUPABASE_SERVICE_ROLE_KEY=<YOUR_SUPABASE_SERVICE_ROLE_KEY>
```

In `backend/.env`:

```bash
SUPABASE_URL=https://<YOUR_SUPABASE_PROJECT_REF>.supabase.co
SUPABASE_JWT_SECRET=<YOUR_SUPABASE_JWT_SECRET>
```

---

## 4. Verification Flow

1. Start the Next.js development server:
   ```bash
   npm run dev
   ```
2. Navigate to `http://localhost:3000/login` or `http://localhost:3000/register`.
3. Click **Continue with Google** / **Sign up with Google**.
4. Complete Google authentication.
5. You will be redirected to `/auth/callback`, which exchanges the authorization code for a session and routes to `/onboarding` (first-time users) or `/dashboard` (returning users).
