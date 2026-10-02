# Step-by-Step Implementation Guide

This guide implements Phase 1 from [PLAN.md](./PLAN.md): upload a document, index it, ask a question, and display a grounded answer with sources.

## 1. Install prerequisites

Install:

- Python 3.11 or newer
- Node.js 20 or newer
- Git
- An API key for the chosen AI provider

Verify the installations:

```bash
python --version
node --version
npm --version
git --version
```

## 2. Create the project folders

From the repository root:

```bash
mkdir backend frontend
```

## 3. Set up the Flask backend

Create and activate a virtual environment:

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

Create `backend/requirements.txt` with the Flask framework, CORS support, environment-variable loading, AI SDK, and a local vector store.

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create this initial backend layout:

```text
backend/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── rag.py
│   └── storage.py
├── tests/
├── .env
└── requirements.txt
```

## 3.1 Add backend dependencies

Create `backend/requirements.txt`:

```txt
Flask
flask-cors
python-dotenv
openai
pytest
```

## 3.2 Add the application factory

Create `backend/app/__init__.py`:

```python
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_cors import CORS
from .routes import api


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        TESTING=False,
    )

    if test_config:
        app.config.update(test_config)

    CORS(app)
    app.register_blueprint(api, url_prefix="/api")
    return app


app = create_app()
```

## 3.3 Add in-memory vector storage

Create `backend/app/storage.py`:

```python
import math


class MemoryStore:
    def __init__(self):
        self.items = []

    def add(self, document_id, filename, chunk_index, text, embedding):
        self.items.append({
            "document_id": document_id,
            "filename": filename,
            "chunk_index": chunk_index,
            "text": text,
            "embedding": embedding,
        })

    def search(self, query_embedding, limit=4):
        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0

        matches = []
        for item in self.items:
            result = {key: value for key, value in item.items() if key != "embedding"}
            result["score"] = cosine(query_embedding, item["embedding"])
            matches.append(result)

        return sorted(matches, key=lambda item: item["score"], reverse=True)[:limit]


store = MemoryStore()
```

## 3.4 Add RAG helpers

Create `backend/app/rag.py`:

```python
import os
from openai import OpenAI


client = OpenAI(api_key=os.environ.get("AI_API_KEY"))


def chunk_text(text, size=800, overlap=100):
    text = " ".join(text.split())
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def embed(text):
    response = client.embeddings.create(
        model=os.environ["AI_EMBEDDING_MODEL"],
        input=text,
    )
    return response.data[0].embedding


def answer_question(question, sources):
    context = "\n\n".join(
        f"[{source['filename']} #{source['chunk_index']}] {source['text']}"
        for source in sources
    )
    prompt = (
        "Answer using only the context below. If the answer is not in the "
        "context, say you do not know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    response = client.chat.completions.create(
        model=os.environ["AI_CHAT_MODEL"],
        messages=[
            {"role": "system", "content": "You answer questions from supplied documents."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content
```

## 3.5 Add API routes

Create `backend/app/routes.py`:

```python
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
```

The API now has these endpoints:

```text
GET  /api/health
POST /api/documents   multipart form field: file
POST /api/chat        JSON body: {"question": "..."}
```

## 4. Configure environment variables

Create `backend/.env`:

```env
AI_API_KEY=replace-with-your-key
AI_CHAT_MODEL=replace-with-your-chat-model
AI_EMBEDDING_MODEL=replace-with-your-embedding-model
FLASK_PORT=5000
```

Do not commit `.env`. Add it to `.gitignore` and commit only `.env.example`.

## 5. Create the Flask application

In `app/__init__.py`:

1. Create the Flask app.
2. Load environment variables.
3. Enable CORS for the Vue development server.
4. Register the API routes.
5. Initialize the local document/vector storage.

Keep application creation in a factory function so tests can create an isolated app.

## 6. Add the health endpoint

In `app/routes.py`, add:

```text
GET /api/health
```

Return JSON similar to:

```json
{"status": "ok"}
```

Run the backend and verify it:

```bash
flask --app app run --debug --port 5000
```

