# Product Requirements

**Status:** Draft for review — Phase 01  
**Product:** AI-Powered UI/UX Auditor  
**Last reviewed:** 2026-11-16

## 1. Product statement

Help designers and product teams turn interface screenshots into evidence-aware, prioritized design feedback and an editable Google Stitch prompt. Users may audit one screen or an explicitly ordered set of screens. The product augments, but does not replace, professional review or functional testing.

## 2. Users and primary needs

- **Product/UI designer:** identify visual hierarchy, consistency, and accessibility concerns; produce actionable redesign instructions.
- **UX researcher/product manager:** review a proposed flow and understand friction or missing transitions visible in the supplied screens.
- **Design lead/team:** apply shared design guidance and compare consistency across projects.
- **Knowledge administrator:** curate global or project-only reference material and monitor its processing.

## 3. Scope

### In scope for the initial product

- Authenticated user workspaces and projects.
- Single-screen audit and ordered multi-screen audit.
- Image upload, preview, reorder, and removal before submission.
- Individual screen findings and genuine cross-screen findings.
- Numbered annotations overlaid on original screenshots, with accessible finding-list navigation.
- Severity, confidence, evidence type, uncertainty, rationale, recommendation, and optional source references for findings.
- Global and project-specific knowledge upload, processing, categorization, replacement, deletion, and status.
- One editable, copyable Stitch prompt by default, based on findings selected by the user.
- Audit history, processing status, and explicit error/retry states.
- User feedback and evaluation instrumentation with appropriate privacy controls.

### Out of scope until separately approved

- Browser crawling, live-site inspection, DOM/source-code analysis, or automated interaction testing.
- Claims that screenshots establish runtime behavior, keyboard operation, or screen-reader compatibility.
- Automatic redesign/image generation or direct Stitch API integration.
- Team billing, enterprise SSO, public sharing, and third-party integrations beyond prompt copy/export.
- Training foundation models on customer assets.

## 4. Modes and functional requirements

### Mode A — Single Screen Audit

1. Accept one supported raster screenshot and preserve its original dimensions and aspect ratio.
2. Ask for optional context (product, screen purpose, audience, platform, constraints).
3. Identify visible elements and evaluate visual hierarchy, clarity, consistency, and screenshot-evident accessibility risks.
4. Return findings with stable IDs, issue category, title, valid normalized bounding box or an explicitly screen-level scope, severity, calibrated confidence, description, impact, recommendation, and evidence classification.
5. Number and render findings on the image; selecting a marker and selecting its list item are equivalent.
6. Generate exactly one complete, editable prompt from selected findings. If none are selected, use all findings.

### Mode B — Multi-Screen UX Audit

1. Accept 2 or more screenshots; the product must publish a configurable maximum before launch (recommended initial maximum: 12).
2. Let users arrange and label the intended sequence and optionally describe the journey and expected outcome.
3. Analyze each screen individually using the same baseline as Mode A.
4. Compare screens for repeated components, tokens, layout patterns, wording, and visible navigation conventions.
5. Build an ordered, evidence-backed journey representation. Detect apparent gaps, inconsistent controls/labels, confusing transitions, and friction only when supported by the supplied sequence and context.
6. Keep screen-level findings distinct from cross-screen findings; a cross-screen finding may reference multiple screens and bounding boxes.
7. Generate one prompt that names each screen and preserves its order and relationships, and addresses only selected findings.
8. State that sequence and transitions are user-provided or inferred from screenshots; never imply that the actual product was traversed.

## 5. Knowledge library requirements

- Accept PDF, DOCX, TXT, and Markdown initially. Consider HTML and PPTX after extraction and security evaluation.
- Validate content independently of file extension; apply configurable per-file, per-project, and per-tenant limits.
- Extract text with page/slide and source offsets when available; OCR scanned PDFs as needed.
- Chunk, embed, index, and retrieve with document, version, category, scope, and page metadata.
- Support global administrator-managed knowledge and project-scoped knowledge; project retrieval must not expose another project’s material.
- Display queued/processing/ready/failed/deleting states, actionable errors, retry, replacement, and deletion.
- Detect duplicates by tenant/scope and cryptographic content hash. A replacement is versioned and becomes active only after successful processing.
- Retrieved knowledge supplements general model knowledge and visual evidence; it never becomes the model’s only source of reasoning.
- Label visual observations, source-supported advice, and general professional advice separately. Show citations only for retrieved source passages and retain page references when available.

## 6. User experience requirements

- Explain supported formats, image limits, privacy/retention behavior, and analysis limitations before upload.
- Show asynchronous progress and allow users to leave and return to an audit.
- Clearly distinguish observations from hypotheses; make confidence and uncertainty legible rather than presenting a score as certainty.
- Provide keyboard-accessible controls and a non-canvas finding list for annotations.
- Allow users to edit issue selection and generated prompt without changing source findings.
- Provide an explicit empty/partial result state; never represent a failed analysis as a successful clean audit.

## 7. Quality attributes and proposed service targets

Targets are design goals for a representative beta workload, not guarantees; validate them with pilot traffic and cost measurements.

| Attribute | Proposed target |
|---|---|
| Availability | 99.5% monthly for authenticated product/API, excluding planned maintenance and provider outages |
| API responsiveness | p95 under 500 ms for non-analysis reads/writes; analysis is asynchronous |
| Analysis completion | p95 under 90 seconds for one screen and 180 seconds for 12 screens, excluding documented provider outages |
| Durability | Persistent audit/job state; retry-safe processing and idempotent callbacks |
| Isolation | No cross-tenant or cross-project asset, audit, or knowledge access |
| Accessibility | WCAG 2.2 AA target for the application UI; screenshot findings are not a conformance certification |
| Explainability | Every published finding has evidence classification, confidence, and a concise rationale |
| Observability | Correlation ID and stage status for each job; no raw image/document contents in routine logs |

## 8. Success measures

- Task completion and user-rated usefulness of findings and Stitch prompts.
- Finding precision, recall, localization quality, and severity agreement against expert-labeled sets.
- Citation precision and project-scope retrieval leakage tests.
- Multi-screen consistency/flow quality against expert pairwise and journey annotations.
- Completion latency, retry/failure rate, and cost per completed audit/document.
- Prompt edit/copy rates and issue dismissal/acceptance rates (interpret as feedback, not ground truth).

## 9. Assumptions and open decisions

The initial design assumes a hosted SaaS product, a single cloud region for launch, private uploads, and user-initiated audits. Confirm deployment region, retention/deletion policy, upload/plan limits, supported languages, global-knowledge ownership, and whether organization/team workspaces are required before implementation. See `DEVELOPMENT_ROADMAP.md`.
