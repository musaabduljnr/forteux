# Authentication Implementation

**Decision:** Amazon Cognito OIDC, NextAuth v4 encrypted JWT sessions in Next.js, and independent RS256 bearer-token validation in FastAPI.

## Options compared

| Option | Benefits | Trade-offs | Decision |
|---|---|---|---|
| Amazon Cognito | AWS integration, OIDC/OAuth, managed user pool, compatible with the recommended AWS storage path | User-pool configuration and hosted UI are AWS-specific; operational configuration is required | Selected |
| Auth0 or another managed OIDC provider | Mature hosted identity, broad integrations, provider portability through OIDC | Separate vendor, pricing, and data-processing review; no benefit justifying a second provider for this AWS-first foundation | Not selected |
| Self-hosted identity (for example Keycloak) | Deployment and data control | Adds a security-critical service and operations burden; not appropriate for this foundation | Not selected |

For the web session, the existing Next.js application uses NextAuth v4 rather than implementing a custom cookie/session system. A server-side API proxy was selected over direct browser-to-API bearer-token calls so the access token and backend address remain server-side.

## Sign-in and request flow

1. The user selects **Sign in with Cognito** when OIDC is enabled.
2. NextAuth uses the OAuth authorization-code flow and server-held Cognito client secret.
3. NextAuth stores its session in an encrypted, HttpOnly cookie. The browser does not receive the raw Cognito access token.
4. `/api/backend/*` retrieves the server-side session token and forwards it as `Authorization: Bearer ...`.
5. FastAPI validates the token and maps `(issuer, subject)` to a local user record.
6. On first verified access, the backend creates the user, a personal tenant, and an owner membership. Tenant/project identity never comes from a frontend-supplied user ID.

## Backend token validation

The API validates RS256 signature against the issuer's JWKS, issuer, expiry, required `iat`/`sub` claims, Cognito `token_use=access`, and the configured Cognito `client_id`. The `client_id` claim is used for access-token client validation; Cognito access tokens do not use an ID-token audience check in the same way. JWKS clients are cached by URL. An identity-provider key-fetch outage returns 503; malformed, expired, wrong-issuer, wrong-client, or non-access tokens return 401.

Endpoints use FastAPI bearer authentication and query records through the verified principal's tenant membership. Disabled users are rejected. The API does not accept a session header, user ID, or tenant ID as proof of identity.

## Session lifecycle

NextAuth is configured with a one-hour JWT session. The Cognito app client template uses the authorization-code flow and a one-hour access token. This implementation stores the access token and expiry in the encrypted NextAuth JWT but does not refresh it; after expiry the proxy returns an authentication error and the user must sign in again. A production product decision is needed for seamless refresh/rotation and sign-out/revocation semantics.

## Configuration

Web server variables:

- `NEXTAUTH_URL`
- `NEXTAUTH_SECRET` (unique, high-entropy secret per environment)
- `COGNITO_ISSUER`
- `COGNITO_CLIENT_ID`
- `COGNITO_CLIENT_SECRET`
- `NEXT_PUBLIC_OIDC_ENABLED=true` only when the matching server configuration is deployed
- `BACKEND_API_URL` (server-only)

Backend variables:

- `OIDC_ISSUER`
- `OIDC_CLIENT_ID`
- Optional `OIDC_JWKS_URL`; otherwise derived from the issuer's `/.well-known/jwks.json`

Never put client secrets, API tokens, database credentials, or S3 credentials in `NEXT_PUBLIC_*` variables. Keep them in a managed secret store in deployed environments.

## Security and verification

`infra/cognito-user-pool.yaml` defines an email-based user pool, OAuth client, callback/logout URLs, password policy, optional MFA, and hosted UI domain. The template is not deployed by this repository session. Restrict callback URLs to exact environment origins, require HTTPS outside local development, enable MFA for administrators, and validate account recovery, access reviews, and user lifecycle before production.

Automated tests cover missing bearer tokens, rejection of non-access tokens, valid signed test-token identity provisioning, and temporary JWKS failure behavior. They do not authenticate against a live Cognito user pool.
