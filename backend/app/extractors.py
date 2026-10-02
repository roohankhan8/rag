from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extract_document(filename, data):
    extension = Path(filename).suffix.lower()

    if extension in {".txt", ".md"}:
        return [{"text": data.decode("utf-8", errors="replace"), "page": None}]

    if extension == ".pdf":
        reader = PdfReader(BytesIO(data))
        return [
            {"text": page.extract_text() or "", "page": index + 1}
            for index, page in enumerate(reader.pages)
        ]

    if extension == ".docx":
        document = Document(BytesIO(data))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        return [{"text": text, "page": None}]

    raise ValueError("unsupported file type")
