from mcp.client2 import MCPClient
from mcp.schemas import MCPInvokeRequest


def test_mcp_registry_and_invoke_mock():
    client = MCPClient()

    assert "postgres" in client.list_servers()
    result = client.invoke(MCPInvokeRequest(server_name="postgres", tool_name="run_query", arguments={"sql": "SELECT 1"}))

    assert result.success is True
    assert result.content["status"] == "mocked"
