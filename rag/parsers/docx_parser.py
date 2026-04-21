from __future__ import annotations

from io import BytesIO


def parse_docx(file_bytes: bytes) -> list[dict]:
    from docx import Document

    document = Document(BytesIO(file_bytes))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
    return [{"page_number": 1, "text": text}]
