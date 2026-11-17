# Phase 02 Route Inventory

| Route | Purpose | Key interactions |
|---|---|---|
| `/` | Dashboard overview | Open audits/projects, create audit/project, view knowledge |
| `/audits/new` | Single/multi-screen audit setup | Select mode/focus/project, preview/replace/remove screenshots, name/reorder screens, enter context, create local demo record |
| `/audits/[auditId]` | Audit workspace | Screen navigation, zoom/fit, normalized annotations, selection/highlighting, multi-screen flow order, generate/edit/regenerate/copy prompt |
| `/audits/demo` | Labelled single-screen illustrative workspace | View explicit demonstration-only issue fixtures and normalized annotations |
| `/audits/demo-flow` | Labelled multi-screen illustrative flow | Browse ordered sample screens and cross-screen demonstration fixtures |
| `/projects` | Project list and management | Search, create, open project |
| `/projects/[projectId]` | Project details | Rename, review audits/knowledge, create audit, confirm deletion |
| `/history` | Audit history | Search, filter by mode/status, sort by date, open audit |
| `/knowledge` | Knowledge management | Choose scope/project, select local file metadata, search/filter, view details, replace/remove metadata |
| `/design-system` | Design-pattern placeholder | Select project and inspect empty future extraction categories |
| `/settings` | Profile/preferences | Edit local profile placeholder, theme, audit mode, knowledge preferences, project selection |

Unknown audit/project IDs render explicit empty/not-found states. All records/actions are browser-local demonstration data; routes are not protected by authentication because no identity service exists yet.
