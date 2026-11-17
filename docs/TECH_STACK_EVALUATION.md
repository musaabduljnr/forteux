# Technology Stack Evaluation

**Status:** Foundation stack decisions finalized; AI provider remains a later benchmark decision  
**Last reviewed:** 2026-11-16

## 1. Recommended default

| Area | Recommendation | Rationale |
|---|---|---|
| Frontend | Next.js + React + TypeScript | Mature ecosystem, accessible UI options, typed API client, suitable for upload and interactive annotations |
| Backend/API | Python + FastAPI + Pydantic | Strong document/vision/ML ecosystem, typed request contracts, async HTTP support |
| Workers | Python worker process with durable managed queue; Celery/RQ only if queue choice supports required durability | Isolate CPU/OCR/AI work; independently scale and retry |
| Authentication | Managed OIDC (AWS Cognito on AWS or equivalent) | Avoid custom password/session security; support standards-based provider change |
| Relational database | PostgreSQL | Transactions, mature JSON support, reliable relational data and broad managed offerings |
| Vector search | pgvector initially | Minimizes systems and enables scope-aware hybrid SQL retrieval; benchmark filtered vector performance |
| Object storage | S3 private buckets (or equivalent) | Durable encrypted object storage, lifecycle and short-lived scoped URLs |
| Queue/cache | Managed durable queue preferred; Redis for short-lived cache/rate limiting if useful | Durable work delivery should not depend on volatile cache semantics |
| OCR/extraction | Native PDF/DOCX parsers first; PaddleOCR/Tesseract or managed OCR for scanned docs | Cost/control vs throughput trade-off; benchmark language/layout quality |
| Image processing | Pillow/OpenCV with bounded processing; optional detector/grounding model behind interface | Common formats and controlled geometry transformations |
| Annotation rendering | SVG overlay and accessible DOM finding list | Scalable normalized boxes, keyboard navigation and responsive rendering |
| Observability | OpenTelemetry-compatible traces/metrics/logs | Provider- and cloud-neutral monitoring; redact payloads |
| Deployment | Containers; managed relational/object/queue services | Repeatable environments and independent API/worker scaling |

This is a starting point, not a commitment to AWS or a specific managed vendor. Avoid adding Kubernetes, a separate vector database, and microservices at launch without a measured need.

## 2. AI provider/model comparison

Static feature claims and prices change. The following comparison uses provider documentation checked on 2026-11-16 and should be rechecked during procurement and benchmark. Model availability, regions, quotas, data terms, and prices can differ by platform. Capability does not imply comparative accuracy for UI auditing; select via the project’s own evaluation set.

| Provider | Documented capabilities relevant to this product | Strengths | Risks / trade-offs |
|---|---|---|---|
| OpenAI API | Current model catalog describes latest models as image-input capable; model pages list reasoning/tool capabilities. Structured Outputs supports JSON Schema on supported models. | Unified multimodal and structured-output API; choice of flagship, balanced, and lower-cost model tiers; provider ecosystem | Model IDs and capabilities evolve; verify structured output, image resolution/tiling, data retention, and endpoint availability for selected model |
| Google Gemini API | Current Gemini catalog lists text/image/PDF and multimodal model families; structured-output guide documents JSON Schema-based output. | Native multimodal input and long-context options; possible fit for multi-image reasoning and PDF ingestion | Model tiers/statuses change; large context can raise cost and encourage oversized inputs; validate output schema constraints and region/data terms |
| Anthropic Claude API | Current model overview says current models support image input and vision; structured outputs are documented for supported models, including JSON schema-constrained output. | Strong reasoning options and documented structured output; multiple speed/cost tiers | Image resolution/limits and schema support differ by model; validate provider contract and lifecycle; separate embedding provider needed |

**Recommendation:** run a blinded benchmark of representative single- and multi-screen tasks across at least two candidates. Keep the primary multimodal vision/reasoning provider behind `VisionReasoningProvider`; use provider-neutral schemas and validation. Select a separate embedding provider or hosted model behind `EmbeddingProvider` and benchmark retrieval independently. A second inference provider is a portability option, not an automatic synchronous fallback: sending private content to a second vendor requires explicit policy and user-facing disclosure.

Do not route providers solely by low confidence or cost until the quality/cost behavior is measured. Prefer an explicit, auditable configuration and canary migration. Pin model versions where supported; record every model ID used.

## 3. Actual provider selection criteria

Benchmark with the same permissioned test set, prompts, and post-processing:

- Image detail and small-text perception on actual screenshot dimensions.
- Bounding-box localization quality (IoU and useful region coverage).
- Cross-screen consistency and journey reasoning versus independent-audit baseline.
- Supported strict structured output, refusal/error behavior, and schema limitations.
- Latency, throughput limits, rate limits, batch/cache support, and cost per completed audit.
- Data retention/training terms, regional processing, contractual commitments, and incident terms.
- Model availability/retirement windows and version migration support.

