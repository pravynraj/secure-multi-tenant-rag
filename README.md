# secure-multi-tenant-rag
Secure multi-tenant RAG API with JWT authentication, tenant-isolated Qdrant retrieval, PostgreSQL ACL validation, and append-only retrieval auditing.
# Secure Multi-Tenant RAG

A security-focused **Retrieval-Augmented Generation (RAG)** API built with **FastAPI**, designed to enforce tenant isolation and document-level access control throughout the retrieval pipeline.

The system combines **JWT authentication**, **tenant-scoped Qdrant filtering**, **PostgreSQL-backed ACL verification**, and **append-only retrieval auditing** to prevent unauthorized documents from reaching the LLM context.

## Overview

Traditional RAG systems can retrieve relevant information without sufficiently considering **who is allowed to access that information**.

This project addresses that problem by making authorization part of the retrieval pipeline.

### Security Flow

```text
User
  │
  ▼
JWT Authentication
  │
  ▼
Live User & Tenant Validation
  │
  ▼
Qdrant Tenant + ACL Pre-Filter
  │
  ▼
PostgreSQL ACL Verification
  │
  ▼
Audit Event
  │
  ▼
Authorized Context
  │
  ▼
LLM
```

The caller does not provide a tenant ID to the document or chat APIs. Tenant scope is derived from the authenticated database user.

## Key Features

* JWT-based authentication
* Multi-tenant architecture
* Tenant-isolated document retrieval
* Qdrant vector database
* Role-based access control
* User-specific ACL support
* PostgreSQL-backed authorization verification
* Retrieval auditing
* Protection against stale vector-store permissions
* Document ingestion and embedding
* LLM-compatible chat endpoint
* Docker Compose deployment
* Local SQLite development mode
* FastAPI automatic Swagger documentation
* Unit tests for authorization and tenant isolation

## Technology Stack

| Technology            | Purpose                                  |
| --------------------- | ---------------------------------------- |
| Python                | Core programming language                |
| FastAPI               | REST API framework                       |
| SQLAlchemy            | Database ORM                             |
| PostgreSQL            | Persistent database and ACL verification |
| SQLite                | Local development database               |
| Qdrant                | Vector database                          |
| Sentence Transformers | Text embeddings                          |
| PyJWT                 | JWT authentication                       |
| Passlib / bcrypt      | Password hashing                         |
| Docker                | Containerization                         |
| Docker Compose        | Multi-service orchestration              |
| OpenAI-compatible API | LLM integration                          |
| Uvicorn               | ASGI server                              |

The main dependencies include FastAPI, SQLAlchemy, PostgreSQL/psycopg, PyJWT, Qdrant Client, and Sentence Transformers.

## Architecture

The application uses multiple security layers.

### 1. Authentication

Users authenticate through:

```http
POST /auth/token
```

The API generates a signed JWT containing authentication and role information.

### 2. Tenant Isolation

Every authenticated user belongs to a tenant.

For example:

```text
Company A
├── Alice - HR
└── Bob - Employee

Company B
├── Charlie - HR
└── David - Employee
```

The tenant is determined from the authenticated user rather than being supplied by the API caller.

### 3. Qdrant Filtering

Qdrant applies a mandatory tenant condition and ACL-related filtering before candidate documents are returned.

```text
tenant_id = authenticated_user.tenant_id
       +
role/user ACL match
```

### 4. PostgreSQL ACL Verification

Qdrant filtering is not treated as the final security boundary.

The application loads the current document ACL from PostgreSQL and verifies authorization again before a chunk is included in the LLM context.

This provides an additional protection layer when permissions have changed.

### 5. Retrieval Auditing

Retrieval events are recorded in PostgreSQL.

The audit table is designed to be append-only, with database protection against updates and deletes.

## Security Model

The project follows a **defense-in-depth** approach:

```text
Authentication
      ↓
Tenant Validation
      ↓
Vector Database Filtering
      ↓
Database ACL Verification
      ↓
Audit Logging
      ↓
LLM Context
```

If the Qdrant permissions become stale, the PostgreSQL ACL verification can still reject the unauthorized document.

ACL changes are committed to PostgreSQL first and then synchronized to Qdrant.

## API Endpoints

