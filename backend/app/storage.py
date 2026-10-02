import math


class MemoryStore:
    def __init__(self):
        self.items = []

    def add(self, document_id, filename, chunk_index, text, embedding, page=None):
        self.items.append({
            "document_id": document_id,
            "filename": filename,
            "chunk_index": chunk_index,
            "text": text,
            "embedding": embedding,
            "page": page,
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
