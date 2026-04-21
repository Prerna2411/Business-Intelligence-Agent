from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from graph.nodes import WorkflowNodes
from graph.routes import (
    route_after_analysis,
    route_after_planner,
    route_after_reflection,
    route_after_sql,
    route_after_visualization,
)
from graph.state import BIState


class BIWorkflow:
    def __init__(self, nodes: WorkflowNodes) -> None:
        self.nodes = nodes
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(BIState)
        graph.add_node("planner", self.nodes.run_planner)
        graph.add_node("sql", self.nodes.run_sql)
        graph.add_node("analysis", self.nodes.run_analysis)
        graph.add_node("reflection", self.nodes.run_reflection)
        graph.add_node("visualization", self.nodes.run_visualization)

        graph.add_edge(START, "planner")
        graph.add_conditional_edges("planner", route_after_planner, {"sql": "sql", "analysis": "analysis"})
        graph.add_conditional_edges("sql", route_after_sql, {"analysis": "analysis"})
        graph.add_conditional_edges("analysis", route_after_analysis, {"reflection": "reflection"})
        graph.add_conditional_edges("reflection", route_after_reflection, {"visualization": "visualization"})
        graph.add_conditional_edges("visualization", route_after_visualization, {END: END})
        return graph.compile()

    def run(self, state: BIState) -> BIState:
        return self.graph.invoke(state)
