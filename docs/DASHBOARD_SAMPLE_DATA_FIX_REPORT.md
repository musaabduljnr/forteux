# Dashboard Sample Data Fix Report

## 1. Root Cause

The deployed dashboard displayed fabricated sample data (`2` audits, `4` screens analysed, `4` issues identified, `3` projects: `"Northstar Commerce"`, `"Fieldnotes Mobile"`, `"Atlas Workspace"`, and sample audits `"Checkout — illustrative workspace"` and `"Field planning flow — sample"`) because:

1. **Client-side demo state initialization:** `components/app-state.tsx` initialized React context state (`projects`, `audits`, `documents`, `user`) directly from hardcoded arrays in `lib/demo-data.ts` (`demoProjects`, `demoAudits`, `demoKnowledge`, `demoUser`) and persisted them under `localStorage` key `"forteux-frontend-demo-v1"`.
2. **Dashboard reading from demo context:** `app/dashboard/page.tsx` consumed `audits`, `projects`, and `documents` from `useAppState()` instead of querying persisted backend records for the authenticated user.
3. **API proxy path mismatch:** Several frontend pages called `/api/backend/v1/...` while `BACKEND_API_URL` already includes `/api/v1`, which would produce `/api/v1/v1/...` upstream paths.

## 2. Origin of the Displayed Data

- **Origin:** **Frontend mocks** in `lib/demo-data.ts` loaded by `components/app-state.tsx` and cached in `localStorage`.
- **Production Supabase database check:** Verified via read-only query against project `edlkpfrlsrgslcdwjykv`:
  - `projects`: `0` rows
  - `audits`: `0` rows
  - `audit_screens`: `0` rows
  - `findings`: `0` rows
  - `knowledge_documents`: `0` rows
- No seeded or shared sample records exist in production Supabase.

## 3. Files and Components Changed

- [components/app-state.tsx](file:///home/musa-a-abu/Desktop/forteux/components/app-state.tsx)
  - Removed `lib/demo-data` imports and initialized `projects`, `audits`, `documents` as `[]` and `user` as an empty default object.
  - Changed `createAudit` default `isDemo` from `true` to `false` and `status` from `"demo"` to `"ready"`.
  - Bumped storage key to `"forteux-workspace-v2"` and removed legacy `"forteux-frontend-demo-v1"` on mount so previously cached sample records are cleared from user browsers.
- [app/dashboard/page.tsx](file:///home/musa-a-abu/Desktop/forteux/app/dashboard/page.tsx)
  - Replaced `useAppState()` data consumption with an authenticated fetch to `GET /api/backend/dashboard/summary`.
  - Renders real metrics (`total_audits`, `screens_analysed`, `issues_identified`, `total_projects`), real recent audits, and real recent projects, plus an explicit unavailable state if the backend request fails.
- [app/api/backend/[...path]/route.ts](file:///home/musa-a-abu/Desktop/forteux/app/api/backend/[...path]/route.ts)
  - Normalized redundant leading `v1/` segments when `BACKEND_API_URL` already ends with `/v1`.
- [lib/types.ts](file:///home/musa-a-abu/Desktop/forteux/lib/types.ts)
  - Added `DashboardAuditItem`, `DashboardProjectItem`, and `DashboardSummaryResponse` interfaces, and optional `screen_count`/`finding_count` on `AuditRead`.
- [backend/app/api/v1/schemas.py](file:///home/musa-a-abu/Desktop/forteux/backend/app/api/v1/schemas.py)
  - Added `DashboardAuditItem`, `DashboardProjectItem`, and `DashboardSummaryResponse` Pydantic models.
- [backend/app/api/v1/routes.py](file:///home/musa-a-abu/Desktop/forteux/backend/app/api/v1/routes.py)
  - Added `GET /api/v1/dashboard/summary` endpoint.
- [backend/tests/test_dashboard.py](file:///home/musa-a-abu/Desktop/forteux/backend/tests/test_dashboard.py)
  - Added automated tests covering Scenarios A–E and unauthenticated access.

## 4. Changes Made to User Isolation & Metrics Calculation

In `GET /api/v1/dashboard/summary` (`backend/app/api/v1/routes.py`):
- Enforces `get_current_principal` authentication (`401` if unauthenticated).
- Scopes all queries by `Membership.user_id == principal.id` and `Membership.tenant_id == principal.tenant_id` (and `tenant_id == principal.tenant_id` on `Project`, `Audit`, and `Finding`).
- Excludes soft-deleted records (`Project.deleted_at.is_(None)` and `Audit.deleted_at.is_(None)`).
- Uses `COUNT(DISTINCT ...)` to prevent join-induced duplicate counts.
- Excludes incomplete or failed audits/jobs from `screens_analysed` (`Audit.status == "completed"`) and `issues_identified` (`Audit.status == "completed"` and `AnalysisJob.status == "completed"`).

## 5. Empty-State Behaviour

When an authenticated user has no records:
- Overview cards display `0` for **Total audits**, **Screens analysed**, **Issues identified**, and **Projects**.
- **Recent audits** renders:
  - Title: `"Your workspace is ready."`
  - Description: `"Start your first UI/UX audit to see your findings, projects, and design insights here."`
  - Primary CTA: `"Start your first audit"` (`/audits/new`)
- **Projects** renders:
  - Title: `"No projects yet"`
  - Description: `"Create a project to organise your audits and design assets."`
  - Secondary CTA: `"Create a project"` (`/projects`)
- Welcome banner greets the user by their Supabase profile name (`profiles.full_name` -> user metadata -> email prefix -> `"Designer"`).

## 6. Tests Performed and Results

### Backend Tests (`backend/.venv/bin/python -m pytest tests/test_dashboard.py tests/test_ownership.py tests/test_auth.py tests/test_dev_auth.py -v`)
- **17 passed, 0 failed** (0.75s):
  - `test_dashboard_requires_authentication`: `PASSED`
  - `test_dashboard_scenario_a_fresh_user_sees_zeros`: `PASSED`
  - `test_dashboard_scenario_b_genuine_user_data`: `PASSED`
  - `test_dashboard_scenario_c_user_isolation`: `PASSED`
  - `test_dashboard_scenario_d_failed_and_incomplete_audits_excluded_from_completed_metrics`: `PASSED`
  - `test_dashboard_scenario_e_deleted_records_excluded`: `PASSED`
  - `test_ownership.py` (2 tests), `test_auth.py` (4 tests), `test_dev_auth.py` (5 tests): `PASSED`

### Frontend Validation & Production Build
- `npm run lint`: `0 errors` (3 pre-existing warnings in `app/history/page.tsx` and `app/projects/[projectId]/page.tsx`)
- `npm run typecheck`: `0 errors`
- `npm run build`: succeeded cleanly; `lib/demo-data.ts` sample projects/audits are not bundled into `/dashboard`.

## 7. Production Database Cleanup

**None required.** Production Supabase (`edlkpfrlsrgslcdwjykv`) contains `0` rows across `projects`, `audits`, `audit_screens`, `findings`, and `knowledge_documents`. No destructive SQL was executed or needed.
