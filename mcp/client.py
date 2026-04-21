import os
from pathlib import Path

import clickhouse_connect
from dotenv import load_dotenv
from mcp.server import FastMCP

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

server = FastMCP(name="clickhouse")


def get_clickhouse_client():
    host = os.getenv("CLICKHOUSE_HOST")
    port = os.getenv("CLICKHOUSE_PORT")
    username = os.getenv("CLICKHOUSE_USER")
    password = os.getenv("CLICKHOUSE_PASSWORD")

    if not host or not port or not username or not password:
        raise ValueError(
            "Missing one or more ClickHouse environment variables: "
            "CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD"
        )

    # Bypass any local proxy settings for direct ClickHouse Cloud access.
    os.environ["NO_PROXY"] = host
    os.environ["no_proxy"] = host

    return clickhouse_connect.get_client(
        host=host,
        port=int(port),
        username=username,
        password=password,
        secure=True,
    )


try:
    result = get_clickhouse_client().query("SELECT 1")
    print("ClickHouse Connected:", result.result_rows)
except Exception as e:
    print("Connection Failed:", str(e))


@server.tool()
def health_check():
    try:
        result = get_clickhouse_client().query("SELECT 1")
        return {"status": "connected", "result": result.result_rows}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@server.tool()
def list_tables():
    return get_clickhouse_client().query("SHOW TABLES").result_rows


@server.tool()
def run_query(query: str):
    if not query.lower().strip().startswith("select"):
        return "Only SELECT queries allowed"

    result = get_clickhouse_client().query(query)
    return result.result_rows


@server.tool()
def get_schema():
    return get_clickhouse_client().query(
        """
        SELECT table, name, type
        FROM system.columns
        WHERE database = currentDatabase()
        """
    ).result_rows


if __name__ == "__main__":
    server.run()
