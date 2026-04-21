from __future__ import annotations

from mcp.registry import build_default_registry
from mcp.schemas import MCPInvokeRequest, MCPInvokeResult, MCPServerConfig


class MCPClient:
    """Small in-process MCP facade for development and tests."""

    def __init__(self, registry: dict[str, MCPServerConfig] | None = None) -> None:
        self.registry = registry or build_default_registry()

    def list_servers(self) -> list[str]:
        return sorted(self.registry.keys())

    def list_tools(self, server_name: str) -> list[str]:
        server = self.registry[server_name]
        return [tool.name for tool in server.tools]

    def invoke(self, request: MCPInvokeRequest) -> MCPInvokeResult:
        if request.server_name not in self.registry:
            return MCPInvokeResult(success=False, content=None, error=f"Unknown MCP server: {request.server_name}")
        if request.tool_name not in self.list_tools(request.server_name):
            return MCPInvokeResult(success=False, content=None, error=f"Unknown tool: {request.tool_name}")
        payload = {
            "server": request.server_name,
            "tool": request.tool_name,
            "arguments": request.arguments,
            "status": "mocked",
        }
        return MCPInvokeResult(success=True, content=payload)
    