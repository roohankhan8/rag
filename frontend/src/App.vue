<script setup>
import { computed, onMounted, ref } from "vue";
const activeTab = ref("chat"),
  file = ref(null),
  question = ref(""),
  answer = ref(""),
  sources = ref([]),
  documents = ref([]),
  status = ref(""),
  error = ref(""),
  busy = ref(false),
  uploadInput = ref(null),
  toast = ref(null),
  authenticated = ref(false),
  authMode = ref("login"),
  email = ref(""),
  password = ref(""),
  authError = ref("");
const hasAnswer = computed(() => answer.value || sources.value.length);
async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Something went wrong");
  return data;
}
function showToast(message) {
  toast.value = message;
  setTimeout(() => (toast.value = null), 4500);
}
function selectFile(e) {
  file.value = e.target.files?.[0] || null;
  status.value = file.value ? `${file.value.name} is ready to upload.` : "";
  error.value = "";
}
async function loadDocuments() {
  try {
    documents.value = (await readResponse(await fetch("/api/documents"))).documents || [];
  } catch {}
}
async function authenticate() {
  authError.value = "";
  try {
    await readResponse(
      await fetch(`/api/auth/${authMode.value}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.value, password: password.value }),
      })
    );
    authenticated.value = true;
    loadDocuments();
  } catch (e) {
    authError.value = e.message;
  }
}
async function upload() {
  if (!file.value) return;
  busy.value = true;
  const body = new FormData();
  body.append("file", file.value);
  try {
    const data = await readResponse(
      await fetch("/api/documents", { method: "POST", body })
    );
    status.value = `${data.filename} indexed · ${data.chunks} chunks`;
    file.value = null;
    if (uploadInput.value) uploadInput.value.value = "";
    await loadDocuments();
  } catch (e) {
    error.value = e.message;
    showToast(e.message);
  } finally {
    busy.value = false;
  }
}
async function ask() {
  if (!question.value.trim() || busy.value) return;
  busy.value = true;
  answer.value = "";
  sources.value = [];
  try {
    const data = await readResponse(
      await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.value }),
      })
    );
    answer.value = data.answer;
    sources.value = data.sources || [];
  } catch (e) {
    showToast(e.message);
  } finally {
    busy.value = false;
  }
}
function newQuestion() {
  activeTab.value = "chat";
  question.value = "";
  answer.value = "";
  sources.value = [];
}
function syncTab() {
  if (location.hash === "#documents") activeTab.value = "documents";
}
onMounted(() => {
  syncTab();
  addEventListener("hashchange", syncTab);
  readResponse(fetch("/api/auth/me"))
    .then(() => {
      authenticated.value = true;
      loadDocuments();
    })
    .catch(() => {});
});
</script>
<template>
  <div class="min-h-screen bg-[#f7f7f4] text-[#202127] lg:flex">
    <div
      v-if="!authenticated"
      class="fixed inset-0 z-10 grid place-items-center bg-[#f7f7f4] p-4"
    >
      <form
        class="w-full max-w-sm rounded-2xl border border-[#e3e1da] bg-white p-7 shadow-xl"
        @submit.prevent="authenticate"
      >
        <div class="mb-3 text-center text-3xl text-[#c66b4d]">✦</div>
        <h1 class="text-center font-display text-2xl font-semibold">
          Welcome to contextual
        </h1>
        <p class="my-2 mb-6 text-center text-sm text-[#92918b]">
          Sign in to your private knowledge workspace.
        </p>
        <label class="mb-4 block text-xs font-semibold"
          >Email<input
            v-model="email"
            type="email"
            required
            class="mt-1.5 block w-full rounded-lg border border-[#deded8] px-3 py-2.5 text-sm" /></label
        ><label class="mb-4 block text-xs font-semibold"
          >Password<input
            v-model="password"
            type="password"
            minlength="8"
            required
            class="mt-1.5 block w-full rounded-lg border border-[#deded8] px-3 py-2.5 text-sm"
        /></label>
        <p v-if="authError" class="mb-3 text-xs text-red-600">{{ authError }}</p>
        <button
          class="w-full rounded-lg bg-[#c66b4d] py-3 text-sm font-semibold text-white"
        >
          {{ authMode === "login" ? "Sign in" : "Create account" }}</button
        ><button
          type="button"
          class="mt-4 w-full text-xs text-[#8b8b85]"
          @click="authMode = authMode === 'login' ? 'register' : 'login'"
        >
          {{
            authMode === "login"
              ? "Need an account? Register"
              : "Already registered? Sign in"
          }}
        </button>
      </form>
    </div>
    <div
      v-if="toast"
      class="fixed right-4 top-4 z-20 rounded-xl border border-[#e5b5a7] bg-[#fff7f4] px-4 py-3 text-xs text-[#713f38] shadow-xl"
      role="alert"
    >
      ! {{ toast }}
    </div>
    <aside
      class="flex shrink-0 flex-col border-b border-[#dfdfd8] bg-[#efefe9] px-5 py-5 lg:min-h-screen lg:w-64 lg:border-b-0 lg:border-r"
    >
      <div class="pb-6 font-display text-xl font-bold lg:pb-11">
        <span class="text-2xl text-[#c66b4d]">✦</span> contextual
      </div>
      <div
        class="hidden pb-3 font-mono text-[10px] tracking-widest text-[#8b8b85] lg:block"
      >
        WORKSPACE
      </div>
      <nav class="flex gap-1 lg:grid">
        <button
          class="rounded-lg px-3 py-2.5 text-left text-sm hover:bg-[#e5e4dc]"
          :class="{ 'bg-[#e5e4dc] font-semibold': activeTab === 'chat' }"
          @click="activeTab = 'chat'"
        >
          ◌ &nbsp; Ask documents</button
        ><button
          class="rounded-lg px-3 py-2.5 text-left text-sm hover:bg-[#e5e4dc]"
          :class="{ 'bg-[#e5e4dc] font-semibold': activeTab === 'documents' }"
          @click="activeTab = 'documents'"
        >
          ▤ &nbsp; Document library
          <span class="float-right font-mono text-xs">{{ documents.length }}</span>
        </button>
      </nav>
      <div class="mt-auto hidden border-t border-[#dddcd4] pt-4 text-xs lg:block">
        <strong>Researcher</strong
        ><small class="block text-[#92918b]">Personal workspace</small>
      </div>
    </aside>
    <main class="mx-auto w-full max-w-[1480px] px-4 py-7 sm:px-8 lg:px-14 lg:py-11">
      <header class="mb-8 flex items-start justify-between">
        <div>
          <span class="font-mono text-[10px] tracking-widest text-[#8b8b85]"
            >KNOWLEDGE WORKSPACE</span
          >
          <h1 class="mt-2 font-display text-2xl font-semibold sm:text-3xl">
            {{ activeTab === "chat" ? "Ask your documents" : "Your document library" }}
          </h1>
        </div>
        <button
          class="rounded-lg border border-[#deded8] px-3 py-2 text-xs"
          @click="newQuestion"
        >
          ＋ New question
        </button>
      </header>
      <div class="mb-8 flex gap-6 border-b border-[#e6e5df]">
        <button
          class="border-b-2 border-transparent pb-3 text-xs"
          :class="{ 'border-[#c66b4d] font-semibold': activeTab === 'chat' }"
          @click="activeTab = 'chat'"
        >
          Ask documents</button
        ><button
          class="border-b-2 border-transparent pb-3 text-xs"
          :class="{ 'border-[#c66b4d] font-semibold': activeTab === 'documents' }"
          @click="activeTab = 'documents'"
        >
          Documents
          <span class="rounded-full bg-[#f1dfd5] px-1.5 py-0.5 font-mono text-[10px]">{{
            documents.length
          }}</span>
        </button>
      </div>
      <section
        v-if="activeTab === 'chat'"
        class="mx-auto flex min-h-[600px] max-w-4xl flex-col"
      >
        <div
          v-if="!hasAnswer"
          class="flex flex-1 flex-col items-center pt-12 text-center"
        >
          <div
            class="mb-8 grid h-16 w-16 place-items-center rounded-full border border-[#e3b9a7] bg-[#f0ddd3] text-2xl text-[#c66b4d]"
          >
            ✦
          </div>
          <span class="font-mono text-[10px] tracking-widest text-[#8b8b85]"
            >YOUR AI RESEARCH ASSISTANT</span
          >
          <h2 class="mt-3 font-display text-3xl font-semibold sm:text-[38px]">
            What would you like<br /><em class="text-[#c66b4d] not-italic"
              >to understand?</em
            >
          </h2>
          <p class="mt-4 max-w-sm text-sm text-[#92918b]">
            Ask a question about your uploaded documents. Answers are grounded in your
            sources.
          </p>
          <div class="mt-7 flex gap-2">
            <button
              class="rounded-full border border-[#e1d2c9] bg-[#fdf7f3] px-3 py-2 text-xs"
              @click="question = 'Summarize the uploaded documents'"
            >
              Summarize my documents</button
            ><button
              class="rounded-full border border-[#e1d2c9] bg-[#fdf7f3] px-3 py-2 text-xs"
              @click="question = 'What are the key points?'"
            >
              Find key points
            </button>
          </div>
        </div>
        <div v-else class="flex-1 space-y-7 pb-8">
          <div class="flex justify-end">
            <span class="rounded-xl bg-[#eee4dc] px-4 py-3 text-sm">{{ question }}</span>
          </div>
          <div class="rounded-xl border border-[#e3e1da] bg-white p-5 shadow-sm">
            <div class="font-mono text-[10px] text-[#c66b4d]">✦ CONTEXTUAL</div>
            <p class="my-4 whitespace-pre-wrap text-sm leading-7">{{ answer }}</p>
            <div v-if="sources.length" class="flex flex-wrap gap-2 border-t pt-3">
              <span
                v-for="source in sources"
                :key="source.filename + source.chunk_index"
                class="rounded-md bg-[#f6eee9] px-2 py-1.5 font-mono text-[11px]"
                >↗ {{ source.filename }}</span
              >
            </div>
          </div>
        </div>
        <form
          class="rounded-xl border border-[#d9d8d1] bg-white p-3.5 shadow-sm"
          @submit.prevent="ask"
        >
          <textarea
            v-model="question"
            rows="2"
            placeholder="Ask anything about your documents…"
            class="w-full resize-none border-0 bg-transparent text-sm outline-none"
          ></textarea>
          <div class="flex justify-end">
            <button
              class="h-8 w-8 rounded-lg bg-[#c66b4d] text-lg text-white"
              :disabled="busy || !question.trim()"
            >
              {{ busy ? "…" : "↑" }}
            </button>
          </div>
        </form>
      </section>
      <section v-else class="mx-auto max-w-5xl">
        <div class="mb-8 flex items-end justify-between">
          <div>
            <span class="font-mono text-[10px] tracking-widest text-[#8b8b85]"
              >YOUR SOURCES</span
            >
            <h2 class="mt-2 font-display text-2xl font-semibold">
              Build your knowledge base
            </h2>
            <p class="mt-2 text-sm text-[#92918b]">
              Upload documents to give your assistant context.
            </p>
          </div>
          <span
            class="grid h-12 w-12 place-items-center rounded-full bg-[#f1dfd5] font-mono text-sm"
            >{{ documents.length }}</span
          >
        </div>
        <div class="grid gap-6 lg:grid-cols-2">
          <div class="rounded-xl border border-[#e3e1da] bg-white p-5 shadow-sm">
            <div
              class="cursor-pointer rounded-xl border border-dashed border-[#d7b9aa] bg-[#fdf7f3] p-8 text-center"
              @click="uploadInput?.click()"
            >
              <input
                ref="uploadInput"
                class="hidden"
                type="file"
                accept=".txt,.md,.pdf,.docx"
                @change="selectFile"
              />
              <div class="mb-3 text-2xl text-[#c66b4d]">↑</div>
              <strong class="block truncate text-sm">{{
                file ? file.name : "Drop a document here"
              }}</strong>
              <p class="mt-1 text-[10px] text-[#aaa09a]">
                PDF, DOCX, MD or TXT · 2 MB max
              </p>
            </div>
            <button
              class="mt-3 w-full rounded-lg bg-[#c66b4d] py-2.5 text-xs font-semibold text-white"
              :disabled="busy || !file"
              @click="upload"
            >
              ＋ {{ busy ? "Indexing..." : "Add document" }}
            </button>
            <p v-if="status" class="mt-2 text-[10px] text-green-700">✓ {{ status }}</p>
            <p v-if="error" class="mt-2 text-[10px] text-red-600">{{ error }}</p>
          </div>
          <div class="rounded-xl border border-[#e3e1da] bg-[#fbfbf8] p-5">
            <span class="font-mono text-[10px] tracking-wider text-[#8b8b85]"
              >INDEXED SOURCES</span
            >
            <h3 class="mt-1 font-display text-base font-semibold">Documents</h3>
            <div v-if="!documents.length" class="py-8 text-center text-xs text-[#aaa9a1]">
              No documents yet.
              <p class="mt-2">Add one to get started.</p>
            </div>
            <div
              v-for="document in documents"
              :key="document.id"
              class="flex items-center gap-3 border-t border-[#ecebe5] py-3"
            >
              <span class="text-[#c66b4d]">▤</span>
              <div class="min-w-0 flex-1">
                <strong class="block truncate text-xs">{{ document.filename }}</strong
                ><small class="text-[10px] text-[#aaa9a1]"
                  >{{ document.status }} · ready to search</small
                >
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>
