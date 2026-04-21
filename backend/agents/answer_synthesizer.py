from __future__ import annotations


class AnswerSynthesizer:
    def combine(self, db_result: dict | None, rag_result: dict | None) -> dict:
        db_result = db_result or {}
        rag_result = rag_result or {}

        sections = []
        if rag_result.get("summary"):
            sections.append(f"Document answer: {rag_result['summary']}")
        if db_result.get("analysis", {}).get("summary"):
            sections.append(f"Database answer: {db_result['analysis']['summary']}")

        return {
            "summary": "\n\n".join(sections) if sections else "No answer was synthesized.",
            "db_result": db_result,
            "rag_result": rag_result,
        }
