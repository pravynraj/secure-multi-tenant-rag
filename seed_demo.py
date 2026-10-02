from sqlalchemy import select

from app.auth.jwt import hash_password
from app.ingestion.pipeline import index_document
from app.models.db import Document, SessionLocal, User, initialize_database
from app.retrieval.qdrant import ensure_collection, get_qdrant_client


DEMO_USERS = [
    ("alice", "company_a", "hr", ["hr"]),
    ("bob", "company_a", "employee", ["employee"]),
    ("charlie", "company_b", "hr", ["hr"]),
    ("david", "company_b", "employee", ["employee"]),
]

DEMO_DOCUMENTS = [
    ("hr_salary_001", "Company A salary policy", "Company A salary details are confidential.", "company_a"),
    ("hr_salary_002", "Company B salary policy", "Company B salary details are confidential.", "company_b"),
]


def main() -> None:
    initialize_database()
    try:
        ensure_collection()
        with SessionLocal() as db:
            for user_id, tenant_id, password, roles in DEMO_USERS:
                user = db.scalar(select(User).where(User.user_id == user_id))
                if user is None:
                    db.add(
                        User(
                            user_id=user_id,
                            tenant_id=tenant_id,
                            password_hash=hash_password(password),
                            roles=roles,
                        )
                    )
            db.commit()

            for document_id, title, content, tenant_id in DEMO_DOCUMENTS:
                document = db.scalar(select(Document).where(Document.document_id == document_id))
                if document is None:
                    document = Document(
                        document_id=document_id,
                        tenant_id=tenant_id,
                        title=title,
                        content=content,
                        allowed_roles=["hr"],
                        allowed_users=[],
                        classification="confidential",
                        chunk_count=0,
                    )
                    db.add(document)
            db.commit()

            for document_id, _, _, _ in DEMO_DOCUMENTS:
                document = db.scalar(select(Document).where(Document.document_id == document_id))
                if document is None:
                    raise RuntimeError(f"Seed document {document_id} was not persisted")
                chunk_count = index_document(
                    document_id=document.document_id,
                    tenant_id=document.tenant_id,
                    title=document.title,
                    content=document.content,
                    allowed_roles=document.allowed_roles,
                    allowed_users=document.allowed_users,
                    classification=document.classification,
                )
                document.chunk_count = chunk_count
            db.commit()
    finally:
        get_qdrant_client().close()
        get_qdrant_client.cache_clear()
    print("Created demo users and indexed demo documents.")


if __name__ == "__main__":
    main()
