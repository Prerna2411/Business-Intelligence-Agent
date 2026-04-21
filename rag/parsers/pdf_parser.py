from __future__ import annotations

from io import BytesIO


def parse_pdf(file_bytes: bytes) -> list[dict]:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(file_bytes))
    pages: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append(
            {
                "page_number": index,
                "text": page.extract_text() or "",
            }
        )
    return pages
