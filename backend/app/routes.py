import os
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from .extractors import extract_document
from .rag import answer_question, chunk_text, embed
from .storage import add_document, delete_document, list_documents, search

api = Blueprint("api", __name__)


@api.get("/health")
def health():
    return jsonify(status="ok")


@api.post("/documents")
def upload_document():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify(error="file is required"), 400

    filename = secure_filename(uploaded.filename)
    extension = os.path.splitext(filename)[1].lower()
    if extension not in {".txt", ".md", ".pdf", ".docx"}:
        return jsonify(error="supported files are .txt, .md, .pdf, and .docx"), 400

    try:
        sections = extract_document(filename, uploaded.read())
    except Exception as error:
        return jsonify(error=f"could not read document: {error}"), 400

    text_chunks = []
    for section in sections:
        for text in chunk_text(section["text"]):
            text_chunks.append({"text": text, "page": section["page"]})
    if not text_chunks:
        return jsonify(error="file is empty"), 400

    embedded_chunks = [
        {"text": chunk["text"], "page": chunk["page"], "embedding": embed(chunk["text"])}
        for chunk in text_chunks
    ]
    document_id = add_document(filename, embedded_chunks)
    return jsonify(document_id=document_id, filename=uploaded.filename,
                   chunks=len(text_chunks)), 201


@api.get("/documents")
def documents():
    return jsonify(documents=list_documents())


@api.delete("/documents/<int:document_id>")
def remove_document(document_id):
    if not delete_document(document_id):
        return jsonify(error="document not found"), 404
    return "", 204


@api.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    if not question:
        return jsonify(error="question is required"), 400

    sources = search(embed(question))
    if not sources:
        return jsonify(answer="I do not know based on the uploaded documents.", sources=[])
    return jsonify(answer=answer_question(question, sources), sources=sources)
