from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.services.llm_service import LLMService
from memory.hybrid_retriever import HybridRetriever


@dataclass
class RAGAgentOutput:
    summary: str
    insights: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    confidence: str = "medium"
    citations: list[dict[str, Any]] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "insights": self.insights,
            "follow_ups": self.follow_ups,
            "confidence": self.confidence,
            "citations": self.citations,
            "chunks": self.chunks,
        }


class RAGAgent:
    def __init__(self, llm: LLMService, retriever: HybridRetriever, top_k: int = 5) -> None:
        self.llm = llm
        self.retriever = retriever
        self.top_k = top_k

    def run(self, question: str) -> RAGAgentOutput:
        hits = self.retriever.retrieve(query=question, top_k=self.top_k)
        if not hits:
            return RAGAgentOutput(
                summary="No uploaded document context was available for this question.",
                insights=["Upload a PDF, DOCX, or text file and index it first."],
                follow_ups=[],
                confidence="low",
                citations=[],
                chunks=[],
            )

        fallback = self._fallback_answer(question=question, hits=hits)
        payload = self.llm.invoke_json(
            system_prompt=(
                "You are a grounded document QA agent. Return strict JSON with keys "
                "summary, insights, follow_ups, confidence. Answer only from the retrieved chunks."
            ),
            user_prompt=(
                f"Question: {question}\n"
                f"Retrieved chunks: {[{'file_name': hit.metadata.get('file_name'), 'page_number': hit.metadata.get('page_number'), 'text': hit.text} for hit in hits]}\n"
            ),
            fallback=fallback,
        )
        return RAGAgentOutput(
            summary=str(payload.get("summary") or fallback["summary"]),
            insights=self._normalize_list(payload.get("insights"), fallback["insights"]),
            follow_ups=self._normalize_list(payload.get("follow_ups"), fallback["follow_ups"]),
            confidence=str(payload.get("confidence") or fallback["confidence"]),
            citations=self._build_citations(hits),
            chunks=[{"score": hit.score, "text": hit.text, "metadata": hit.metadata} for hit in hits],
        )

    def _fallback_answer(self, question: str, hits) -> dict[str, Any]:
        top_hit = hits[0]
        snippet = top_hit.text[:280].strip()
        return {
            "summary": f"Based on the uploaded documents, the strongest matching evidence comes from {top_hit.metadata.get('file_name', 'the uploaded file')} (page {top_hit.metadata.get('page_number', '?')}). {snippet}",
            "insights": [
                "This answer is grounded in the uploaded document chunks retrieved by the hybrid retriever.",
                "Dense and keyword retrieval were combined before answer generation.",
            ],
            "follow_ups": ["Ask for a comparison, summary, or specific citation from the uploaded material."],
            "confidence": "medium",
        }

    @staticmethod
    def _build_citations(hits) -> list[dict[str, Any]]:
        citations = []
        for hit in hits:
            citations.append(
                {
                    "file_name": hit.metadata.get("file_name", ""),
                    "page_number": hit.metadata.get("page_number", ""),
                    "chunk_index": hit.metadata.get("chunk_index", ""),
                    "score": round(hit.score, 4),
                }
            )
        return citations

    @staticmethod
    def _normalize_list(value: Any, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return fallback
