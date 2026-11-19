# Vercel Preview Deployment Test Plan & Verification Runbook

**Target:** Vercel Preview Environments (`*.vercel.app`)  
**Objective:** Validate all Forteux end-to-end features in an isolated staging environment before promoting to production.

---

## 1. Environment Segregation Principles

1. **Staging Database:** Preview deployments must connect to a separate staging Supabase project (or staging database schema), never production user data.
2. **Wildcard OAuth Callback:** Ensure `https://*.vercel.app/auth/callback` is added to the staging Supabase project's **Allowed Redirect URLs**.
3. **Staging Storage:** Uses a dedicated staging storage bucket (e.g. `forteux-staging-assets`) so test uploads never contaminate production storage.

---

## 2. End-to-End Verification Runbook

Execute this verification checklist on any new preview deployment:

| Step # | Flow / Feature | Test Procedure | Expected Outcome | Pass/Fail |
|---|---|---|---|---|
| **1** | **Landing Page** | Open `https://<preview-id>.vercel.app/` | Hero renders with animations, navigation items scroll smoothly, no 404 or styling breaks. | [ ] |
| **2** | **Registration** | Navigate to `/register`. Fill name, new email, and 12-char password. | Password strength indicator updates to "Strong". Submitting initiates signup. | [ ] |
| **3** | **Google OAuth** | Click "Continue with Google" on `/login`. | Google consent screen appears. Post-auth redirects to `/auth/callback` then `/onboarding`. | [ ] |
| **4** | **Onboarding Wizard** | Step through steps 1–4 (name, role, intended use, finish). | Progress bar advances. Profile is created in `profiles` table. Final step directs to `/dashboard`. | [ ] |
| **5** | **Dashboard** | View `/dashboard` as authenticated user. | Dynamic greeting displays user's name ("Welcome back, ..."). Metric cards show 0s or initial counts. | [ ] |
| **6** | **Project Creation** | Navigate to `/projects`, create "E-Commerce Checkout Audit". | Project appears in list and recent projects on dashboard. | [ ] |
| **7** | **Screenshot Upload** | Go to `/audits/new`, upload a PNG/JPEG screenshot (<10MB). | Preview thumbnail appears with name, dimension, and size. | [ ] |
| **8** | **Single-Screen Audit** | Submit single-screen audit review. | Audit workspace loads; bounding boxes and findings render with severity and confidence scores. | [ ] |
| **9** | **Stitch Prompt** | In audit review, select 2 findings and generate Stitch prompt. | Formatted markdown prompt displays with context, ready for one-click copy. | [ ] |
| **10** | **Multi-Screen Audit** | Create multi-screen audit with 3 sequential screenshots. | Sequence reordering works. Analysis evaluates journey consistency and screen transitions. | [ ] |
| **11** | **Knowledge Upload** | In `/knowledge`, upload a PDF or DOCX brand guide (<20MB). | Document status transitions to `ready`. Chunks and page references indexed. | [ ] |
| **12** | **Design System** | Open `/design-system`, extract tokens from project audit. | Color swatches, typography scale, component patterns, and consistency score display. | [ ] |
| **13** | **Export Center** | In `/exports`, create PDF, CSV, and JSON exports. | Export status transitions to `completed`. Download link opens signed asset. | [ ] |
| **14** | **Settings & Sign Out** | In `/settings`, update display name and click "Sign out". | Profile updates. Sign out redirects to `/login`. Protected routes block access. | [ ] |
