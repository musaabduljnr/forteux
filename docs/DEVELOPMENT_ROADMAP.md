# Development Roadmap

**Status:** Phase 02 frontend and backend foundation complete — review required before Phase 03  
**Last reviewed:** 2026-11-16

The Phase 02 brief defines a frontend-only phase and explicitly names Phase 03 as Screenshot Upload and Image Processing. The backend foundation was subsequently implemented as a prerequisite to image processing. Its cloud resources are not provisioned or verified. Do not begin screenshot processing until the foundation handoff is reviewed and approved.

## Phase 01 — Product requirements and architecture

- Define product modes, evidence policy, scope, data model, API surface, security baseline, acceptance criteria, and technology alternatives.
- Obtain decisions on hosting, region, tenants, limits, retention, identity, and initial providers.
- **Exit:** stakeholder reviews architecture; remaining decisions have owners and approval dates.

## Phase 02 — Frontend dashboard and application interface

- Build a responsive Next.js/React/TypeScript application shell, design tokens, navigation, dashboard, projects, audit history, knowledge library, design-system, and settings routes.
- Add local screenshot previews, screen ordering, structured annotation rendering, finding selection, and editable/copyable Stitch prompt UI.
- Keep demo data isolated and explicitly labelled; do not implement backend services, AI analysis, document extraction, or vector retrieval.
- **Exit:** requested routes and frontend interactions work; responsive, accessibility, build, type-check, and browser validation are recorded; implementation report is complete. **Complete; awaiting review/approval before Phase 03.**

## Foundation prerequisite — Backend, database, authentication, and storage

- Establish FastAPI, PostgreSQL models/migrations, Cognito-compatible OIDC, tenant/project ownership, private S3 integration, health checks, and a Next.js authenticated API client/proxy.
- Preserve the Phase 02 frontend; do not add image processing or AI.
- **Exit:** foundation code and local tests are complete. **Implemented; live Cognito, PostgreSQL, S3, IAM, and deployment remain unverified.** See `FOUNDATION_IMPLEMENTATION_REPORT.md`.

## Phase 03 — Screenshot Upload and Image Processing (next; approval required)

- Integrate the Phase 02 uploader with the authenticated API and private upload path implemented in the foundation.
- Validate file signature, media type, size, dimensions, and image decoding; quarantine until checked; preserve originals and geometry and create safe derivatives.
- Implement upload state, progress, failure and retry UX; securely bind assets to authorized projects.
- Do not add screenshot AI analysis unless the scope is separately approved.
- **Exit:** upload, content validation, storage privacy, image orientation/dimension preservation, removal/deletion, and browser states pass security and functional acceptance tests. This phase has not started.

## Phase 04 — Backend/API foundations and single-screen analysis

- Add durable job lifecycle, observability, and remaining API contracts; the initial authentication/database/storage foundation already exists.
- Add typed provider adapters, a single-screen analysis pipeline, validated structured findings, normalized bounding boxes, and one Stitch prompt.
- **Exit:** Phase 01 API/security/AI acceptance criteria for a single-screen vertical slice pass.

## Phase 05 — Evaluation-first analysis quality

- Create a permissioned expert-labeled single-screen dataset with clear annotation instructions.
- Establish detection, localization, false-positive, severity, recommendation, and confidence calibration baselines.
- Add offline evaluation and canary tooling; tune thresholds on train/validation data only.
- **Exit:** agreed held-out thresholds are met or product limitations and a narrower scope are approved.

## Phase 06 — Knowledge library

- Implement file ingestion, extraction/OCR, deduplication, versions, categories, chunking, embeddings, hybrid retrieval, citations, deletion, and prompt-injection safeguards.
- Verify global/project scoping and citation provenance.
- **Exit:** retrieval, citation, deletion, and security acceptance criteria pass; deletion is reconciled across object and vector stores.

## Phase 07 — Multi-screen UX reasoning

- Implement independent per-screen analysis, ordered screen comparison, design-pattern consistency, journey reasoning, cross-screen findings, and combined prompt generation.
- Build expert-labeled pairwise, consistency, and journey test sets.
- **Exit:** cross-screen reasoning measurably outperforms independent-screen aggregation, without materially reducing per-screen precision.

## Phase 08 — Production hardening and beta

- Complete quotas, cost controls, back-pressure, retries/dead-letter handling, retention/deletion UX, global-library administration, and provider migration controls.
- Run load, failure-injection, accessibility, recovery, security, and privacy reviews.
- Launch a limited beta; monitor quality, latency, cost, user feedback, and incidents.
- **Exit:** service targets and support runbooks are approved; no critical security/privacy issues remain.

## Dependencies and critical path

1. Product/legal decisions on user data, residency, retention, and provider terms.
2. Tenant model, identity provider, and storage provider are selected in the foundation; choose the launch region and approve upload/retention limits before production data is stored.
3. Provision and live-test secure project authorization, PostgreSQL, Cognito, bucket/IAM policy, and storage deletion before exposing production uploads.
4. Human-labeled evaluation data is required before meaningful accuracy thresholds or model selection.
5. Cross-screen expert annotations are required before claiming flow-analysis quality.

## Risks to schedule and cost

- Ground-truth labeling is labor-intensive and needed for reliable localization/false-positive measures.
- Vision calls and repeated multi-screen comparisons can dominate per-audit cost; enforce limits and measure per-stage usage.
- OCR and embeddings scale with document pages, not only file count; scanned PDFs can be significantly more expensive.
- Data residency/compliance requirements can constrain providers and cloud regions.
- Model retirement, API changes, and inconsistent structured-output support require adapter and regression work.
- Global-knowledge curation requires an accountable owner and review cadence.

## Decisions requiring approval before production uploads and later AI phases

| Decision | Recommended default | Needed from |
|---|---|---|
| Launch cloud region | AWS selected; region and data-residency review remain open | Product/security |
| Identity integration | Cognito and OIDC flow implemented; provision pool and review user lifecycle/MFA | Product/security |
| Production image/document limits | Current 10 MiB per screenshot and 12-screen UI limit are provisional | Product/engineering |
| Retention and deletion SLA | Explicit policy; immediate access revocation, asynchronous purge | Product/legal |
| AI provider and model | Benchmark at least one multimodal primary and one alternative | AI/product/security |
| Global knowledge | Platform-curated, administrator-only write access | Product |
| Supported languages | English first unless launch market requires more | Product |
| Durable queue | Select for background AI/knowledge work in Phase 04+ | Engineering |
