# Environment Configuration

Use separate environment values and secrets for local development, test, staging, and production. Keep `.env.local` and `backend/.env` out of version control; the committed `.env.example` files contain placeholders only.

## Next.js web application

Copy the root `.env.example` to `.env.local` and set:

| Variable | Required | Notes |
|---|---|---|
| `NEXTAUTH_URL` | Yes | Exact web origin, including scheme |
| `NEXTAUTH_SECRET` | Yes | Generate a unique random secret for each environment; never keep the sample placeholder |
| `COGNITO_ISSUER` | For sign-in | Cognito User Pool issuer URL |
| `COGNITO_CLIENT_ID` | For sign-in | OAuth app-client ID |
| `COGNITO_CLIENT_SECRET` | For sign-in | Server-only secret |
| `NEXT_PUBLIC_OIDC_ENABLED` | For sign-in | Set to `true` only when all Cognito values are valid |
| `BACKEND_API_URL` | For API requests | Server-only FastAPI base URL including `/api/v1`; HTTPS in production |

Generate a session secret with Node.js:

```powershell
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

Register the exact NextAuth callback URL (`/api/auth/callback/cognito`) and logout URL with Cognito. Use HTTPS for deployed URLs.

## FastAPI backend

Copy `backend/.env.example` to `backend/.env` and set:

| Variable | Required | Notes |
|---|---|---|
| `APP_ENV` | Yes | `development`, `test`, or `production`; production guards are enabled in production |
| `LOG_LEVEL` | No | Defaults to `INFO` |
| `API_PREFIX` | No | Defaults to `/api/v1` |
| `DATABASE_URL` | Yes for ready service | PostgreSQL URL, preferably `postgresql+psycopg://...`; production TLS must use `sslmode=require`, `verify-ca`, or `verify-full` |
| `OIDC_ISSUER` | Yes for authentication | Cognito User Pool issuer |
| `OIDC_CLIENT_ID` | Yes for authentication | Must match the access-token `client_id` claim |
| `OIDC_JWKS_URL` | No | Derived from issuer when omitted |
| `AWS_REGION` | Yes for storage | Bucket's AWS region |
| `S3_BUCKET` | Yes for storage | Private bucket name |
| `S3_ENDPOINT_URL` | No | Compatible endpoint; HTTPS required in production |
| `S3_UPLOAD_TTL_SECONDS` | No | 60-900 seconds; default 300 |
| `S3_DOWNLOAD_TTL_SECONDS` | No | 60-900 seconds; default 300 |
| `MAX_UPLOAD_BYTES` | No | Defaults to 10 MiB |
| `ALLOWED_ORIGINS` | No | Comma-separated exact browser origins for direct API CORS; same-origin proxy is used by the web app |

For local development set `APP_ENV=development`; configure test/placeholder credentials only for local/test usage. Do not configure production against SQLite or local filesystem storage. In production, inject secrets from a managed secret store and use workload identity for AWS access.

## Local commands

Run commands from the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

The current requirements are also available as `requirements.txt` and `requirements-dev.txt` for pip-based environment setup. `/health/live` checks only process liveness. `/health/ready` returns 503 until the database, OIDC configuration, and S3 bucket access check succeed.

## Secret handling and deployment gates

- Never commit `.env`, private keys, client secrets, database passwords, AWS access keys, bearer tokens, or presigned URLs.
- Do not prefix server-only secrets with `NEXT_PUBLIC_`.
- Rotate secrets per environment and restrict access by service/role.
- Restrict Cognito callback/logout URLs, S3 IAM permissions, database network access, and CORS to the deployed service origins.
- Confirm bucket encryption, public access block, TLS-only policy, PostgreSQL TLS, backups, recovery tests, retention/deletion policy, and monitoring before production.
- The templates in `infra/` are not deployed by these instructions. No live Cognito, PostgreSQL, or S3 configuration is present in this workspace.
