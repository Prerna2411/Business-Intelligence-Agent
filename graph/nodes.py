from __future__ import annotations

from backend.agents.analysis import AnalysisAgent
from backend.agents.planner import PlannerAgent
from backend.agents.reflection_agent import ReflectionAgent
from backend.agents.sql_agent import SQLAgent
from backend.agents.visulaization_agent import VisualizationAgent
from graph.state import BIState


class WorkflowNodes:
    def __init__(
        self,
        planner: PlannerAgent,
        sql_agent: SQLAgent,
        analysis_agent: AnalysisAgent,
        reflection_agent: ReflectionAgent,
        visualization_agent: VisualizationAgent,
    ) -> None:
        self.planner = planner
        self.sql_agent = sql_agent
        self.analysis_agent = analysis_agent
        self.reflection_agent = reflection_agent
        self.visualization_agent = visualization_agent

    def run_planner(self, state: BIState) -> BIState:
        plan = self.planner.run(state["question"])
        return {
            **state,
            "plan": plan.to_dict(),
            "next_step": "sql" if plan.needs_database else "analysis",
        }

    def run_sql(self, state: BIState) -> BIState:
        plan = self.planner.run(state["question"])
        sql_output = self.sql_agent.run(state["question"], plan)
        return {
            **state,
            "plan": state.get("plan") or plan.to_dict(),
            "sql": sql_output.to_dict(),
            "next_step": "analysis",
        }

    def run_analysis(self, state: BIState) -> BIState:
        plan = self.planner.run(state["question"])
        sql_output = self.sql_agent.run(state["question"], plan) if not state.get("sql") else None
        sql_payload = state.get("sql") or sql_output.to_dict()
        analysis_output = self.analysis_agent.run(
            state["question"],
            plan,
            sql_output if sql_output else self._sql_output_from_dict(sql_payload),
        )
        return {
            **state,
            "plan": state.get("plan") or plan.to_dict(),
            "sql": sql_payload,
            "analysis": analysis_output.to_dict(),
            "next_step": "reflection",
        }

    def run_reflection(self, state: BIState) -> BIState:
        sql_output = self._sql_output_from_dict(state["sql"])
        analysis_output = self._analysis_output_from_dict(state["analysis"])
        reflection = self.reflection_agent.run(sql_output, analysis_output)
        return {
            **state,
            "reflection": reflection.to_dict(),
            "next_step": "visualization",
        }

    def run_visualization(self, state: BIState) -> BIState:
        sql_result = state.get("sql", {}).get("result", {})
        visualization = self.visualization_agent.run(state["question"], sql_result)
        return {
            **state,
            "visualization": visualization.to_dict(),
            "next_step": "end",
        }

    @staticmethod
    def _sql_output_from_dict(payload: dict):
        from backend.agents.sql_agent import SQLAgentOutput

        return SQLAgentOutput(
            sql=payload.get("sql", ""),
            rationale=payload.get("rationale", ""),
            selected_tables=payload.get("selected_tables", []),
            selected_columns=payload.get("selected_columns", []),
            result=payload.get("result", {}),
            warnings=payload.get("warnings", []),
            error=payload.get("error"),
        )

    @staticmethod
    def _analysis_output_from_dict(payload: dict):
        from backend.agents.analysis import AnalysisOutput

        return AnalysisOutput(
            summary=payload.get("summary", ""),
            insights=payload.get("insights", []),
            follow_ups=payload.get("follow_ups", []),
            confidence=payload.get("confidence", "medium"),
        )