In another terminal:

```bash
curl http://127.0.0.1:5000/api/health
```

## 7. Implement document ingestion

In `app/routes.py`, add:

```text
POST /api/documents
```

The endpoint should:

1. Read a multipart file upload.
2. Reject missing, empty, oversized, and unsupported files.
3. Read UTF-8 text for the first MVP.
4. Split text into chunks with a small overlap.
5. Generate an embedding for each chunk.
6. Store each chunk, embedding, filename, and chunk index.
7. Return the document identifier and chunk count.

Keep chunking in `app/rag.py` and storage in `app/storage.py` so route handlers only coordinate the flow.

Example response:

```json
{
  "document_id": "example.txt",
  "chunks": 4
}
```

## 8. Implement local vector search

Start with the simplest storage that works locally.

The storage layer must support:

```text
add(document_id, filename, chunk_index, text, embedding)
search(query_embedding, limit)
```

For a small MVP, an in-memory list and cosine similarity are enough. Persisted vector storage can be added in Phase 3.

Implement cosine similarity carefully:

- Return no results when no documents exist.
- Ignore zero-length vectors.
- Sort results by descending similarity.
- Return the top few chunks.

## 9. Implement question answering

In `app/routes.py`, add:

```text
POST /api/chat
```

Accept:

```json
{"question": "What is this document about?"}
```

The request flow is:

1. Validate the question.
2. Generate its embedding.
3. Search for the most relevant chunks.
4. Build a prompt containing only those chunks.
5. Ask the chat model to answer from the supplied context.
6. Tell the model to say when the answer is not present.
7. Return the answer and source excerpts.

Example response:

```json
{
  "answer": "...",
  "sources": [
    {
      "filename": "example.txt",
      "chunk_index": 0,
      "text": "...",
      "score": 0.91
    }
  ]
}
```

Never send the entire document to the model when retrieved chunks are available.

## 10. Add backend tests

Create a small test suite covering:

1. `GET /api/health` returns HTTP 200.
2. Missing document uploads return a client error.
3. A valid text document is chunked and stored.
4. Search returns the most relevant chunk.
5. An empty question is rejected.

Mock the AI client in unit tests. Do not spend API credits during normal test runs.

Run the tests:

```bash
pytest
```

## 11. Create the Vue frontend

From the repository root, in a second terminal:

```bash
npm create vite@latest frontend -- --template vue
cd frontend
npm install
npm run dev
```

Use the existing Vue/Vite structure. Do not add a UI framework for the first version.

## 12. Build the upload interface

Create a simple upload component that:

1. Accepts `.txt` and `.md` files.
2. Sends them to `POST http://127.0.0.1:5000/api/documents`.
3. Shows upload progress or a loading state.
4. Shows the indexed chunk count.
5. Displays API errors clearly.

Use `FormData` for the upload request.

Replace `frontend/src/App.vue` with:

```vue
<script setup>
import { ref } from 'vue'

const file = ref(null)
const question = ref('')
const answer = ref('')
const sources = ref([])
const message = ref('')
const busy = ref(false)

function selectFile(event) {
  file.value = event.target.files[0]
}

async function upload() {
  if (!file.value) return
  busy.value = true
  message.value = ''
  const body = new FormData()
  body.append('file', file.value)
  try {
    const response = await fetch('/api/documents', { method: 'POST', body })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || 'Upload failed')
    message.value = `Indexed ${data.chunks} chunks from ${data.document_id}.`
  } catch (error) {
    message.value = error.message
  } finally {
    busy.value = false
  }
}

async function ask() {
  if (!question.value.trim()) return
  busy.value = true
  answer.value = ''
  sources.value = []
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question.value }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || 'Question failed')
    answer.value = data.answer
    sources.value = data.sources
  } catch (error) {
    answer.value = error.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main>
    <h1>Document Q&A</h1>

    <section>
      <h2>Upload a document</h2>
      <input type="file" accept=".txt,.md" @change="selectFile" />
      <button :disabled="busy || !file" @click="upload">Upload</button>
      <p>{{ message }}</p>
    </section>

    <section>
      <h2>Ask a question</h2>
      <form @submit.prevent="ask">
        <input v-model="question" placeholder="Ask about the document" />
        <button :disabled="busy">Ask</button>
      </form>
      <p v-if="answer"><strong>Answer:</strong> {{ answer }}</p>
      <h3 v-if="sources.length">Sources</h3>
      <ul>
        <li v-for="source in sources" :key="`${source.filename}-${source.chunk_index}`">
          <strong>{{ source.filename }}</strong> — {{ source.text }}
        </li>
      </ul>
    </section>
  </main>
</template>

<style>
body { font-family: system-ui, sans-serif; margin: 0; }
main { max-width: 760px; margin: 40px auto; padding: 0 20px; }
section { border: 1px solid #ddd; border-radius: 8px; margin: 20px 0; padding: 20px; }
input { margin-right: 8px; padding: 8px; }
button { padding: 8px 14px; }
li { margin: 10px 0; }
</style>
```

