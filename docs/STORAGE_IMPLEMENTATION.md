# Storage Implementation

**Decision:** private Amazon S3 bucket with server-generated object keys and short-lived presigned URLs.

## Options compared

| Option | Assessment | Decision |
|---|---|---|
| Amazon S3 | Mature private buckets, IAM, encryption, lifecycle policies, regional controls, presigned operations; fits AWS-first stack | Selected |
| S3-compatible managed storage (for example Cloudflare R2) | Can reduce egress or provide alternative regional/price options; compatibility and IAM/CORS details differ | Optional endpoint adapter; requires independent deployment/security validation |
| Self-hosted MinIO | Useful for controlled development/testing | Not a production default; requires operating availability, replication, encryption, access control, and backups |

The API requires `AWS_REGION` and `S3_BUCKET`. `S3_ENDPOINT_URL` is optional for compatible services and must use HTTPS in production. AWS credentials are obtained through the AWS SDK credential chain (prefer workload IAM roles); do not store long-lived access keys in source or browser variables.

## Object lifecycle

1. An authenticated member requests an upload for a project. The API enforces the declared size limit, PNG/JPEG MIME/extension pairing, and idempotency.
2. The API generates an opaque key under tenant/project/asset UUIDs and returns a short-lived presigned PUT URL plus required headers.
3. The browser uploads directly to S3 over TLS. Bucket CORS allows only the configured web origin and the required PUT/header set.
4. The authenticated completion endpoint performs `HeadObject` and checks stored content length and content type against the declaration, then records `uploaded_unverified`.
5. Authenticated retrieval returns a short-lived presigned GET URL forced to attachment/octet-stream.
6. Deletion marks the database row inaccessible before removing the object. If cleanup fails, the row remains `deleting` for visible retry/operations handling.

No browser request supplies an S3 key. The bucket template blocks public access, enables AES-256 server-side encryption, denies non-TLS transport, aborts incomplete multipart uploads, and does not configure public ACLs. The current template does not enable versioning. If versioning is later enabled, the API role must have carefully scoped version-list/delete permissions and the cleanup workflow must be exercised.

## Important content-validation boundary

The foundation validates request metadata and checks the metadata S3 stored. It does not inspect magic bytes, decode image content, enforce image dimensions, scan for malware, or create derived images. A completed asset is intentionally labeled `uploaded_unverified`. Do not treat metadata checks as proof that the bytes are a safe/valid screenshot; implement quarantine and image validation in the approved processing phase.

## IAM and deployment requirements

The API role needs bucket-scoped permissions for presigned PUT/GET, `HeadObject`, and object deletion; if versioning is enabled, grant version listing/deletion explicitly. The bucket must remain private and the policy must prevent public access. The browser receives only short-lived object-specific URLs. Verify that CloudFront, logging, lifecycle, backups, and retention do not unintentionally make content public or retain deleted content beyond policy.

`infra/private-screenshots-bucket.yaml` is a CloudFormation template, not evidence of a deployed bucket. No real bucket, IAM role, credentials, or live transfer were available during implementation.
