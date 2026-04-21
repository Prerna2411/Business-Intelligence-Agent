from __future__ import annotations

from collections import deque


class ShortTermMemory:
    def __init__(self, max_items: int = 10) -> None:
        self._items: deque[dict] = deque(maxlen=max_items)

    def add(self, role: str, content: str) -> None:
        self._items.append({"role": role, "content": content})

    def dump(self) -> list[dict]:
        return list(self._items)