## 13. Build the chat interface

Create a chat component that:

1. Contains a question input and submit button.
2. Sends JSON to `POST http://127.0.0.1:5000/api/chat`.
3. Disables submission while waiting.
4. Shows the returned answer.
5. Lists source filenames, excerpts, and similarity scores.
6. Handles empty questions and failed requests.

Keep state local to the page until conversation persistence is required.

## 14. Connect frontend and backend

Use one of these approaches:

- Configure the Vite development proxy to forward `/api` to Flask.
- Or keep the Flask URL in a frontend environment variable.

The Vite proxy is the smallest local-development setup. Use it so frontend code can call `/api/health`, `/api/documents`, and `/api/chat` without hardcoded hostnames.

Add the proxy to `frontend/vite.config.js`:

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
    },
  },
})
```

If Vite generated a different config, keep its existing plugin configuration and add only the `server.proxy` block.

## 14.1 Add backend tests

Create `backend/tests/test_api.py`:

```python
from app import create_app


def test_health():
    client = create_app({"TESTING": True}).test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_upload_requires_file():
    client = create_app({"TESTING": True}).test_client()
    response = client.post("/api/documents")
    assert response.status_code == 400


def test_chat_requires_question():
    client = create_app({"TESTING": True}).test_client()
    response = client.post("/api/chat", json={})
    assert response.status_code == 400
```

The upload and chat tests that call the AI provider should mock `embed` and `answer_question`; do not make paid API calls from tests.

## 15. Run the complete MVP

Start Flask:

```bash
cd backend
.\.venv\Scripts\Activate.ps1
flask --app app run --debug --port 5000
```

Start Vue in another terminal:

```bash
cd frontend
npm run dev
```

Then verify the full flow:

1. Open the Vue URL shown by Vite.
2. Upload a short `.txt` or `.md` document.
3. Confirm that indexing succeeds.
4. Ask a question answered by the document.
5. Confirm that sources are displayed.
6. Ask an unrelated question and confirm the system does not invent an answer.

## 16. Add project documentation

Update `README.md` with:

- Project purpose
- Required software
- Backend setup
- Frontend setup
- Environment variables
- Test commands
- Local run commands
- Known MVP limitations

## 17. Commit the working MVP

Before committing:

```bash
git status
pytest
npm run build
```

Confirm that secrets and generated folders are ignored. Then create a focused commit:

```bash
git add PLAN.md IMPLEMENTATION.md README.md backend frontend .gitignore .env.example
git commit -m "Build Flask Vue RAG MVP"
```

## 18. Continue with later phases

Only continue after the Phase 1 flow works.

Use this order:

1. Better document handling
2. Persistent storage
3. Authentication and user isolation
4. RAG quality evaluation
5. Conversational history
6. Streaming and background processing
7. Production readiness
8. Advanced AI features

For each phase:

1. Define the user-visible acceptance criteria.
2. Implement the smallest complete slice.
3. Add one focused validation check.
4. Update `PLAN.md` and `README.md`.
5. Stop when the acceptance criteria pass.

Do not add abstractions for future phases until the current phase needs them.
