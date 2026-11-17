# Phase 03 Implementation Plan

**Status:** Backend foundation is implemented; screenshot processing has not started. Stop here pending user review and approval.

## Foundation now present

- Next.js frontend with a Cognito/NextAuth session boundary and same-origin authenticated API proxy.
- FastAPI service, structured validation/errors, request IDs, liveness/readiness routes, and modular API/service layout.
- SQLAlchemy 2 models and reversible Alembic migration for users, tenants, memberships, projects, audits, and screen assets.
- Cognito-compatible access-token verification and tenant membership ownership checks.
- Private S3-compatible storage integration for short-lived upload/download URLs, metadata confirmation, and deletion.
- Reusable frontend API client and local configuration templates.

The foundation test suite uses isolated SQLite data, generated test keys, and offline S3 URL generation. No PostgreSQL, Cognito pool, AWS bucket, IAM role, or CloudFormation stack is configured or claimed operational. See [FOUNDATION_TEST_REPORT.md](./FOUNDATION_TEST_REPORT.md).

## Phase 03 scope after approval

1. Integrate the existing screenshot UI with the authenticated project/asset APIs, preserving current frontend behavior and screen ordering.
2. Validate uploaded file signatures, MIME type, dimensions, decode behavior, decompression limits, and size. Quarantine objects until verification completes.
3. Preserve originals and create safe derived assets with orientation/dimension mapping; do not begin AI analysis.
4. Implement accurate upload progress, retry/cancel, replacement/removal, processing state, and cleanup UX.
5. Add tests for malformed and oversized files, cross-user access, storage failure, cleanup, and geometry preservation.
6. Document and validate the approved retention policy and production bucket/IAM configuration before customer uploads.

Do not implement AI findings, OCR, knowledge-document processing, embeddings, vector retrieval, or Stitch generation in this phase.

## Decisions and prerequisites

### Selected for the implementation foundation

- OIDC provider: Amazon Cognito; NextAuth v4 sessions; FastAPI independently verifies access tokens.
- Database and ORM: PostgreSQL, SQLAlchemy 2, Alembic.
- Storage: private AWS S3, with an optional S3-compatible endpoint boundary.
- Ownership model: tenant workspaces and memberships; an initial verified user receives a personal tenant.

### Still required before production customer data

- Provision Cognito, PostgreSQL, S3, IAM roles, TLS networking, and secret management in the selected region.
- Select and document retention/deletion periods, incident/support ownership, and applicable privacy obligations.
- Confirm byte, dimension, and screen-count limits. Current 10 MiB backend limit and 12-screen frontend limit are provisional.
- Exercise live OAuth, PostgreSQL migrations/TLS, direct S3 transfer, CORS, deletion, and cross-user isolation in staging.

Do not substitute fake authentication, public buckets, or local filesystem/SQLite persistence for production services.
