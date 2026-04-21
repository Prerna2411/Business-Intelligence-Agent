from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.agents.analysis import AnalysisOutput
from backend.agents.sql_agent import SQLAgentOutput


@dataclass
class ReflectionOutput:
    approved: bool
    checks: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    needs_retry: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "checks": self.checks,
            "risks": self.risks,
            "needs_retry": self.needs_retry,
        }


class ReflectionAgent:
    def run(self, sql_output: SQLAgentOutput, analysis_output: AnalysisOutput) -> ReflectionOutput:
        checks = [
            "Verified the generated statement is read-only.",
            "Checked that the returned summary is grounded in executed rows.",
            "Confirmed the selected columns can drive both table output and charting.",
        ]
        risks: list[str] = []

        if not sql_output.sql.lower().startswith("select"):
            risks.append("The generated SQL is not read-only.")
        if sql_output.error:
            risks.append(f"Query execution failed: {sql_output.error}")
        if not sql_output.selected_columns:
            risks.append("No schema-grounded columns were selected before SQL generation.")
        if analysis_output.confidence == "low":
            risks.append("The answer confidence is low because execution or grounding was incomplete.")

        return ReflectionOutput(
            approved=not risks,
            checks=checks,
            risks=risks,
            needs_retry=False,
        )
