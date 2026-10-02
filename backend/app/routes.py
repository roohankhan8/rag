import os
from flask import Blueprint, jsonify, request
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

    extension = os.path.splitext(uploaded.filename)[1].lower()
    if extension not in {".txt", ".md"}:
        return jsonify(error="only .txt and .md files are supported"), 400

    text = uploaded.read().decode("utf-8", errors="replace")
    chunks = chunk_text(text)
    if not chunks:
        return jsonify(error="file is empty"), 400

    for index, chunk in enumerate(chunks):
        store.add(uploaded.filename, uploaded.filename, index, chunk, embed(chunk))

    return jsonify(document_id=uploaded.filename, chunks=len(chunks)), 201


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

