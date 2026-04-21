from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanStep:
    name: str
    description: str
    owner: str


@dataclass
class PlannerOutput:
    intent: str
    needs_database: bool
    metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    time_range: str = "unspecified"
    steps: list[PlanStep] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "needs_database": self.needs_database,
            "metrics": self.metrics,
            "dimensions": self.dimensions,
            "time_range": self.time_range,
            "steps": [step.__dict__ for step in self.steps],
            "assumptions": self.assumptions,
        }


class PlannerAgent:
    DB_HINTS = {
        "table",
        "tables",
        "column",
        "columns",
        "database",
        "db",
        "sql",
        "query",
        "revenue",
        "sales",
        "profit",
        "orders",
        "customers",
        "count",
        "total",
        "trend",
        "clickhouse",
    }

    def run(self, question: str) -> PlannerOutput:
        tokens = [token.strip(" ,.?").lower() for token in question.split()]
        metrics = [
            token
            for token in tokens
            if token in {"revenue", "sales", "profit", "orders", "customers", "margin", "count", "total"}
        ]
        dimensions = [
            token
            for token in tokens
            if token in {"region", "product", "category", "segment", "customer", "date", "month", "quarter", "year"}
        ]
        needs_database = any(token in self.DB_HINTS for token in tokens)

        if "why" in tokens or "driver" in tokens or "reason" in tokens:
            intent = "root_cause_analysis"
        elif "compare" in tokens or "vs" in tokens:
            intent = "comparison_analysis"
        elif "trend" in tokens or "over" in tokens:
            intent = "trend_analysis"
        else:
            intent = "descriptive_analysis"

        time_range = "monthly" if "month" in tokens else "quarterly" if "quarter" in tokens else "latest"
        steps = [
            PlanStep("planner", "Classify the question and decide whether warehouse access is needed.", "planner"),
            PlanStep("schema_grounding", "Inspect ClickHouse tables and columns relevant to the question.", "sql_agent"),
            PlanStep("sql_generation", "Generate safe ClickHouse SQL with Groq.", "sql_agent"),
            PlanStep("execution", "Run the SQL against ClickHouse and collect rows.", "sql_agent"),
            PlanStep("analysis", "Summarize the results for the user with Groq.", "analysis_agent"),
            PlanStep("visualization", "Choose a chart using the returned result columns.", "visualization_agent"),
            PlanStep("reflection", "Validate confidence, assumptions, and remaining risks.", "reflection_agent"),
        ]
        assumptions = [
            "The question can be answered from the current ClickHouse database.",
            "Only read-only SELECT queries should be generated and executed.",
        ]
        return PlannerOutput(
            intent=intent,
            needs_database=needs_database,
            metrics=metrics,
            dimensions=dimensions,
            time_range=time_range,
            steps=steps,
            assumptions=assumptions,
        )
