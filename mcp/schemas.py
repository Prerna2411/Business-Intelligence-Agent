from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    transport: str
    command: str
    args: list[str] = field(default_factory=list)
    tools: list[MCPTool] = field(default_factory=list)


@dataclass
class MCPInvokeRequest:
    server_name: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPInvokeResult:
    success: bool
    content: Any
    error: str | None = None
