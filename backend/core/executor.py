from __future__ import annotations

from backend.core.orchestrator import Orchestrator


class Executor:
    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator

    def execute(self, question: str) -> dict:
        return self.orchestrator.run(question)
