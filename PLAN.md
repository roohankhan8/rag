# Flask + Vue RAG Project Plan

## Project goal

Build an AI application with a Flask backend and Vue frontend that lets users upload documents, ask questions, and receive answers grounded in retrieved document content.

The project will grow in stages. Each stage should remain runnable before the next one begins.

## Phase 1: Minimal RAG MVP

### Backend

- Create a Flask application in `backend/`.
- Add `GET /api/health`.
- Add `POST /api/documents` for text and Markdown uploads.
- Split documents into manageable chunks.
- Generate embeddings through the selected AI provider.
- Store embeddings in the simplest suitable local vector store.
- Add `POST /api/chat` for user questions.
- Retrieve the most relevant chunks.
- Generate an answer using the retrieved context.
- Return the answer and source excerpts.
- Add CORS and environment-variable configuration.

### Frontend

- Create a Vue application in `frontend/`.
- Add a document upload form.
- Add a basic chat interface.
- Show loading and error states.
- Display retrieved source excerpts with each answer.

### Validation

- Test the health endpoint.
- Test document upload.
- Test retrieval and answer generation.
- Run one end-to-end upload → retrieve → answer smoke test.

### Explicitly deferred

- Authentication
- Persistent database storage
- Conversation history
- Background processing
- Streaming responses
- Multiple vector-store providers
- Production deployment

## Phase 2: Better document handling

- Support PDF and DOCX files.
- Extract document metadata such as filename, title, and page number.
- Improve chunking for headings, paragraphs, and tables.
- Reject unsupported or unsafe files.
- Add file size and content validation.
- Show document processing status in the UI.

Add this phase when users need to work with real-world documents beyond plain text and Markdown.

## Phase 3: Persistent storage

- Add a relational database for users, documents, and conversations.
- Persist document metadata and processing state.
- Persist chat sessions and messages.
- Persist vector-store identifiers or embeddings as needed.
- Add migrations and a local development database.

Add this phase when data must survive application restarts or users need saved conversations.

## Phase 4: Authentication and user isolation

- Add user registration and login.
- Protect document and chat endpoints.
- Scope documents and conversations to the authenticated user.
- Add logout and session/token handling.
- Add authorization checks for every document operation.

Add this phase before exposing the application to multiple users or the public internet.

## Phase 5: Improved RAG quality

- Add configurable retrieval limits.
- Add similarity thresholds.
- Add metadata filtering.
- Add reranking when retrieval quality requires it.
- Improve prompts for citations and uncertainty.
- Return a clear response when the documents do not contain the answer.
- Add a small evaluation dataset with expected answers and sources.

Add this phase when the MVP works but answers are incomplete, irrelevant, or poorly grounded.

## Phase 6: Conversational experience

- Add conversation history to the frontend.
- Rewrite follow-up questions using conversation context.
- Add new-chat and rename-chat actions.
- Allow users to inspect citations and source documents.
- Add copy and retry actions for answers.

Add this phase when users need multi-turn conversations instead of isolated questions.

## Phase 7: Streaming and background processing

- Process large uploads asynchronously.
- Add job status and retry handling.
- Stream generated answers to the Vue interface.
- Add cancellation for long-running requests.
- Add request timeouts and provider failure handling.

Add this phase when document processing or answer generation becomes slow enough to affect usability.

## Phase 8: Production readiness

- Add structured logging.
- Add application metrics and error tracking.
- Add rate limiting.
- Add secret management.
- Add input, output, and prompt-injection protections.
- Add automated tests for key API and RAG behavior.
- Add Docker configuration.
- Add CI checks.
- Deploy the Flask API, Vue frontend, database, and vector store.
- Add backups and recovery procedures.

Add this phase before production use or handling sensitive data.

## Phase 9: Advanced AI features

Potential later features:

- Multiple knowledge bases.
- Team sharing and permissions.
- Hybrid keyword plus vector search.
- Query expansion.
- Agent-style tool use.
- Structured data extraction.
- Document summarization.
- Question generation.
- Feedback-based answer improvement.
- Model and provider comparison.

Only add these features after measuring a real user need. Avoid building an agent framework or provider abstraction without a concrete use case.

## Stop conditions

Stop implementation after Phase 1 when the following work reliably:

1. A user uploads a document.
2. The backend chunks and indexes it.
3. A user asks a question.
4. Relevant chunks are retrieved.
5. The answer is generated from those chunks.
6. The frontend shows the answer and sources.

Do not begin a later phase until the current phase is runnable and its acceptance checks pass.

## Recommended initial structure

```text
.
├── PLAN.md
├── README.md
├── .env.example
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── rag.py
│   │   └── storage.py
│   ├── tests/
│   └── requirements.txt
└── frontend/
    ├── src/
    ├── package.json
    └── vite.config.js
```

This structure is intentionally small. Split modules further only when the code becomes difficult to navigate.
