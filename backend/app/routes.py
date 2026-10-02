import os
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from .extractors import extract_document
from .rag import answer_question, chunk_text, embed
from .storage import store

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
    allowed = {".txt", ".md", ".pdf", ".docx"}
    if extension not in allowed:
        return jsonify(error="supported files are .txt, .md, .pdf, and .docx"), 400

    try:
        sections = extract_document(filename, uploaded.read())
    except (ValueError, Exception) as error:
        return jsonify(error=f"could not read document: {error}"), 400

    chunks = []
    for section in sections:
        for chunk in chunk_text(section["text"]):
            chunks.append({"text": chunk, "page": section["page"]})

    if not chunks:
        return jsonify(error="file is empty"), 400

    for index, chunk in enumerate(chunks):
        store.add(filename, filename, index, chunk["text"], embed(chunk["text"]), chunk["page"])

    return jsonify(document_id=filename, chunks=len(chunks)), 201


@api.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    if not question:
        return jsonify(error="question is required"), 400

    sources = store.search(embed(question))
    if not sources:
        return jsonify(answer="I do not know based on the uploaded documents.", sources=[])

    return jsonify(answer=answer_question(question, sources), sources=sources)

