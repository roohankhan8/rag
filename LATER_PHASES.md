# Later Phases: Step-by-Step Guide

This guide expands step 18 from [IMPLEMENTATION.md](./IMPLEMENTATION.md). Complete one phase at a time. Do not start the next phase until the current phase passes its acceptance checks.

## Before every phase

1. Start from a working branch or commit.
2. Run the current backend tests.
3. Run the frontend build.
4. Write the user-visible outcome for the phase.
5. Add the smallest implementation that achieves that outcome.
6. Add one focused test or manual verification.
7. Update `README.md` and `PLAN.md`.

## Phase 2: Better document handling

### Goal

Allow users to upload common business documents and see useful source metadata.

### Steps

1. Add document-extraction dependencies only for formats you will support.
2. Add PDF extraction for text and page numbers.
3. Add DOCX extraction for paragraphs.
4. Change the ingestion result to return chunks with metadata:

   ```python
   {
       "text": "...",
       "page": 2,
       "section": "Leave policy"
   }
   ```

5. Store page and section metadata with every embedding.
6. Update the source response to show page numbers.
7. Validate file extension, MIME type, size, and decoded content.
8. Reject encrypted, empty, and unreadable files with a clear error.
9. Add an upload status message in Vue.

### Acceptance check

Upload a PDF, ask a question about page 2, and confirm the answer displays the correct page as a source.

### Stop condition

Stop when `.txt`, `.md`, and the selected document formats upload safely and source metadata is visible.

### Code starter: document extraction interface

Create `backend/app/extractors.py`:

```python
from pathlib import Path


def extract_text(filename, data):
    extension = Path(filename).suffix.lower()
    if extension in {".txt", ".md"}:
        return [{"text": data.decode("utf-8", errors="replace"), "page": None}]
    raise ValueError("unsupported file type")
```

Keep PDF and DOCX extraction behind this function. The route should not know how each file format is parsed.

## Phase 3: Persistent storage

### Goal

Keep documents, chunks, and embeddings after the backend restarts.

### Steps

1. Choose one database for the first deployment; use SQLite locally.
2. Add tables for `documents` and `chunks`.
3. Store document status as `pending`, `ready`, or `failed`.
4. Store chunk text, metadata, and embedding values.
5. Move the current `MemoryStore` operations behind the same storage methods.
6. Load ready documents when the application starts, or query them on demand.
7. Add a document list endpoint.
8. Add a delete-document endpoint.
9. Add Vue controls for listing and deleting documents.
10. Add a migration mechanism before changing the schema further.

### Acceptance check

Upload a document, restart Flask, and successfully ask a question about it.

### Stop condition

Stop when restart persistence and document deletion work without changing the chat API contract.

### Code starter: SQLAlchemy models

Add `Flask-SQLAlchemy` to `backend/requirements.txt`, then create `backend/app/models.py`:

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ready")
    chunks = db.relationship("Chunk", cascade="all, delete-orphan")


class Chunk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("document.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    embedding = db.Column(db.JSON, nullable=False)
    page = db.Column(db.Integer)
```

Initialize it in the app factory:

```python
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rag.db"
db.init_app(app)
with app.app_context():
    db.create_all()
```

### Complete Phase 3 implementation: SQLite with the standard library

This is the smallest complete persistence upgrade. It avoids adding an ORM and stores embeddings as JSON.

Replace `backend/app/storage.py` with:

```python
import json
import math
import os
import sqlite3
from pathlib import Path


DATABASE = Path(os.environ.get("RAG_DATABASE", "rag.db"))


def connect():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ready',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """)


def add_document(filename, chunks):
    with connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        document = connection.execute(
            "INSERT INTO documents (filename) VALUES (?) RETURNING id",
            (filename,),
        ).fetchone()
        document_id = document["id"]

        connection.executemany(
            """
            INSERT INTO chunks (document_id, chunk_index, text, embedding)
            VALUES (?, ?, ?, ?)
            """,
            [
                (document_id, index, text, json.dumps(embedding))
                for index, (text, embedding) in enumerate(chunks)
            ],
        )
    return document_id


def delete_document(document_id):
    with connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,),
        )
    return cursor.rowcount > 0


def list_documents():
    with connect() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT id, filename, status, created_at FROM documents ORDER BY id DESC"
        )]


def search(query_embedding, limit=4):
    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0

    with connect() as connection:
        rows = connection.execute("""
            SELECT chunks.text, chunks.chunk_index, chunks.embedding,
                   documents.id AS document_id, documents.filename
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            WHERE documents.status = 'ready'
        """).fetchall()

    results = []
    for row in rows:
        result = {
            "document_id": row["document_id"],
            "filename": row["filename"],
            "chunk_index": row["chunk_index"],
            "text": row["text"],
            "score": cosine(query_embedding, json.loads(row["embedding"])),
        }
        results.append(result)
    return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]
