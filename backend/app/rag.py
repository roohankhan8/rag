import os
# from openai import OpenAI
from google import genai

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
        model=os.environ["AI_EMBEDDING_MODEL"],
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
        "Answer using only the context below. If the answer is not in the "
        "context, say you do not know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    chat = client.chats.create(model=os.environ["AI_CHAT_MODEL"])
    response = chat.send_message(prompt)
    return response.text
