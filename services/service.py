from __future__ import annotations

from backend.app.config import get_settings
from backend.agents.rag_agent import RAGAgent
from backend.core.executor import Executor
from backend.core.orchestrator import Orchestrator
from backend.services.clickhouse_service import ClickHouseService
from backend.services.embedding_service import EmbeddingService
from backend.services.llm_service import LLMService
from memory.document_store import ChromaDocumentStore
from memory.hybrid_retriever import HybridRetriever
from memory.retriever import MemoryRetriever
from memory.short_term import ShortTermMemory
from memory.sparse_index import SparseKeywordIndex
from memory.vector_store import InMemoryVectorStore
from rag.ingest import DocumentIngestor


class BIService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.short_term_memory = ShortTermMemory()
        self.vector_store = InMemoryVectorStore()
        self.retriever = MemoryRetriever(self.vector_store)
        self.llm = LLMService(self.settings)
        self.clickhouse = ClickHouseService(self.settings)
        self.embedding_service = EmbeddingService()
        self.document_store = ChromaDocumentStore(self.settings.chroma_path)
        self.sparse_index = SparseKeywordIndex(self.settings.sparse_index_path)
        self.hybrid_retriever = HybridRetriever(
            document_store=self.document_store,
            sparse_index=self.sparse_index,
            embedding_service=self.embedding_service,
        )
        self.document_ingestor = DocumentIngestor(
            settings=self.settings,
            embedding_service=self.embedding_service,
            document_store=self.document_store,
            sparse_index=self.sparse_index,
        )
        self.rag_agent = RAGAgent(
            llm=self.llm,
            retriever=self.hybrid_retriever,
            top_k=self.settings.rag_top_k,
        )
        self.executor = Executor(
            Orchestrator(
                settings=self.settings,
                retriever=self.retriever,
                llm=self.llm,
                clickhouse=self.clickhouse,
            )
        )

    def runtime_status(self) -> dict:
        has_api_key = self.settings.has_groq_api_key
        has_database = self.settings.has_clickhouse_credentials
        return {
            "mock_mode": not has_api_key,
            "has_api_key": has_api_key,
            "has_database": has_database,
            "has_chroma": self.document_store.is_available,
            "document_count": len(self.document_store.list_documents()) if self.document_store.is_available else 0,
            "groq_model": self.settings.groq_model,
            "clickhouse_host": self.settings.clickhouse_host,
            "reason": (
                "Groq is not configured, so SQL and summaries will fall back to deterministic schema-driven logic."
                if not has_api_key
                else "Groq and ClickHouse are available for live DB reasoning."
            ),
        }

    def ingest_documents(self, uploaded_files: list[tuple[str, bytes]]) -> list[dict]:
        results = []
        for file_name, file_bytes in uploaded_files:
            try:
                result = self.document_ingestor.ingest_file(file_name=file_name, file_bytes=file_bytes)
                results.append(
                    {
                        "document_id": result.document_id,
                        "file_name": result.file_name,
                        "chunk_count": result.chunk_count,
                        "status": result.status,
                        "message": result.message,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "document_id": "",
                        "file_name": file_name,
                        "chunk_count": 0,
                        "status": "error",
                        "message": f"Failed to index {file_name}: {exc}",
                    }
                )
        return results

    def list_documents(self) -> list[dict]:
        docs = {doc["document_id"]: doc for doc in self.sparse_index.list_documents()}
        for doc in self.document_store.list_documents():
            docs[doc["document_id"]] = doc
        return sorted(docs.values(), key=lambda item: item["file_name"])

    def ask(self, question: str, use_rag: bool = False) -> dict:
        self.short_term_memory.add("user", question)
        if use_rag and self.list_documents():
            rag_result = self.rag_agent.run(question).to_dict()
            result = {
                "question": question,
                "analysis": {
                    "summary": rag_result["summary"],
                    "insights": rag_result["insights"],
                    "follow_ups": rag_result["follow_ups"],
                    "confidence": rag_result["confidence"],
                },
                "rag": rag_result,
                "sql": {},
                "visualization": {"chart_type": "table", "x_axis": "", "y_axis": "", "title": "Document Answer", "reason": "Document Q&A does not produce a SQL chart by default."},
                "reflection": {"approved": True, "checks": ["Hybrid RAG was used because uploaded documents are available."], "risks": [], "needs_retry": False},
                "plan": {"intent": "document_question_answering", "route": "rag"},
            }
        else:
            result = self.executor.execute(question)

        summary = result.get("analysis", {}).get("summary", "")
        if summary:
            self.short_term_memory.add("assistant", summary)
        result["conversation"] = self.short_term_memory.dump()
        result["runtime"] = self.runtime_status()
        result["documents"] = self.list_documents()
        return result
