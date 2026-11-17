# Foundation Test Report

**Scope:** Backend/API, authentication, database migration, storage URL generation, and frontend compatibility checks.

## Automated checks

Run the backend commands from `backend`; run frontend commands from the repository root:

| Check | Command | Result |
|---|---|---|
| FastAPI import and route registration | `.\.venv\Scripts\python.exe -c "from app.main import app"` | Passed; 14 routes registered |
| Live backend startup | `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 18937`, then `GET /health/live` | Passed; temporary local process returned `{"status":"live"}` and was stopped |
| Backend automated suite | `.\.venv\Scripts\python.exe -m pytest -q` | Passed; 15 tests, 1 upstream Starlette deprecation warning |
| Python compilation | `.\.venv\Scripts\python.exe -m compileall -q app migrations tests` | Passed |
| Frontend lint | `npm run lint` | Passed |
| Frontend TypeScript | `npm run typecheck` | Passed |
| Frontend production build | `npm run build` in an isolated temporary copy | Passed; temporary copy removed without touching the existing development server |
| Frontend dependency audit | `npm audit` | Passed; 0 vulnerabilities |
| Alembic migration | Covered by `test_migrations.py` | Upgrade and downgrade tested against temporary SQLite |
| Auth and authorization | Covered by `test_auth.py` and `test_ownership.py` | Missing/invalid token, verified test identity, JWKS outage, project tenant isolation and authenticated project attribution tested |
| S3 and asset lifecycle | Covered by `test_storage.py` | SigV4 URL expiry and signed content type/length, download response headers, upload idempotency, metadata completion, retrieval URL, and deletion tested offline |
| Health | Covered by `test_health.py` | Liveness, dependency-ready, and dependency-unavailable behavior tested |

## Not tested or not available

- No live PostgreSQL server was configured. SQLite validates basic model/migration behavior, not PostgreSQL-specific behavior, TLS, backups, or performance.
- No live Cognito pool was configured. OIDC verification uses a locally generated RSA key and test JWKS stub; real OAuth redirects, provider claims, key rotation, refresh, and account lifecycle remain unverified.
- No AWS S3 bucket, IAM role, credentials, or CloudFormation deployment was available. Presigned URLs were generated offline using a SigV4-configured SDK client; live CORS, upload/download, IAM, encryption, and deletion remain unverified.
- No cross-user test was run against real authenticated users/provider tokens; authorization isolation is tested against isolated SQLite data and an injected verified principal.
- No screenshot decoding, image signature validation, malware scanning, AI analysis, knowledge processing, or worker execution was tested or implemented.

## Outcome

The software foundation passes the local automated checks above, but the service is not operational for production until its required external services are provisioned and live integration checks pass. The sole backend test warning is emitted by the installed Starlette/httpx test-client integration, not by application code. See [FOUNDATION_IMPLEMENTATION_REPORT.md](./FOUNDATION_IMPLEMENTATION_REPORT.md).