Use official documentation and check live pricing during implementation; do not hard-code price assumptions into architecture. Cost drivers are input image tokens/tiles, number of screens and reasoning passes, output length, retries, embedding volume, OCR pages, and reranking. Cost controls: image/screen/page limits, staged reasoning, reusable preprocessing, bounded excerpts, cached embeddings, quotas, and budget alerts.

## 4. Alternatives considered

### Frontend

- **Next.js/React:** recommended for ecosystem and hiring; ensure server routes do not become an accidental second backend that bypasses API controls.
- **SvelteKit/Vue:** viable lower-complexity alternatives; choose for team expertise, not audit-specific capability.

### Backend

- **FastAPI/Python:** recommended for shared AI/document ecosystem.
- **NestJS/TypeScript:** strong modular API and shared types, but document/OCR/model tooling may require a Python worker anyway.
- **Serverless functions:** useful for low-volume control-plane actions, not ideal for long-running extraction/analysis without durable workflow orchestration.

### Vector storage

- **pgvector:** simplest initial operational footprint and relational metadata joins.
- **Dedicated vector DB (Qdrant/Weaviate/Pinecone):** consider for measured scale, recall, or isolation needs; adds another data lifecycle, backup, access-control, and deletion surface.

### OCR/document extraction

- **Open-source libraries:** potentially lower marginal cost and more control; require operating, tuning, and language-quality validation.
- **Managed OCR/document AI:** stronger layout features and reduced operations for supported document types, but per-page cost, residency, and vendor lock-in need review.

### Queue

- **Managed durable queue:** recommended in a chosen cloud for delivery and dead-letter management.
- **Redis-backed workers:** quicker initial setup; must configure persistence, acknowledgments, visibility/retry semantics, and failure recovery before relying on it for durable work.

## 5. Current documentation references

- OpenAI [models](https://developers.openai.com/api/docs/models), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [pricing](https://developers.openai.com/api/docs/pricing), and [data controls](https://developers.openai.com/api/docs/guides/your-data).
- Google [Gemini models](https://aistudio.google.com/docs/models), [structured outputs](https://aistudio.google.com/docs/structured-output), [pricing](https://ai.google.dev/gemini-api/docs/pricing), and [data use](https://ai.google.dev/gemini-api/terms).
- Anthropic [models overview](https://platform.claude.com/docs/en/models/overview), [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [pricing](https://platform.claude.com/docs/en/about-claude/pricing), and [data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention).

Confirm all links, supported features, pricing, and terms again when selecting a provider; public docs are not a substitute for contractual review.

## 6. Phase 02 frontend implementation choices

The Phase 01 recommendation approved Next.js, React, and TypeScript, but did not select a styling system or component library. Phase 02 therefore uses CSS custom properties/design tokens, hand-built accessible React components, and small inline SVG icons rather than adding an unapproved UI package or CSS framework. This keeps the initial dependency surface small and makes the component inventory explicit. These choices do not constrain later backend or AI provider selection.

The frontend demo stores project, audit, and document metadata in browser local storage. Screenshot previews are temporary object URLs and are not persisted; file contents are not uploaded or saved. Replace this demonstration state adapter with the Phase 03/04 API and private-storage services before production use.

## 7. Foundation technology decisions

The foundational implementation resolves the infrastructure choices for the existing application:

| Area | Final choice | Alternatives considered / implication |
|---|---|---|
| Authentication | Amazon Cognito OIDC with NextAuth v4 JWT sessions; FastAPI independently verifies Cognito RS256 access tokens | Auth0/other OIDC providers remain possible through the issuer/JWKS boundary, but provider-specific Cognito app-pool setup must be replaced. Self-hosted identity was rejected to avoid operating a security-critical service |
| API proxy/session handling | Same-origin Next.js server proxy injects the access token from the HttpOnly server session | Direct browser bearer-token API calls were rejected because they expose tokens to browser JavaScript |
| ORM/migrations | SQLAlchemy 2 typed ORM and Alembic | Fits Python/FastAPI and migration tooling; migrations remain explicit release operations |
| Relational database | PostgreSQL using psycopg 3 | SQLite is limited to tests; production guards reject it |
| Object storage | Private AWS S3, presigned PUT/GET, server-generated keys, AWS SDK credential chain | R2/other S3-compatible services can be configured through the endpoint boundary but require separate IAM/CORS/retention validation. MinIO is not a production default |
| Infrastructure templates | CloudFormation for Cognito and private S3 | Templates are not deployed or verified against a live AWS account |

These are implementation decisions, not claims that production services have been provisioned. The web session currently has a one-hour lifetime and the foundation does not refresh the Cognito access token. Product and operations must decide refresh/re-authentication behavior, production region, retention, and service budgets before launch. The AI provider and durable queue remain intentionally unselected until the required product benchmarks and workflow constraints are approved.
