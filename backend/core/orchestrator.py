from __future__ import annotations

from backend.agents.analysis import AnalysisAgent
from backend.agents.planner import PlannerAgent
from backend.agents.reflection_agent import ReflectionAgent
from backend.agents.sql_agent import SQLAgent
from backend.agents.visulaization_agent import VisualizationAgent
from backend.app.config import Settings
from backend.services.clickhouse_service import ClickHouseService
from backend.services.llm_service import LLMService
from graph.nodes import WorkflowNodes
from graph.state import build_initial_state, final_answer
from graph.workflow import BIWorkflow
from memory.retriever import MemoryRetriever


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        retriever: MemoryRetriever,
        llm: LLMService,
        clickhouse: ClickHouseService,
    ) -> None:
        self.settings = settings
        self.retriever = retriever
        self.workflow = BIWorkflow(
            WorkflowNodes(
                planner=PlannerAgent(),
                sql_agent=SQLAgent(llm=llm, clickhouse=clickhouse),
                analysis_agent=AnalysisAgent(llm=llm),
                reflection_agent=ReflectionAgent(),
                visualization_agent=VisualizationAgent(llm=llm),
            )
        )

    def run(self, question: str) -> dict:
        state = build_initial_state(
            question=question,
            memories=self.retriever.retrieve(question, top_k=self.settings.top_k_memories),
        )
        result_state = self.workflow.run(state)
        result = final_answer(result_state)
        plan = result.get("plan") or {}
        self.retriever.remember(
            record_id=f"memory-{abs(hash(question))}",
            text=question,
            metadata={"intent": plan.get("intent", "unknown")},
        )
        return result
