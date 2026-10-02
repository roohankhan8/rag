import os
# from openai import OpenAI
from google import genai
from google.genai.errors import ServerError

# client = OpenAI(api_key=os.environ.get("AI_API_KEY"))
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

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
    response = client.models.embed_content(
        model=os.environ.get("AI_EMBEDDING_MODEL", "gemini-embedding-001"),
        contents=text,
    )
    return response.embeddings[0].values


def answer_question(question, sources):
    def source_text(source):
        page = f" page {source['page']}" if source.get("page") else ""
        return f"[{source['filename']}{page} #{source['chunk_index']}] {source['text']}"

    context = "\n\n".join(
        source_text(source)
        for source in sources
    )
    prompt = (
        "Answer using only the context below. If the answer is not supported "
        "by the context, say: I could not find that in your documents. "
        "Do not use outside knowledge or invent citations.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    primary = os.environ.get("AI_CHAT_MODEL", "gemini-2.5-flash")
    fallback = os.environ.get("AI_CHAT_FALLBACK_MODEL", "gemini-3.5-flash-lite")
    try:
        response = client.models.generate_content(model=primary, contents=prompt)
    except ServerError as error:
        if error.code != 503 or fallback == primary:
            raise
        response = client.models.generate_content(model=fallback, contents=prompt)
    return response.text
