# Flask + Vue RAG Application

A small retrieval-augmented generation application with a Flask API and Vue frontend.

The MVP supports:

- Uploading `.txt` and `.md` documents
- Chunking and embedding document text
- In-memory vector similarity search
- Asking questions about uploaded documents
- Returning answers with source excerpts

## Requirements

- Python 3.11+
- Node.js 20+
- A Google Gemini API key

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GEMINI_API_KEY=your-api-key
AI_CHAT_MODEL=gemini-2.5-flash
AI_EMBEDDING_MODEL=gemini-embedding-001
FLASK_PORT=5000
```

Start Flask:

```powershell
flask --app app run --debug --port 5000
```

Verify the API:

```powershell
curl http://127.0.0.1:5000/api/health
```

Expected response:

```json
{"status":"ok"}
```

## Frontend setup

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite.

The Vite proxy forwards `/api` requests to Flask at `http://127.0.0.1:5000`.

## Test the application

1. Open the Vue application.
2. Upload one of the files in `sample_documents/`.
3. Ask a question answered by that document.
4. Confirm that the answer includes source excerpts.
5. Ask a question unrelated to the document and confirm the application states that it does not know.

Sample documents:

- `sample_documents/company-handbook.md`
- `sample_documents/product-guide.md`
- `sample_documents/python-basics.md`

## Run backend tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

## Build the frontend

```powershell
cd frontend
npm run build
```

## API endpoints

### Health

```text
GET /api/health
```

### Upload document

```text
POST /api/documents
```

Send a multipart form field named `file`.

### Ask a question

```text
POST /api/chat
```

Request body:

```json
{"question":"What are the standard working hours?"}
```

## MVP limitations

- Documents are stored only in memory and disappear when Flask restarts.
- Only `.txt` and `.md` files are supported.
- There is no authentication or user isolation.
- Chat history is not persisted.
- The application uses synchronous document processing.
- API usage is subject to Gemini free-tier limits.

See [PLAN.md](./PLAN.md) for the later development phases and [IMPLEMENTATION.md](./IMPLEMENTATION.md) for the full implementation guide.