```

Update `backend/app/__init__.py`:

```python
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_cors import CORS
from .storage import init_db
from .routes import api


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=2 * 1024 * 1024, TESTING=False)
    if test_config:
        app.config.update(test_config)

    CORS(app)
    init_db()
    app.register_blueprint(api, url_prefix="/api")
    return app


app = create_app()
```

Update the imports and handlers in `backend/app/routes.py`:

```python
import os
from flask import Blueprint, jsonify, request
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

    extension = os.path.splitext(uploaded.filename)[1].lower()
    if extension not in {".txt", ".md"}:
        return jsonify(error="only .txt and .md files are supported"), 400

    text = uploaded.read().decode("utf-8", errors="replace")
    text_chunks = chunk_text(text)
    if not text_chunks:
        return jsonify(error="file is empty"), 400

    embedded_chunks = [(chunk, embed(chunk)) for chunk in text_chunks]
    document_id = add_document(uploaded.filename, embedded_chunks)
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
```

Delete the old `MemoryStore` usage. The database file is created automatically as `backend/rag.db` when Flask starts.

Verify persistence:

```powershell
cd backend
flask --app app run --debug --port 5000
```

Upload a document, stop Flask, start it again, and call:

```powershell
curl http://127.0.0.1:5000/api/documents
```

The uploaded document should still be listed.

## Phase 4: Authentication and user isolation

### Goal

Ensure each user can access only their own documents and conversations.

### Steps

1. Choose session cookies or bearer tokens; use one approach consistently.
2. Add a `users` table with securely hashed passwords if using password login.
3. Add registration, login, logout, and current-user endpoints.
4. Add a `user_id` to documents and conversations.
5. Require authentication on document and chat endpoints.
6. Filter every document query by the authenticated user.
7. Check ownership before reading or deleting a document.
8. Add frontend login state and route protection.
9. Add tests proving user A cannot read user B's document.
10. Add rate limits to login and registration.

### Acceptance check

Create two users, upload separate documents, and verify that neither user can retrieve the other user's content.

### Stop condition

Stop when authentication, ownership checks, and unauthorized-access tests pass.

### Code starter: ownership check

Every document query must include the current user:

```python
from flask import abort
from .models import Document


def get_owned_document(document_id, user_id):
    document = Document.query.filter_by(
        id=document_id,
        user_id=user_id,
    ).first()
    if document is None:
        abort(404)
    return document
```

Do not fetch by document ID first and check ownership afterward in a separate code path.

## Phase 5: RAG quality evaluation

### Goal

Measure and improve retrieval and answer quality instead of tuning by guesswork.

### Steps

1. Create a small evaluation set of questions, expected answers, and expected sources.
2. Add a script that runs each question through retrieval.
3. Record retrieved filenames, chunk indexes, scores, and generated answers.
4. Measure whether the expected source appears in the top results.
5. Add a similarity threshold for rejecting irrelevant results.
6. Tune chunk size and overlap using the evaluation set.
7. Add metadata filtering when users select a document or collection.
8. Require the answer prompt to cite source identifiers.
9. Return a clear “not found” response when retrieval is below the threshold.
10. Re-run the evaluation after every retrieval or prompt change.

### Acceptance check

The evaluation set shows that the expected source is retrieved for the target questions and unrelated questions do not produce confident answers.

### Stop condition

Stop when quality improvements are measured and the system has a documented baseline.

### Code starter: retrieval evaluation

Create `backend/evaluate_retrieval.py`:

```python
from app.rag import embed
from app.storage import store

CASES = [
    {
        "question": "What are the standard working hours?",
        "expected_file": "company-handbook.md",
    },
]


for case in CASES:
    results = store.search(embed(case["question"]), limit=4)
    files = {result["filename"] for result in results}
    passed = case["expected_file"] in files
    print("PASS" if passed else "FAIL", case["question"], files)
```

Run it only against test data and record the result before changing chunking or prompts.

## Phase 6: Conversational history

### Goal

Support follow-up questions in a saved chat conversation.

### Steps

1. Add `conversations` and `messages` tables.
2. Add endpoints to create, list, rename, and delete conversations.
3. Add an endpoint to send a message to a conversation.
4. Store the user question and assistant answer.
5. Use recent conversation messages to rewrite ambiguous follow-up questions.
6. Retrieve document context using the rewritten question.
7. Keep the retrieved context separate from untrusted user conversation text.
8. Add a Vue conversation list and message history.
9. Add new-chat, retry, and copy-answer actions.
10. Limit history sent to the model to control cost and context size.

### Acceptance check

Ask a question, follow up with “What about the second option?”, and verify that the system resolves the reference using the prior message.

### Stop condition

Stop when conversations survive refreshes and follow-up questions use the correct context.

### Code starter: message models

```python
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False, default="New chat")
    messages = db.relationship("Message", cascade="all, delete-orphan")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
