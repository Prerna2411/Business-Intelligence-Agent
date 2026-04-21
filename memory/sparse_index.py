from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from rag.schemas import DocumentChunk, RetrievalHit


class SparseKeywordIndex:
    def __init__(self, index_path: str) -> None:
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, dict] = self._load()

    def upsert(self, chunks: list[DocumentChunk]) -> None:
        for chunk in chunks:
            term_counts = Counter(self._tokenize(chunk.text))
            self._records[chunk.chunk_id] = {
                "document_id": chunk.document_id,
                "text": chunk.text,
                "metadata": chunk.metadata,
                "term_counts": dict(term_counts),
                "length": sum(term_counts.values()),
            }
        self._save()

    def search(self, query: str, top_k: int = 5) -> list[RetrievalHit]:
        query_terms = self._tokenize(query)
        if not query_terms or not self._records:
            return []

        doc_freq = Counter()
        for record in self._records.values():
            for token in set(record["term_counts"]):
                doc_freq[token] += 1

        total_docs = max(len(self._records), 1)
        avg_doc_length = sum(record["length"] for record in self._records.values()) / total_docs
        scores: list[tuple[float, str, dict]] = []

        for chunk_id, record in self._records.items():
            score = 0.0
            for term in query_terms:
                tf = record["term_counts"].get(term, 0)
                if not tf:
                    continue
                idf = math.log(1 + (total_docs - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
                score += idf * ((tf * 2.2) / (tf + 1.2 * (1 - 0.75 + 0.75 * record["length"] / max(avg_doc_length, 1))))
            if score > 0:
                scores.append((score, chunk_id, record))

        scores.sort(key=lambda item: item[0], reverse=True)
        hits = []
        for score, chunk_id, record in scores[:top_k]:
            hits.append(
                RetrievalHit(
                    chunk_id=chunk_id,
                    text=record["text"],
                    score=score,
                    metadata=record["metadata"],
                )
            )
        return hits

    def list_documents(self) -> list[dict]:
        seen: dict[str, dict] = {}
        for record in self._records.values():
            document_id = record.get("document_id", "")
            metadata = record.get("metadata", {})
            if document_id and document_id not in seen:
                seen[document_id] = {
                    "document_id": document_id,
                    "file_name": metadata.get("file_name", ""),
                }
        return sorted(seen.values(), key=lambda item: item["file_name"])

    def _load(self) -> dict[str, dict]:
        if not self.index_path.exists():
            return {}
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        self.index_path.write_text(json.dumps(self._records, ensure_ascii=True, indent=2), encoding="utf-8")

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token.strip(".,:;!?()[]{}\"'").lower() for token in text.split() if token.strip()]
