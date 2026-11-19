# Forteux CI/CD & Branching Strategy Plan

**Continuous Integration System:** GitHub Actions  
**Pipeline Configuration:** [.github/workflows/ci.yml](file:///c:/Users/Musa%20A.%20Abubakar/Desktop/forteux/.github/workflows/ci.yml)

---

## 1. Branch Strategy

```
  feature/xxx ──► pull request ──► develop (Preview Environment)
                                       │
                                   release/xxx
                                       │
                                       ▼
                                 main (Production Environment)
```

1. **`main` (Production):**
   - Protected branch requiring passing CI checks and review approval.
   - Triggers production deployments to Vercel (`app.forteux.ai`) and production container registry.
2. **`develop` (Staging / Preview):**
   - Integration branch for completed features.
   - Triggers preview deployments to Vercel preview URLs.
3. **`feature/*` / `fix/*` (Working Branches):**
   - Developer worktrees. Pull requests into `develop` run full CI validation.

---

## 2. CI Automation Stages

The automated pipeline defined in `.github/workflows/ci.yml` enforces two concurrent validation jobs:

### Job 1: `frontend-validation`
- **Node Engine:** Node.js 20.x
- **Checks:**
  1. `npm ci` (deterministic lockfile installation)
  2. `npm run lint` (ESLint rule enforcement across `app`, `components`, `lib`)
  3. `npm run typecheck` (`tsc --noEmit` zero-error enforcement)
  4. `npm run build` (Next.js production compile and static route generation)

### Job 2: `backend-validation`
- **Python Engine:** Python 3.11
- **Checks:**
  1. `pip install -r requirements.txt -r requirements-dev.txt`
  2. Pytest execution (`pytest tests/ -v`) covering all 159 test cases:
     - Multi-tenant tenant isolation
     - Row Level Security logic
     - AI Vision and bounding box benchmarks
     - RAG chunking and vector retrieval
     - Export generation and history pagination