```

Keep the first version simple: send only the most recent few messages to the model.

## Phase 7: Streaming and background processing

### Goal

Keep the UI responsive for large documents and slow model responses.

### Steps

1. Measure current upload and answer latency first.
2. Add a background job mechanism only if measured latency requires it.
3. Create document-processing jobs with `pending`, `running`, `ready`, and `failed` states.
4. Return a job or document ID immediately after upload.
5. Add a status endpoint.
6. Poll document status from Vue, or use server-sent events if polling is insufficient.
7. Add retries with a maximum attempt count.
8. Add request timeouts for embedding and generation calls.
9. Stream answer tokens using server-sent events or the provider's streaming API.
10. Allow the user to cancel a long-running answer.

### Acceptance check

Upload a large document without blocking the API request, and observe answer text arriving progressively in the UI.

### Stop condition

Stop when failed jobs are visible, retry safely, and do not create duplicate chunks.

### Code starter: job status endpoint

```python
@api.get("/documents/<int:document_id>/status")
def document_status(document_id):
    document = get_owned_document(document_id, current_user.id)
    return {"id": document.id, "status": document.status}
```

### Code starter: streamed answer response

```python
from flask import Response, stream_with_context


@api.post("/chat/stream")
def stream_chat():
    question = request.json["question"]

    def generate():
        chat = client.chats.create(model=os.environ["AI_CHAT_MODEL"])
        for part in chat.send_message_stream(question):
            if part.text:
                yield part.text

    return Response(stream_with_context(generate()), mimetype="text/plain")
```

Use the provider's streaming API only after the normal answer endpoint is reliable.

## Phase 8: Production readiness

### Goal

Make the application safe and observable enough for real users.

### Steps

1. Move all secrets to deployment-managed environment variables.
2. Disable Flask debug mode in production.
3. Add structured request and error logging.
4. Add health and readiness checks.
5. Add request IDs for tracing failures.
6. Add rate limiting for uploads, chat, and authentication.
7. Validate upload content and enforce storage quotas.
8. Add prompt-injection defenses and treat document text as untrusted input.
9. Add output handling that avoids exposing secrets or private documents.
10. Add database backups and a restore test.
11. Add CI checks for backend tests and frontend builds.
12. Add Docker configuration only when the deployment target requires it.
13. Configure HTTPS, allowed origins, secure cookies, and security headers.
14. Monitor model errors, latency, token usage, and retrieval quality.

### Acceptance check

Deploy to a non-production environment, run smoke tests, verify logs and alerts, restore a backup, and confirm that secrets are not present in source control.

### Stop condition

Stop when the deployment can be monitored, recovered, and updated safely.

### Code starter: production configuration

```python
import os

app.config.update(
    DEBUG=False,
    TESTING=False,
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,
    SECRET_KEY=os.environ["SECRET_KEY"],
)
```

Run Flask behind a production WSGI server:

```bash
pip install gunicorn
gunicorn --workers 2 --bind 0.0.0.0:5000 "app:create_app()"
```

Never enable debug mode or hardcode production secrets.

## Phase 9: Advanced AI features

Implement these only when a measured product need exists.

### Possible order

1. Multiple knowledge bases and collections.
2. Team sharing and document permissions.
3. Hybrid keyword and vector search.
4. Reranking and query expansion.
5. Structured data extraction.
6. Document summaries and generated questions.
7. Tool use and agent workflows.
8. Provider and model comparison.

For every advanced feature:

1. Define one concrete user outcome.
2. Add an evaluation case before implementation.
3. Implement the smallest version.
4. Measure quality, latency, and cost.
5. Keep the feature only if it improves the target outcome.

### Code starter: metadata filtering

Add a filter before ranking results:

```python
def search(query_embedding, limit=4, document_id=None):
    candidates = self.items
    if document_id is not None:
        candidates = [item for item in candidates if item["document_id"] == document_id]
    return rank_by_similarity(candidates, query_embedding, limit)
```

Only add filtering when the UI exposes a real document or collection selection.

## Recommended stopping rule

The project is complete when the current users can reliably upload documents, find grounded answers, manage their data, and recover from failures. More AI features are optional; reliability and evidence should come first.
