from __future__ import annotations

import hashlib
from pathlib import Path

from backend.app.config import Settings
from backend.services.embedding_service import EmbeddingService
from memory.document_store import ChromaDocumentStore
from memory.sparse_index import SparseKeywordIndex
from rag.chunker import DocumentChunker
from rag.parsers.docx_parser import parse_docx
from rag.parsers.pdf_parser import parse_pdf
from rag.parsers.text_parser import parse_text
from rag.schemas import IngestionResult


class DocumentIngestor:
    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        document_store: ChromaDocumentStore,
        sparse_index: SparseKeywordIndex,
    ) -> None:
        self.settings = settings
        self.embedding_service = embedding_service
        self.document_store = document_store
        self.sparse_index = sparse_index
        self.chunker = DocumentChunker(
            chunk_size=settings.rag_chunk_size,
            overlap=settings.rag_chunk_overlap,
        )

    def ingest_file(self, file_name: str, file_bytes: bytes) -> IngestionResult:
        uploads_dir = Path(self.settings.uploads_path)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        document_id = self._build_document_id(file_name=file_name, file_bytes=file_bytes)
        file_path = uploads_dir / f"{document_id}_{file_name}"
        file_path.write_bytes(file_bytes)

        suffix = Path(file_name).suffix.lower()
        if suffix == ".pdf":
            pages = parse_pdf(file_bytes)
        elif suffix == ".docx":
            pages = parse_docx(file_bytes)
        else:
            pages = parse_text(file_bytes)

        chunks = self.chunker.chunk_document(document_id=document_id, file_name=file_name, pages=pages)
        if not chunks:
            return IngestionResult(
                document_id=document_id,
                file_name=file_name,
                chunk_count=0,
                status="skipped",
                message="No readable text was extracted from the uploaded file.",
            )

        self.document_store.upsert_chunks(chunks=chunks, embeddings=self.embedding_service.embed_documents([chunk.text for chunk in chunks]))
        self.sparse_index.upsert(chunks)
        return IngestionResult(
            document_id=document_id,
            file_name=file_name,
            chunk_count=len(chunks),
            status="indexed",
            message=f"Indexed {len(chunks)} chunks from {file_name}.",
        )

    @staticmethod
    def _build_document_id(file_name: str, file_bytes: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(file_name.encode("utf-8"))
        digest.update(file_bytes)
        return digest.hexdigest()[:16]
