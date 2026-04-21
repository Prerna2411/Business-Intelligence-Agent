from __future__ import annotations

from typing import Any, Literal, TypedDict


class BIState(TypedDict, total=False):
    question: str
    next_step: Literal["sql", "analysis", "reflection", "visualization", "end"] | None
    plan: dict[str, Any] | None
    sql: dict[str, Any] | None
    analysis: dict[str, Any] | None
    reflection: dict[str, Any] | None
    visualization: dict[str, Any] | None
    memories: list[dict[str, Any]]


def build_initial_state(question: str, memories: list[dict[str, Any]] | None = None) -> BIState:
    return {
        "question": question,
        "next_step": None,
        "plan": None,
        "sql": None,
        "analysis": None,
        "reflection": None,
        "visualization": None,
        "memories": memories or [],
    }


def final_answer(state: BIState) -> dict[str, Any]:
    return {
        "question": state["question"],
        "plan": state.get("plan"),
        "sql": state.get("sql"),
        "analysis": state.get("analysis"),
        "reflection": state.get("reflection"),
        "visualization": state.get("visualization"),
        "memories": state.get("memories", []),
    }
