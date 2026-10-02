# Secure Multi-Tenant RAG

A FastAPI starter application demonstrating JWT authentication, tenant-scoped Qdrant filtering, a second PostgreSQL-backed ACL check, and append-only retrieval auditing.

## Security flow

```text
User -> JWT -> live user/tenant validation -> Qdrant ACL pre-filter
     -> PostgreSQL ACL verification -> audit write -> configured LLM
```

The caller never supplies a tenant ID to the document or chat APIs. Tenant scope comes from the authenticated database user. JWT role claims are validated, but current database roles are used for authorization so role revocation takes effect without waiting for token expiry.

## Run locally on Windows

The app can run without Docker using SQLite and Qdrant's embedded local storage. From PowerShell:

```powershell
cd "E:\Secure Multi tenent RAG"
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python seed_demo.py
```

The seed step creates the local database/vector collection and downloads the configured Sentence Transformers embedding model on its first run. Once that succeeds, the app and embedding model can run offline:

```powershell
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the API. Local data is stored in `local.db` and `local_qdrant`. Demo credentials are `alice/hr`, `bob/employee`, `charlie/hr`, and `david/employee`. Alice and Bob belong to `company_a`; Charlie and David belong to `company_b`.

Chat answer generation still requires an LLM. To enable it, set `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` to a local OpenAI-compatible server or a hosted provider before starting the app. Without those settings, `POST /chat` responds with `503`; the rest of the local API and retrieval storage work without an LLM.

## Start with Docker Compose

1. Copy `.env.example` to `.env`, set a random `JWT_SECRET` and database password, and configure an OpenAI-compatible `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.
2. Start the services:

   ```powershell
   docker compose up --build
   ```

3. In another terminal, seed demo identities:

   ```powershell
   docker compose exec api python seed_demo.py
   ```

   Demo credentials are `alice/hr`, `bob/employee`, `charlie/hr`, and `david/employee`. These are for local demonstrations only. Alice and Bob belong to `company_a`; Charlie and David belong to `company_b`.
4. Sign in to get a bearer token:

   ```powershell
   $token = (Invoke-RestMethod -Method Post http://localhost:8000/auth/token `
     -ContentType 'application/json' -Body '{"user_id":"alice","password":"hr"}'
   ).access_token
   ```
5. Submit a document as an HR user:

   ```powershell
   Invoke-RestMethod -Method Post http://localhost:8000/documents `
     -Headers @{ Authorization = "Bearer $token" } -ContentType 'application/json' `
     -Body '{"document_id":"hr_salary_001","title":"Salary policy","content":"Confidential salary policy text.","allowed_roles":["hr"],"classification":"confidential"}'
   ```

   The API embeds and indexes submitted chunks. The document is persisted only after Qdrant indexing succeeds.
6. Ask a question via `POST /chat` with `{"question":"Summarize the salary policy"}` and the bearer token.

The first embedding request downloads the configured Sentence Transformers model. Chat returns `503` until the LLM environment settings point to an available OpenAI-compatible chat-completions API.

## API

- `POST /auth/token`: authenticate and issue a signed JWT.
- `POST /documents`: create and index a tenant-local document (HR/admin).
- `GET /documents`: list documents belonging to the caller's tenant.
- `PUT /documents/{document_id}/acl`: replace ACLs and update Qdrant payloads (HR/admin).
- `POST /chat`: retrieve authorized chunks, write audit events, and generate an answer.
- `GET /admin/audit/document/{document_id}`: view document retrieval history (admin, tenant-scoped).
- `GET /health`: liveness endpoint.

## Authorization and revocation

Qdrant applies a mandatory `tenant_id` condition and requires at least one role or explicit-user ACL match before returning candidates. The application then loads each document's current ACL from PostgreSQL and checks it before any chunk is included in the LLM context. A mismatch is rejected and logged as a security error.

ACL updates commit to PostgreSQL first, then update the Qdrant payload. If Qdrant is unavailable, the API reports the error; stale Qdrant permissions cannot bypass the PostgreSQL check. The audit table has a PostgreSQL trigger that rejects updates and deletes.

## Tests

```powershell
pip install -r requirements.txt pytest
pytest -q
```

The tests cover role/user ACL matching, tenant isolation, revocation decisions, and chunk overlap. End-to-end tests against live PostgreSQL, Qdrant, the embedding model, and an LLM require those services to be running and are not simulated by the unit suite.

## Production hardening

- Replace demo passwords and development secrets; manage secrets outside source control.
- Use TLS, rate limits, request-size limits, and a production database role restricted from modifying/deleting audit rows.
- Restrict document ingestion and ACL management to trusted operators; add malware/content checks as appropriate.
- Use migrations for schema changes and an outbox/retry strategy for reliable Qdrant synchronization.
- Configure retention and privacy controls for stored retrieval queries.
- Add integration tests and measure leakage, latency, filtering overhead, and revocation delay against the deployed services; do not claim unmeasured metrics.
