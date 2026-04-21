from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agents.planner import PlannerOutput
from backend.agents.sql_agent import SQLAgentOutput
from backend.services.llm_service import LLMService


@dataclass
class AnalysisOutput:
    summary: str
    insights: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "insights": self.insights,
            "follow_ups": self.follow_ups,
            "confidence": self.confidence,
        }


class AnalysisAgent:
    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    def run(self, question: str, plan: PlannerOutput, sql_output: SQLAgentOutput) -> AnalysisOutput:
        rows = sql_output.result.get("rows", [])
        columns = sql_output.result.get("columns", [])

        if sql_output.error:
            return AnalysisOutput(
                summary="The SQL was generated, but execution failed before a business answer could be produced.",
                insights=[sql_output.error],
                follow_ups=["Check the generated SQL and confirm the selected ClickHouse columns are valid."],
                confidence="low",
            )

        if not rows:
            return AnalysisOutput(
                summary="The query ran successfully but returned no rows for the current question.",
                insights=["No matching data was returned from ClickHouse."],
                follow_ups=["Try widening the date range or asking with a more specific business metric."],
                confidence="medium",
            )

        fallback = self._fallback_summary(question=question, plan=plan, sql_output=sql_output)
        payload = self.llm.invoke_json(
            system_prompt=(
                "You are a BI analysis agent. Return strict JSON with keys "
                "summary, insights, follow_ups, confidence. Keep claims grounded in the provided rows."
            ),
            user_prompt=(
                f"Question: {question}\n"
                f"Intent: {plan.intent}\n"
                f"SQL: {sql_output.sql}\n"
                f"Columns: {columns}\n"
                f"Sample rows: {rows[:10]}\n"
                f"Row count: {sql_output.result.get('row_count', 0)}\n"
            ),
            fallback=fallback,
        )
        return AnalysisOutput(
            summary=payload.get("summary") or fallback["summary"],
            insights=self._normalize_list(payload.get("insights"), fallback["insights"]),
            follow_ups=self._normalize_list(payload.get("follow_ups"), fallback["follow_ups"]),
            confidence=str(payload.get("confidence") or fallback["confidence"]),
        )

    def _fallback_summary(
        self,
        question: str,
        plan: PlannerOutput,
        sql_output: SQLAgentOutput,
    ) -> dict[str, Any]:
        rows = sql_output.result.get("rows", [])
        columns = sql_output.result.get("columns", [])
        first_row = rows[0] if rows else {}
        numeric_columns = [
            column for column in columns if isinstance(first_row.get(column), (int, float))
        ]
        preview = ", ".join(f"{key}={value}" for key, value in list(first_row.items())[:3]) or "no preview"

        summary = (
            f"The database question was handled as {plan.intent.replace('_', ' ')}. "
            f"The query returned {len(rows)} rows with columns {', '.join(columns)}. "
            f"The first row looks like {preview}."
        )
        insights = [
            "The result is ready to render directly in the UI as a table.",
            f"Numeric columns detected for analysis: {', '.join(numeric_columns) if numeric_columns else 'none'}.",
            "A chart can be chosen from the same returned columns without another warehouse call.",
        ]
        follow_ups = [
            "Ask for a narrower segment or date window if you want a more targeted explanation.",
            "If the SQL looks right but the answer feels off, inspect the selected tables and columns below it.",
        ]
        return {
            "summary": summary,
            "insights": insights,
            "follow_ups": follow_ups,
            "confidence": "high" if rows else "medium",
        }

    @staticmethod
    def _normalize_list(value: Any, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return fallback
