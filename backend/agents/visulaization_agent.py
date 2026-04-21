from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.services.llm_service import LLMService


@dataclass
class VisualizationOutput:
    chart_type: str
    x_axis: str
    y_axis: str
    title: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "title": self.title,
            "reason": self.reason,
        }


class VisualizationAgent:
    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    def run(self, question: str, sql_result: dict[str, Any]) -> VisualizationOutput:
        columns = sql_result.get("columns", [])
        rows = sql_result.get("rows", [])

        fallback = self._fallback_visualization(question=question, columns=columns, rows=rows)
        if not columns:
            return fallback

        sample_rows = rows[:8]
        payload = self.llm.invoke_json(
            system_prompt=(
                "You are a BI visualization agent. Return strict JSON with keys "
                "chart_type, x_axis, y_axis, title, reason. "
                "Choose only from chart_type values: line, bar, scatter, table. "
                "Use only axes present in the provided columns. "
                "Prefer table when the result is not clearly chartable."
            ),
            user_prompt=(
                f"Question: {question}\n"
                f"Columns: {columns}\n"
                f"Sample rows: {sample_rows}\n"
                "Pick the best visualization for a Streamlit frontend."
            ),
            fallback=fallback.to_dict(),
        )

        chart_type = payload.get("chart_type", fallback.chart_type)
        x_axis = payload.get("x_axis", fallback.x_axis)
        y_axis = payload.get("y_axis", fallback.y_axis)
        title = payload.get("title", question or fallback.title)
        reason = payload.get("reason", fallback.reason)

        if chart_type not in {"line", "bar", "scatter", "table"}:
            return fallback
        if chart_type != "table" and (x_axis not in columns or y_axis not in columns):
            return fallback

        return VisualizationOutput(
            chart_type=chart_type,
            x_axis=x_axis,
            y_axis=y_axis,
            title=title,
            reason=reason,
        )

    def _fallback_visualization(
        self,
        question: str,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> VisualizationOutput:
        if not columns:
            return VisualizationOutput(
                chart_type="table",
                x_axis="",
                y_axis="",
                title="Query Result",
                reason="No chartable columns were returned, so the table is the primary output.",
            )

        sample = rows[0] if rows else {}
        numeric_columns = [column for column in columns if isinstance(sample.get(column), (int, float))]
        time_columns = [
            column
            for column in columns
            if any(keyword in column.lower() for keyword in {"date", "time", "day", "month", "year", "period"})
        ]
        category_columns = [column for column in columns if column not in numeric_columns]

        if time_columns and numeric_columns:
            return VisualizationOutput(
                chart_type="line",
                x_axis=time_columns[0],
                y_axis=numeric_columns[0],
                title=question,
                reason="A time column and numeric measure were returned, so a line chart best shows the trend.",
            )
        if category_columns and numeric_columns:
            return VisualizationOutput(
                chart_type="bar",
                x_axis=category_columns[0],
                y_axis=numeric_columns[0],
                title=question,
                reason="A categorical dimension and numeric measure were returned, so a bar chart compares categories well.",
            )
        if len(numeric_columns) >= 2:
            return VisualizationOutput(
                chart_type="scatter",
                x_axis=numeric_columns[0],
                y_axis=numeric_columns[1],
                title=question,
                reason="Two numeric columns were returned, so a scatter plot can show their relationship.",
            )
        return VisualizationOutput(
            chart_type="table",
            x_axis="",
            y_axis="",
            title="Query Result",
            reason="The returned data shape is best explored directly as a table.",
        )
