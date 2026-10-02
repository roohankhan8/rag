<script setup>
import { ref } from "vue";

const file = ref(null);
const question = ref("");
const answer = ref("");
const sources = ref([]);
const message = ref("");
const busy = ref(false);

function selectFile(event) {
  file.value = event.target.files[0];
}

async function upload() {
  if (!file.value) return;
  busy.value = true;
  message.value = "";
  const body = new FormData();
  body.append("file", file.value);
  try {
    const response = await fetch("/api/documents", { method: "POST", body });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Upload failed");
    message.value = `Indexed ${data.chunks} chunks from ${data.document_id}.`;
  } catch (error) {
    message.value = error.message;
  } finally {
    busy.value = false;
  }
}

async function ask() {
  if (!question.value.trim()) return;
  busy.value = true;
  answer.value = "";
  sources.value = [];
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Question failed");
    answer.value = data.answer;
    sources.value = data.sources;
  } catch (error) {
    answer.value = error.message;
  } finally {
    busy.value = false;
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
body {
  font-family: system-ui, sans-serif;
  margin: 0;
}
main {
  max-width: 760px;
  margin: 40px auto;
  padding: 0 20px;
}
section {
  border: 1px solid #ddd;
  border-radius: 8px;
  margin: 20px 0;
  padding: 20px;
}
input {
  margin-right: 8px;
  padding: 8px;
}
button {
  padding: 8px 14px;
}
li {
  margin: 10px 0;
}
</style>
