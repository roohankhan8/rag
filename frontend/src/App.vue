<script setup>
import { computed, onMounted, ref } from "vue";

const file = ref(null);
const question = ref("");
const answer = ref("");
const sources = ref([]);
const documents = ref([]);
const status = ref("");
const error = ref("");
const busy = ref(false);
const uploadInput = ref(null);
const toast = ref(null);
let toastTimer;

const hasAnswer = computed(() => answer.value || sources.value.length);

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

function showToast(message, type = "error") {
  toast.value = { message, type };
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.value = null; }, 4500);
}

function selectFile(event) {
  file.value = event.target.files?.[0] || null;
  status.value = file.value ? `${file.value.name} is ready to upload.` : "";
  error.value = "";
}

async function loadDocuments() {
  try {
    const data = await readResponse(await fetch("/api/documents"));
    documents.value = data.documents || [];
  } catch {
    // The document list is supplementary; chat remains usable if it fails.
  }
}

async function upload() {
  if (!file.value) return;
  busy.value = true;
  error.value = "";
  status.value = "Indexing document…";
  const body = new FormData();
  body.append("file", file.value);
  try {
    const data = await readResponse(await fetch("/api/documents", { method: "POST", body }));
    status.value = `${data.filename} indexed · ${data.chunks} chunks`;
    file.value = null;
    if (uploadInput.value) uploadInput.value.value = "";
    await loadDocuments();
  } catch (requestError) {
    error.value = requestError.message;
    showToast(requestError.message);
    status.value = "";
  } finally {
    busy.value = false;
  }
}

async function ask() {
  if (!question.value.trim() || busy.value) return;
  busy.value = true;
  error.value = "";
  answer.value = "";
  sources.value = [];
  try {
    const data = await readResponse(await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question.value }),
    }));
    answer.value = data.answer;
    sources.value = data.sources || [];
  } catch (requestError) {
    error.value = requestError.message;
    showToast(requestError.message);
  } finally {
    busy.value = false;
  }
}

function newQuestion() {
  question.value = "";
  answer.value = "";
  sources.value = [];
  error.value = "";
}

onMounted(loadDocuments);
</script>

<template>
  <div class="app-shell">
    <div v-if="toast" class="toast" :class="`toast-${toast.type}`" role="alert" aria-live="assertive">
      <span class="toast-icon">!</span><span>{{ toast.message }}</span><button class="toast-close" aria-label="Dismiss notification" @click="toast = null">×</button>
    </div>
    <aside class="sidebar">
      <div class="brand"><span class="brand-mark">✦</span><span>contextual</span></div>
      <div class="workspace-label">WORKSPACE</div>
      <nav class="nav-list" aria-label="Main navigation">
        <a class="nav-item active" href="#workspace"><span class="icon">▦</span> Knowledge workspace</a>
        <a class="nav-item" href="#documents"><span class="icon">▤</span> Documents <span class="nav-count">{{ documents.length }}</span></a>
      </nav>
      <div class="sidebar-bottom">
        <div class="tip-card"><span class="tip-icon">✧</span><div><strong>Grounded answers</strong><p>Upload context first, then ask anything about it.</p></div></div>
        <div class="user-row"><span class="avatar">R</span><div><strong>Researcher</strong><small>Personal workspace</small></div><span class="dots">•••</span></div>
      </div>
    </aside>

    <main id="workspace" class="main-content">
      <header class="topbar"><div><span class="eyebrow">KNOWLEDGE WORKSPACE</span><h1>Ask your documents</h1></div><button class="ghost-button" @click="newQuestion"><span>＋</span> New question</button></header>

      <div class="workspace-grid">
        <section class="conversation-panel" aria-labelledby="question-heading">
          <div v-if="!hasAnswer" class="empty-state">
            <div class="orb"><span>✦</span></div>
            <p class="eyebrow">YOUR AI RESEARCH ASSISTANT</p>
            <h2 id="question-heading">What would you like<br /><em>to understand?</em></h2>
            <p class="empty-copy">Ask a question about your uploaded documents. Answers are grounded in your sources.</p>
          </div>
          <div v-else class="answer-area">
            <div class="question-bubble"><span class="mini-avatar">R</span><p>{{ question }}</p></div>
            <div class="answer-card"><div class="answer-label"><span class="assistant-mark">✦</span> CONTEXTUAL <span class="answer-time">Just now</span></div><p class="answer-text">{{ answer }}</p><div v-if="sources.length" class="source-chips"><span v-for="source in sources" :key="`${source.filename}-${source.chunk_index}`" class="source-chip">↗ {{ source.filename }}<span v-if="source.page"> · p. {{ source.page }}</span></span></div></div>
          </div>

          <form class="composer" @submit.prevent="ask">
            <label class="sr-only" for="question">Ask a question</label>
            <textarea id="question" v-model="question" rows="2" placeholder="Ask anything about your documents…" :disabled="busy" @keydown.enter.exact.prevent="ask"></textarea>
            <div class="composer-footer"><span class="composer-hint">Press Enter to ask <kbd>↵</kbd></span><button class="send-button" type="submit" :disabled="busy || !question.trim()" :aria-label="busy ? 'Asking question' : 'Ask question'"><span v-if="busy" class="spinner"></span><span v-else>↑</span></button></div>
          </form>
          <p class="privacy-note">✦ Your answers are generated from the documents in this workspace.</p>
        </section>

        <aside class="context-panel" id="documents">
          <div class="panel-heading"><div><span class="eyebrow">YOUR SOURCES</span><h3>Document library</h3></div><span class="library-count">{{ documents.length }}</span></div>
          <div class="upload-zone" @click="uploadInput?.click()"><input ref="uploadInput" class="file-input" type="file" accept=".txt,.md,.pdf,.docx" @change="selectFile" /><div class="upload-icon">↑</div><strong>{{ file ? file.name : 'Drop a document here' }}</strong><p>{{ file ? 'Ready to index' : 'PDF, DOCX, MD or TXT · 2 MB max' }}</p></div>
          <button class="upload-button" :disabled="busy || !file" @click="upload"><span>＋</span> {{ busy ? 'Indexing…' : 'Add document' }}</button>
          <p v-if="status" class="status-message">✓ {{ status }}</p><p v-if="error" class="error-message">{{ error }}</p>
          <div class="document-list"><div v-if="!documents.length" class="no-documents"><span>◌</span><p>No documents yet.<br />Add one to get started.</p></div><div v-for="document in documents" :key="document.id" class="document-row"><span class="file-icon">▤</span><div><strong>{{ document.filename }}</strong><small>{{ document.status }} · ready to search</small></div><span class="document-menu">···</span></div></div>
          <div class="context-footer"><span class="pulse-dot"></span><span>Search is ready</span></div>
        </aside>
      </div>
    </main>
  </div>
</template>