| Method | Endpoint                              | Purpose                                            |
| ------ | ------------------------------------- | -------------------------------------------------- |
| POST   | `/auth/token`                         | Authenticate and issue JWT                         |
| POST   | `/documents`                          | Create and index a document                        |
| GET    | `/documents`                          | List tenant documents                              |
| PUT    | `/documents/{document_id}/acl`        | Update document ACL                                |
| POST   | `/chat`                               | Retrieve authorized context and generate an answer |
| GET    | `/admin/audit/document/{document_id}` | View retrieval history                             |
| GET    | `/health`                             | Health check                                       |

## Local Development

### Requirements

* Python 3.10+
* pip
* Git
* Optional: Docker Desktop
* Optional: OpenAI-compatible LLM server/provider

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/secure-multi-tenant-rag.git
cd secure-multi-tenant-rag
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Seed demo data

```powershell
python seed_demo.py
```

The seed script creates demonstration users and documents for two separate tenants and indexes the demo documents into Qdrant.

### 5. Start the API

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

FastAPI's Swagger UI provides interactive API documentation.

## Docker Deployment

The project includes Docker Compose configuration for:

```text
API
 │
 ├── PostgreSQL 16
 │
 └── Qdrant 1.12.4
```

The Compose configuration exposes the API on port `8000` and Qdrant on port `6333`. PostgreSQL and Qdrant health checks are also configured.

Start the application:

```powershell
docker compose up --build
```

Then seed the demo data:

```powershell
docker compose exec api python seed_demo.py
```

## Environment Variables

Create a `.env` file based on `.env.example`.

```env
DATABASE_URL=
QDRANT_URL=
JWT_SECRET=
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
POSTGRES_PASSWORD=
```

Never commit real API keys, passwords, or production secrets.

## Demo Users

The seed script provides two tenants:

### Company A

```text
alice / hr
bob / employee
```

### Company B

```text
charlie / hr
david / employee
```

These accounts are intended only for local demonstration.

## Example Workflow

### 1. Authenticate

```http
POST /auth/token
```

Receive:

```text
Bearer JWT
```

### 2. Create a document

An authorized HR/admin user can submit a document.

```text
Document
   ↓
Chunking
   ↓
Sentence Transformer Embedding
   ↓
Qdrant Index
```

### 3. Ask a question

```http
POST /chat
```

The system:

```text
Question
   ↓
Authentication
   ↓
Tenant identification
   ↓
Qdrant filtered retrieval
   ↓
PostgreSQL ACL verification
   ↓
Audit event
   ↓
Authorized context
   ↓
LLM
   ↓
Answer
```

## Testing

Install pytest:

```powershell
pip install pytest
```

Run:

```powershell
pytest -q
```

The test suite covers areas including:

* Role/user ACL matching
* Tenant isolation
* Authorization revocation decisions
* Chunk overlap

End-to-end testing requires the relevant external services to be running.

## Production Considerations

Before production deployment:

* Replace all demo credentials
* Use strong production secrets
* Enable TLS
* Add rate limiting
* Add request-size limits
* Restrict document ingestion and ACL management
* Use database migrations
* Add reliable Qdrant synchronization/retry mechanisms
* Configure audit-data retention
* Add integration tests
* Measure retrieval leakage, latency, filtering overhead, and revocation delay

These items are intentionally listed as hardening requirements rather than claiming that they are already implemented.

## Project Structure

```text
secure-multi-tenant-rag/
│
├── app/
│   ├── auth/
│   ├── ingestion/
│   ├── models/
│   ├── retrieval/
│   └── main.py
│
├── tests/
│
├── seed_demo.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Why This Project?

This project demonstrates how RAG systems can be designed with **authorization and tenant isolation as first-class components**, rather than treating retrieval as independent from application security.

It is particularly relevant to:

* Enterprise RAG
* Secure AI assistants
* Multi-tenant SaaS platforms
* Document intelligence systems
* Enterprise knowledge bases
* AI security
* Access-controlled semantic search

## Future Improvements

* OAuth2 / enterprise identity integration
* More granular document permissions
* RBAC + ABAC combination
* Encryption at rest
* API rate limiting
* Background indexing jobs
* Distributed task queues
* Observability dashboard
* Retrieval evaluation
* Security/leakage benchmark suite
* Production Kubernetes deployment
* Advanced LLM provider support

## License

Add the license that matches how you want to distribute the project.

---

**Built with Python, FastAPI, PostgreSQL, Qdrant, Sentence Transformers, JWT, and Docker.**
