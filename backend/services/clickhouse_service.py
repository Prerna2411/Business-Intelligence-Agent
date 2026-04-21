from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import clickhouse_connect

from backend.app.config import Settings


@dataclass(frozen=True)
class ColumnInfo:
    database: str
    table: str
    name: str
    type: str

    def to_dict(self) -> dict[str, str]:
        return {
            "database": self.database,
            "table": self.table,
            "name": self.name,
            "type": self.type,
        }


class ClickHouseService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    @property
    def is_available(self) -> bool:
        return self.settings.has_clickhouse_credentials

    def _get_client(self):
        if self._client is None:
            if not self.is_available:
                raise ValueError("ClickHouse credentials are not configured")
            host = self.settings.clickhouse_host or ""
            os.environ["NO_PROXY"] = host
            os.environ["no_proxy"] = host
            self._client = clickhouse_connect.get_client(
                host=host,
                port=self.settings.clickhouse_port,
                username=self.settings.clickhouse_user,
                password=self.settings.clickhouse_password,
                database=self.settings.clickhouse_database,
                secure=self.settings.clickhouse_secure,
            )
        return self._client

    def ping(self) -> bool:
        result = self.query("SELECT 1 AS ok")
        return bool(result["rows"])

    def list_tables(self) -> list[str]:
        result = self.query(
            """
            SELECT concat(database, '.', name) AS full_name
            FROM system.tables
            WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
            ORDER BY database, name
            """
        )
        return [row["full_name"] for row in result["rows"]]

    def get_schema_catalog(self) -> list[ColumnInfo]:
        result = self.query(
            """
            SELECT database, table, name, type
            FROM system.columns
            WHERE database NOT IN ('system', 'information_schema', 'INFORMATION_SCHEMA')
            ORDER BY database, table, position
            """
        )
        return [
            ColumnInfo(
                database=row["database"],
                table=row["table"],
                name=row["name"],
                type=row["type"],
            )
            for row in result["rows"]
        ]

    def get_table_schema(self, table_name: str) -> list[ColumnInfo]:
        if "." in table_name:
            database_name, bare_table_name = table_name.split(".", 1)
            database_filter = f"database = {self._quote(database_name)} AND "
        else:
            database_filter = ""
            bare_table_name = table_name
        result = self.query(
            f"""
            SELECT database, table, name, type
            FROM system.columns
            WHERE {database_filter}table = {self._quote(bare_table_name)}
            ORDER BY position
            """
        )
        return [
            ColumnInfo(
                database=row["database"],
                table=row["table"],
                name=row["name"],
                type=row["type"],
            )
            for row in result["rows"]
        ]

    def query(self, sql: str) -> dict[str, Any]:
        sql = sql.strip().rstrip(";")
        if not sql.lower().startswith("select"):
            raise ValueError("Only SELECT queries are allowed")

        result = self._get_client().query(sql)
        rows = [dict(zip(result.column_names, row)) for row in result.result_rows]
        return {
            "columns": list(result.column_names),
            "rows": rows,
            "row_count": len(rows),
        }

    @staticmethod
    def _quote(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
