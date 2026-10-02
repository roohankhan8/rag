import os
from flask import Blueprint, jsonify, request, session
from werkzeug.utils import secure_filename
from .extractors import extract_document
from .rag import answer_question, chunk_text, embed
from .storage import add_document, delete_document, list_documents, search
from .models import User, db

api = Blueprint("api", __name__)

def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None

def require_user():
    user = current_user()
    return user if user else (jsonify(error="authentication required"), 401)

@api.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    email, password = str(data.get("email", "")).strip().lower(), str(data.get("password", ""))
    if not email or len(password) < 8: return jsonify(error="email and a password of at least 8 characters are required"), 400
    if User.query.filter_by(email=email).first(): return jsonify(error="email is already registered"), 409
    user = User(email=email); user.set_password(password); db.session.add(user); db.session.commit(); session["user_id"] = user.id
    return jsonify(email=user.email), 201

@api.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    user = User.query.filter_by(email=str(data.get("email", "")).strip().lower()).first()
    if user is None or not user.check_password(str(data.get("password", ""))): return jsonify(error="invalid email or password"), 401
    session["user_id"] = user.id
    return jsonify(email=user.email)

@api.post("/auth/logout")
def logout(): session.clear(); return "", 204

@api.get("/auth/me")
def me():
    user = current_user()
    return (jsonify(email=user.email), 200) if user else (jsonify(error="authentication required"), 401)


@api.get("/health")
def health():
    return jsonify(status="ok")


@api.post("/documents")
def upload_document():
    user = require_user()
    if not isinstance(user, User): return user
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
    document_id = add_document(filename, embedded_chunks, user.id)
    return jsonify(document_id=document_id, filename=uploaded.filename,
                   chunks=len(text_chunks)), 201


@api.get("/documents")
def documents():
    user = require_user()
    if not isinstance(user, User): return user
    return jsonify(documents=list_documents(user.id))


@api.delete("/documents/<int:document_id>")
def remove_document(document_id):
    user = require_user()
    if not isinstance(user, User): return user
    if not delete_document(document_id, user.id):
        return jsonify(error="document not found"), 404
    return "", 204


@api.post("/chat")
def chat():
    user = require_user()
    if not isinstance(user, User): return user
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    if not question:
        return jsonify(error="question is required"), 400

    sources = search(embed(question), user.id)
    if not sources:
        return jsonify(answer="I could not find that in your documents.", sources=[])
    return jsonify(answer=answer_question(question, sources), sources=sources)
