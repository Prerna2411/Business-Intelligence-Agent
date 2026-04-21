from __future__ import annotations

from langgraph.graph import END

from graph.state import BIState


def route_after_planner(state: BIState) -> str:
    return state.get("next_step", "sql")


def route_after_sql(state: BIState) -> str:
    return "analysis"


def route_after_analysis(state: BIState) -> str:
    return "reflection"


def route_after_reflection(state: BIState) -> str:
    return "visualization"


def route_after_visualization(state: BIState) -> str:
    return END
