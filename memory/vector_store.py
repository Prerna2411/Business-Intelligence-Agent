from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass
class VectorRecord:
    record_id: str
    text: str
    metadata: dict
    vector: list[float]


class InMemoryVectorStore:
    """A tiny stand-in so the rest of the architecture stays testable."""

    def __init__(self) -> None:
        self._records: list[VectorRecord] = []

    def upsert(self, record_id: str, text: str, metadata: dict | None = None) -> None:
        metadata = metadata or {}
        vector = self._embed(text)
        self._records = [record for record in self._records if record.record_id != record_id]
        self._records.append(VectorRecord(record_id=record_id, text=text, metadata=metadata, vector=vector))

    def search(self, query: str, top_k: int = 3) -> list[VectorRecord]:
        query_vector = self._embed(query)
        scored = [
            (self._cosine_similarity(query_vector, record.vector), record)
            for record in self._records
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:top_k]]

    @staticmethod
    def _embed(text: str) -> list[float]:
        counts = [0.0] * 8
        for index, char in enumerate(text.lower()):
            counts[index % len(counts)] += (ord(char) % 23) / 23.0
        return counts

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = sqrt(sum(a * a for a in left))
        right_norm = sqrt(sum(b * b for b in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)


