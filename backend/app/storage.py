import math

from .models import Chunk, Document, db


def init_db():
    db.create_all()


def add_document(filename, chunks):
    document = Document(filename=filename, status="ready")
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


def delete_document(document_id):
    document = db.session.get(Document, document_id)
    if document is None:
        return False
    db.session.delete(document)
    db.session.commit()
    return True


def list_documents():
    return [{
        "id": item.id,
        "filename": item.filename,
        "status": item.status,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    } for item in Document.query.order_by(Document.id.desc()).all()]


def search(query_embedding, limit=4):
    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0

    results = []
    for chunk in Chunk.query.join(Document).filter(Document.status == "ready"):
        results.append({
            "document_id": chunk.document_id,
            "filename": chunk.document.filename,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "page": chunk.page,
            "score": cosine(query_embedding, chunk.embedding),
        })
    return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]
