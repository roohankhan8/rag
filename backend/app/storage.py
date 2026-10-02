import os

from .models import Chunk, Document, db


def init_db():
    if db.engine.dialect.name == "postgresql":
        db.session.execute(db.text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.session.commit()
    db.create_all()
    # Keep the local Phase 3 database bootable after adding ownership.
    inspector = db.inspect(db.engine)
    if "documents" in inspector.get_table_names() and not any(
        column["name"] == "user_id" for column in inspector.get_columns("documents")
    ):
        db.session.execute(db.text("ALTER TABLE documents ADD COLUMN user_id INTEGER"))
        db.session.commit()


def add_document(filename, chunks, user_id):
    document = Document(filename=filename, status="ready", user_id=user_id)
    db.session.add(document)
    db.session.flush()
    for index, chunk in enumerate(chunks):
        db.session.add(Chunk(
            document_id=document.id,
            chunk_index=index,
            text=chunk["text"],
            embedding=chunk["embedding"],
            page=chunk.get("page"),
        ))
    db.session.commit()
    return document.id


def delete_document(document_id, user_id):
    document = Document.query.filter_by(id=document_id, user_id=user_id).first()
    if document is None:
        return False
    db.session.delete(document)
    db.session.commit()
    return True


def list_documents(user_id):
    return [{
        "id": item.id,
        "filename": item.filename,
        "status": item.status,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    } for item in Document.query.filter_by(user_id=user_id).order_by(Document.id.desc()).all()]


def cosine_similarity(a, b):
    # Retained for the unit test and local fallback; Postgres uses pgvector below.
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0


def search(query_embedding, user_id, limit=None, threshold=None):
    limit = limit or int(os.getenv("RAG_RETRIEVAL_LIMIT", "4"))
    threshold = threshold if threshold is not None else float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.35"))

    if db.engine.dialect.name != "postgresql":
        results = []
        for chunk in Chunk.query.join(Document).filter(Document.status == "ready", Document.user_id == user_id):
            results.append({
                "document_id": chunk.document_id, "filename": chunk.document.filename,
                "chunk_index": chunk.chunk_index, "text": chunk.text, "page": chunk.page,
                "score": cosine_similarity(query_embedding, chunk.embedding),
            })
        return [item for item in sorted(results, key=lambda item: item["score"], reverse=True)
                if item["score"] >= threshold][:limit]

    distance = Chunk.embedding.cosine_distance(query_embedding)
    rows = (db.session.query(Chunk, distance.label("distance"))
            .join(Document)
            .filter(Document.status == "ready", Document.user_id == user_id,
                    distance <= 1 - threshold)
            .order_by(distance)
            .limit(limit)
            .all())
    return [{
        "document_id": chunk.document_id,
        "filename": chunk.document.filename,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "page": chunk.page,
        "score": 1 - distance_value,
    } for chunk, distance_value in rows]
