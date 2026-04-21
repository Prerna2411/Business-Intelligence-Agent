from __future__ import annotations

from mcp.schemas import MCPServerConfig, MCPTool


def build_default_registry() -> dict[str, MCPServerConfig]:
    return {
        "postgres": MCPServerConfig(
            name="postgres",
            transport="stdio",
            command="python",
            args=["mcp-servers/sql-servers/postgres_server.py"],
            tools=[
                MCPTool("list_tables", "Inspect analytical tables and views."),
                MCPTool("run_query", "Execute read-only SQL against the warehouse."),
            ],
        ),

        "clickhouse": MCPServerConfig(
            name="clickhouse",
            transport="stdio",
            command="python",
            args=["mcp-servers/clickhouse-server/server.py"],
            tools=[
                MCPTool("list_tables", "List all tables in ClickHouse"),
                MCPTool("run_query", "Execute SQL queries on ClickHouse"),
            ],
        ),
        "python": MCPServerConfig(
            name="python",
            transport="stdio",
            command="python",
            args=["mcp-servers/python-server/server.py"],
            tools=[
                MCPTool("run_python", "Execute safe dataframe and statistics code."),
            ],
        ),
        "charts": MCPServerConfig(
            name="charts",
            transport="stdio",
            command="python",
            args=["mcp-servers/chart-servers/server.py"],
            tools=[
                MCPTool("build_chart_spec", "Generate chart-ready Vega-Lite style specs."),
            ],
        ),
    }
