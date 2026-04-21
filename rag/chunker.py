from __future__ import annotations

from rag.schemas import DocumentChunk


class DocumentChunker:
    def __init__(self, chunk_size: int = 800, overlap: int = 120) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(self, document_id: str, file_name: str, pages: list[dict]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for page in pages:
            page_number = page["page_number"]
            text = self._normalize(page["text"])
            if not text:
                continue

            start = 0
            chunk_index = 0
            while start < len(text):
                end = min(len(text), start + self.chunk_size)
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{document_id}:{page_number}:{chunk_index}",
                            document_id=document_id,
                            text=chunk_text,
                            metadata={
                                "file_name": file_name,
                                "page_number": page_number,
                                "chunk_index": chunk_index,
                            },
                        )
                    )
                if end >= len(text):
                    break
                start = max(end - self.overlap, start + 1)
                chunk_index += 1
        return chunks

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.split())
