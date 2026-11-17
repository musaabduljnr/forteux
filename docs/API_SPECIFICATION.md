# API Specification

**Status:** Contract outline; foundation subset implemented  
**Last reviewed:** 2026-11-16

This is a resource-oriented contract outline, not a finalized OpenAPI document. All endpoints require TLS and authenticated identity except explicitly public health/readiness endpoints. Tenant context is derived from the validated session/token and membership, never trusted from an unverified request field.

The current foundation implements the routes listed in [BACKEND_ARCHITECTURE.md](./BACKEND_ARCHITECTURE.md). Audit routes persist metadata only; asynchronous jobs, audit screens, findings, prompt operations, knowledge endpoints, pagination, and deletion workflows are future contract items, not currently available API features.

## 1. Conventions

- Prefix: `/api/v1`.
- JSON request/response except direct object-storage transfers.
- UUID resource IDs, UTC ISO-8601 timestamps, pagination with opaque cursors.
- Use `Idempotency-Key` for audit creation, document processing, and other retryable creates.
- Return stable `code`, safe `message`, optional field `details`, and `request_id`; do not expose provider stack traces, secret names, or internal prompts.
- Use `202 Accepted` for asynchronous audit and document jobs. Poll resources or use an authenticated event channel later; polling is the initial default.
- Validate request size and schema at the edge and API.

## 2. Endpoints

### Projects

- `GET /projects` — list projects visible to caller.
- `POST /projects` — create project.
- `GET /projects/{projectId}` — read project.
- `PATCH /projects/{projectId}` — update permitted metadata.
- `DELETE /projects/{projectId}` — request deletion and return deletion status.

### Uploads and assets

- `POST /projects/{projectId}/uploads` — request an upload target after authorization and quota checks; returns asset ID, short-lived signed upload URL, required headers, and expiry.
- `POST /projects/{projectId}/assets/{assetId}/complete` — verify object exists, signature/type/size, then finalize asset.
- `GET /projects/{projectId}/assets` — list assets.
- `DELETE /projects/{projectId}/assets/{assetId}` — remove access and request cleanup.

### Audits

- `POST /projects/{projectId}/audits` — create `single` or `multi` audit with ordered asset IDs, labels, context, and optional knowledge categories; returns `202`, audit ID, job ID, and status URL.
- `GET /projects/{projectId}/audits` — list audit history.
- `GET /projects/{projectId}/audits/{auditId}` — read status, ordered screens, findings, and links to permitted derivatives.
- `POST /projects/{projectId}/audits/{auditId}/retry` — retry a retryable failed stage; idempotent.
- `DELETE /projects/{projectId}/audits/{auditId}` — request deletion.
- `PATCH /projects/{projectId}/audits/{auditId}/findings/{findingId}` — update user-controlled selection/dismissal only; never overwrite model evidence fields.
- `POST /projects/{projectId}/audits/{auditId}/feedback` — submit optional feedback.

### Stitch prompt

- `GET /projects/{projectId}/audits/{auditId}/prompt` — retrieve current prompt/version.
- `PUT /projects/{projectId}/audits/{auditId}/prompt` — save user edit with optimistic version (`If-Match` or version field).
- `POST /projects/{projectId}/audits/{auditId}/prompt/regenerate` — regenerate one prompt from selected finding IDs; returns asynchronous status only if generation is not synchronous.

### Knowledge library

- `POST /projects/{projectId}/knowledge/uploads` — request scoped upload target.
- `POST /projects/{projectId}/knowledge/{documentId}/complete` — verify and enqueue extraction.
- `GET /projects/{projectId}/knowledge` — list project documents and statuses.
- `GET /projects/{projectId}/knowledge/{documentId}` — get metadata, versions, warnings, status.
- `PATCH /projects/{projectId}/knowledge/{documentId}` — rename/categorize or request replacement behavior.
- `POST /projects/{projectId}/knowledge/{documentId}/retry` — retry failed processing.
- `DELETE /projects/{projectId}/knowledge/{documentId}` — hide immediately and enqueue object/vector deletion.
- `GET /knowledge/global` — list global material visible for reference (metadata only, subject to product policy).
- Global upload/management is an administrator-only API surface and should be finalized with the admin product requirements.

### Operations

- `GET /health/live` — process liveness.
- `GET /health/ready` — readiness without sensitive dependency detail.
- `GET /api/v1/jobs/{jobId}` — status only if caller is authorized for its owning resource.

## 3. Representative audit request

```json
{
  "mode": "multi",
  "screens": [
    { "asset_id": "uuid", "sequence": 0, "label": "Choose plan" },
    { "asset_id": "uuid", "sequence": 1, "label": "Checkout" }
  ],
  "context": {
    "product": "Optional",
    "user_goal": "Optional",
    "audience": "Optional",
    "constraints": ["Optional"]
  },
  "knowledge_categories": ["accessibility", "design-system"]
}
```

Response: `202 Accepted` with `audit_id`, `job_id`, `status`, and resource URL. Validate mode/screen count and asset ownership. For multi mode, reject duplicate sequence values, missing assets, or fewer than two screens.

## 4. Error semantics

Use appropriate HTTP statuses: `400` invalid input, `401` unauthenticated, `403` unauthorized, `404` not visible/not found, `409` state/version conflict or duplicate action, `413` upload too large, `415` unsupported media, `422` content cannot be processed, `429` quota/rate limit, `503` temporary dependency outage. Asynchronous worker failures are represented on the audit/document/job resource with stable error codes and retryability.

## 5. Authorization and validation rules

- Check tenant membership, role, project ownership, asset membership, audit ownership, and document scope on every resource operation.
- Never accept client-provided object keys, vector filters, provider model names, confidence values, or finding citations as trusted server-side facts.
- Signed upload/download URLs are short-lived and scoped to one object and operation; uploads are quarantined until server verification.
- Bound array sizes, text fields, image/document dimensions and bytes, and generated content. Rate-limit costly endpoints per identity and tenant.
- Return only fields necessary for the client; redact internal provider request/response payloads.

## 6. Remaining API decisions

Choose polling interval/event transport, global-knowledge administration roles, API versioning, and public-vs-private audit export before those features are implemented.

For the implemented foundation, identity is Cognito OIDC, uploads are limited to declared PNG/JPEG and the configured byte maximum, and direct browser uploads use short-lived S3 presigned URLs. Product retention, region, global-knowledge administration, job/event transport, and full audit/knowledge API contracts remain open for their respective phases.
