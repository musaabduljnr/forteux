# Security and Privacy

**Status:** Security baseline; foundation controls implemented, production review outstanding  
**Last reviewed:** 2026-11-16

## 1. Security objectives

Protect private interface screenshots, user/project documents, findings, and prompts; prevent tenant/project data leakage; keep provider credentials server-side; make deletion, retention, and AI-provider data handling explicit; and treat all uploaded content and model responses as untrusted.

## 2. Identity, access, and isolation

- Use a managed OIDC identity provider; validate issuer, audience, signature, expiry, and session lifecycle. Apply MFA for administrators and privileged global-knowledge operations.
- Model tenant membership and project roles explicitly. Deny by default and authorize on every API, job, download, and deletion path.
- Carry immutable tenant/project ownership in queued jobs; re-check current access and resource state before processing or returning results.
- Scope object keys by opaque tenant/project/resource IDs and enforce private bucket policy. Do not expose predictable public URLs.
- Test cross-tenant and cross-project access for list, get, signed URL, audit, retrieval, prompt, and deletion operations.

## 3. File and content controls

- Allowlist supported file formats; inspect file signatures, MIME, byte size, dimensions, page count, and decompression expansion.
- Upload first to quarantine; scan for malware and malformed active content; parse in isolated, resource-limited worker processes with timeouts and no unnecessary filesystem/network access.
- Reject or explicitly handle password-protected/encrypted files, embedded objects, external references, and unsupported archive/container types.
- Prevent image decompression bombs and abusive dimensions; normalize to safe derived formats without altering the retained original.
- Treat OCR text and document text as untrusted input. Defend against prompt injection by separating system instructions and reference content, reducing tool access, and testing adversarial samples.

## 4. Secrets, network, and provider controls

- Store database credentials, signing keys, and AI-provider keys in a managed secrets service; rotate and scope by environment/service.
- Never place secrets in browser code, prompts, logs, source control, or error payloads.
- Restrict worker egress to approved services and endpoints. Use TLS and service identity; encrypt databases, backups, queue traffic, and object storage at rest.
- Select AI providers/models through a server-side allowlisted capability registry. Apply per-provider budgets, quotas, timeouts, redaction, and fail-closed behavior for policy violations.
- Before launch, review provider retention/training terms, regional processing, subprocessor list, DPA, deletion support, and data-processing settings. Do not claim zero retention unless contract and configuration establish it.

## 5. Privacy and data lifecycle

- Collect only necessary account and audit context. Make context fields optional and explain why they help.
- Document which images, documents, prompts, extracted text, embeddings, and logs are sent to each processor.
- Set a user-approved retention policy for original uploads, derivatives, audit results, and operational traces; expose deletion requests and status.
- On deletion, immediately revoke access and retrieval, then remove objects, cached derivatives, chunks/embeddings, associated findings/prompts, and backups according to documented retention limits. Verify cleanup and report any delay.
- Do not use customer content to train or evaluate models by default. Any opt-in must be separate, informed, revocable, and de-identified where feasible.
- Minimize telemetry; use opaque IDs and redact prompt/image/document bodies. Restrict and audit access to exceptional debugging data.
- Determine applicable privacy obligations, data residency, age restrictions, and incident-notification obligations with legal/privacy review before launch.

## 6. Model-output safety and integrity

- Validate structured model outputs against schemas and business rules before persistence/rendering.
- Treat model-generated links, citations, IDs, issue severity, boxes, and HTML/Markdown as untrusted; escape output and validate provenance and geometry.
- Prevent a model or retrieved document from triggering arbitrary tools, external network requests, destructive actions, or privilege changes.
- Distinguish system-verified facts from model hypotheses and source-supported recommendations in the interface.
- Provide user correction/dismissal mechanisms and an incident path for harmful or misleading content.

## 7. Threat and abuse cases

| Threat | Primary controls |
|---|---|
| IDOR / tenant data leakage | Membership checks, scoped queries, opaque IDs, negative authorization tests |
| Malicious file/parser exploit | Quarantine, scanning, sandboxing, resource limits, patched parsers |
| Prompt injection in uploaded docs | Untrusted-data boundaries, no instruction execution, minimal tools, adversarial eval |
| Credential exposure | Secret manager, server-only access, redaction, rotation |
| Cost exhaustion / denial of service | quotas, file/page/screen limits, rate/concurrency limits, budgets |
| Citation/box fabrication | allowlisted evidence IDs, schema and geometry validation, audit trails |
| Incomplete deletion | tombstone/access revocation, per-store deletion tasks, reconciliation and status |
| Provider breach or policy change | provider review, data minimization, configurable routing, incident and migration plan |

## 8. Launch security gates

Complete a data-flow inventory and privacy review; threat model; dependency and container scanning; authz test suite; upload-parser testing; secret scanning; backup/deletion exercise; provider contract review; incident-response runbook; and independent security assessment appropriate to launch scale. This document is a design baseline, not a certification.

## 9. Foundation implementation notes

- The web application uses a NextAuth v4 encrypted JWT session cookie with Cognito OIDC. A same-origin Next.js server route forwards the access token to FastAPI; the browser is not given the token or Cognito client secret.
- FastAPI validates Cognito RS256 access tokens using issuer/JWKS, expiry, `token_use`, and `client_id`, then derives the local identity from issuer and subject. Project access is checked through a tenant membership on each request.
- PostgreSQL-oriented models and migration use composite tenant/project foreign keys. Tests exercise cross-tenant project isolation.
- The S3 template blocks public access, enables server-side encryption, denies non-TLS transport, and scopes browser CORS to the configured origin. S3 credentials remain server-side.
- Upload completion checks only S3 content type and byte count against request metadata. Image signature validation, decoding, malware scanning, and quarantine are intentionally not implemented in the foundation. The asset status therefore remains `uploaded_unverified`.
- Local tests and templates do not constitute deployment or security certification. Live Cognito, PostgreSQL TLS, S3 IAM/CORS, deletion, retention, recovery, and privacy reviews remain launch gates.
