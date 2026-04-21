from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from backend.agents.planner import PlannerOutput
from backend.services.clickhouse_service import ClickHouseService, ColumnInfo
from backend.services.llm_service import LLMService


@dataclass
class SQLAgentOutput:
    sql: str
    rationale: str
    selected_tables: list[str] = field(default_factory=list)
    selected_columns: list[dict[str, str]] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sql": self.sql,
            "rationale": self.rationale,
            "selected_tables": self.selected_tables,
            "selected_columns": self.selected_columns,
            "result": self.result,
            "warnings": self.warnings,
            "error": self.error,
        }


class SQLAgent:
    def __init__(self, llm: LLMService, clickhouse: ClickHouseService) -> None:
        self.llm = llm
        self.clickhouse = clickhouse

    def run(self, question: str, plan: PlannerOutput) -> SQLAgentOutput:
        try:
            schema_catalog = self.clickhouse.get_schema_catalog()
        except Exception as exc:
            return SQLAgentOutput(
                sql="",
                rationale="Schema lookup failed before SQL generation.",
                warnings=["Unable to inspect ClickHouse schema."],
                error=str(exc),
            )

        query_pattern = self._infer_query_pattern(question)
        selected = self._select_relevant_columns(
            question=question,
            schema_catalog=schema_catalog,
            query_pattern=query_pattern,
        )
        selected_tables = sorted({f"{column.database}.{column.table}" for column in selected})
        fallback_sql = self._build_fallback_sql(
            question=question,
            plan=plan,
            selected=selected,
            query_pattern=query_pattern,
        )

        payload = self.llm.invoke_json(
            system_prompt=(
                "You are a senior ClickHouse SQL agent. "
                "Return strict JSON with keys sql, rationale, selected_tables, selected_columns, warnings. "
                "Use only read-only SELECT queries. Never reference columns outside the provided schema. "
                "Choose the query pattern that matches the business intent, not a generic time trend."
            ),
            user_prompt=self._build_generation_prompt(
                question=question,
                plan=plan,
                selected=selected,
                fallback_sql=fallback_sql,
                query_pattern=query_pattern,
            ),
            fallback={
                "sql": fallback_sql,
                "rationale": "Fallback SQL generated from semantic pattern detection over the grounded schema.",
                "selected_tables": selected_tables,
                "selected_columns": [column.to_dict() for column in selected],
                "warnings": [],
            },
        )
    
        sql = (payload.get("sql") or fallback_sql).strip().rstrip(";")
        if not sql.lower().startswith("select"):
            sql = fallback_sql
        sql = self._enforce_readable_product_label(sql=sql, selected=selected, query_pattern=query_pattern)
        sql = self._fix_having_clause_aliases(sql)
        
        try:
            result = self.clickhouse.query(sql)
            error = None
        except Exception as exc:
            result = {"columns": [], "rows": [], "row_count": 0}
            error = str(exc)

        return SQLAgentOutput(
            sql=sql,
            rationale=payload.get("rationale") or "SQL generated for the detected business question.",
            selected_tables=payload.get("selected_tables") or selected_tables,
            selected_columns=payload.get("selected_columns") or [column.to_dict() for column in selected],
            result=result,
            warnings=payload.get("warnings") or [],
            error=error,
        )

    def _enforce_readable_product_label(
        self,
        sql: str,
        selected: list[ColumnInfo],
        query_pattern: dict[str, Any],
    ) -> str:
        if query_pattern["entity"] != "product":
            return sql

        sql_lower = sql.lower()
        if "product_title" in sql_lower:
            return sql

        product_label = next(
            (
                column.name
                for column in selected
                if column.name.lower() in {"product_title", "product_name"}
            ),
            None,
        )
        if not product_label:
            return sql

        product_key_aliases = ["product_parent", "product_id", " as product_id", " as product_key"]
        if not any(alias in sql_lower for alias in product_key_aliases):
            return sql

        if " from " not in sql_lower:
            return sql

        select_prefix, remainder = sql.split("FROM", 1) if "FROM" in sql else sql.split("from", 1)
        if "select" not in select_prefix.lower():
            return sql

        return f"{select_prefix.rstrip()}, any({product_label}) AS product_title FROM{remainder}"

    def _infer_query_pattern(self, question: str) -> dict[str, Any]:
        tokens = {token.strip(" ,.?").lower() for token in question.split()}
        return {
            "needs_time_grain": bool(
                tokens & {"trend", "over", "monthly", "month", "daily", "day", "weekly", "quarterly", "quarter", "yearly", "year"}
            ),
            "needs_popularity": bool(tokens & {"popular", "popularity", "top", "most"}),
            "needs_low_rating": bool(tokens & {"poorly", "badly", "low", "worst", "negative"}),
            "needs_high_rating": bool(tokens & {"highest", "best", "top-rated"}),
            "entity": "product" if tokens & {"product", "products"} else "category" if "category" in tokens else "generic",
        }

    def _select_relevant_columns(
        self,
        question: str,
        schema_catalog: list[ColumnInfo],
        query_pattern: dict[str, Any],
    ) -> list[ColumnInfo]:
        tokens = {token.strip(" ,.?").lower() for token in question.split()}
        scored: list[tuple[int, ColumnInfo]] = []
        for column in schema_catalog:
            score = 0
            table_name = column.table.lower()
            column_name = column.name.lower()
            column_type = column.type.lower()

            for token in tokens:
                if token and token in column_name:
                    score += 5
                if token and token in table_name:
                    score += 3

            if query_pattern["entity"] == "product" and column_name in {"product_parent", "product_title", "product_id"}:
                score += 10
            if query_pattern["entity"] == "category" and "category" in column_name:
                score += 8
            if query_pattern["needs_popularity"] and any(hint in column_name for hint in {"review", "count", "votes"}):
                score += 8
            if query_pattern["needs_low_rating"] and any(hint in column_name for hint in {"rating", "score", "star"}):
                score += 8
            if query_pattern["needs_time_grain"] and any(hint in column_name for hint in {"date", "time", "month", "year"}):
                score += 6

            if any(metric in column_name for metric in {"revenue", "sales", "amount", "price", "profit", "count", "rating", "votes", "review"}):
                score += 2
            if "int" in column_type or "float" in column_type or "decimal" in column_type:
                score += 1
            scored.append((score, column))

        scored.sort(key=lambda item: (item[0], item[1].table, item[1].name), reverse=True)
        top = [column for score, column in scored if score > 0][:10]
        if top:
            return top
        return schema_catalog[:10]

    def _build_generation_prompt(
        self,
        question: str,
        plan: PlannerOutput,
        selected: list[ColumnInfo],
        fallback_sql: str,
        query_pattern: dict[str, Any],
    ) -> str:
        schema_lines = [
            f"- table={column.database}.{column.table}, column={column.name}, type={column.type}"
            for column in selected
        ]
        return (
            f"Question: {question}\n"
            f"Intent: {plan.intent}\n"
            f"Time range: {plan.time_range}\n"
            f"Derived query pattern: {query_pattern}\n"
            "Relevant schema:\n"
            f"{chr(10).join(schema_lines)}\n\n"
            "Requirements:\n"
            "- Prefer one table unless a join is clearly necessary.\n"
            "- Use aliases that are easy to read in a UI.\n"
            "- Do not group by time unless the user clearly asked for a trend over time.\n"
            "- For popularity questions, prefer COUNT(*) or review counts over unrelated sums unless votes were explicitly requested.\n"
            "- For poorly rated questions, use AVG on the rating column and HAVING filters when the business ask implies thresholds.\n"
            "- For product questions, group by a stable product identifier and include a readable product label when available.\n"
            "- If both popularity and poor rating are requested, produce a ranking/filter query by product, not a time series.\n"
            "- Use LIMIT 20 for ranked entity lists and LIMIT 200 for trends.\n"
            f"- If unsure, use this safe fallback SQL:\n{fallback_sql}\n"
        )

    def _build_fallback_sql(
        self,
        question: str,
        plan: PlannerOutput,
        selected: list[ColumnInfo],
        query_pattern: dict[str, Any],
    ) -> str:
        if not selected:
            return "SELECT 1 AS value LIMIT 1"

        tokens = {token.strip(" ,.?").lower() for token in question.split()}
        table = f"{selected[0].database}.{selected[0].table}"

        time_column = next(
            (column.name for column in selected if any(hint in column.name.lower() for hint in {"date", "time"})),
            None,
        )
        dimension_column = next(
            (column.name for column in selected if "string" in column.type.lower()),
            None,
        )
        rating_column = next(
            (column.name for column in selected if any(hint in column.name.lower() for hint in {"rating", "score", "star"})),
            None,
        )
        votes_column = next(
            (column.name for column in selected if any(hint in column.name.lower() for hint in {"votes", "helpful"})),
            None,
        )
        product_key = next(
            (column.name for column in selected if column.name.lower() in {"product_parent", "product_id"}),
            None,
        )
        product_label = next(
            (column.name for column in selected if column.name.lower() in {"product_title", "product_name"}),
            None,
        )
        category_column = next(
            (column.name for column in selected if "category" in column.name.lower()),
            None,
        )

        if query_pattern["entity"] == "product" and product_key:
            select_parts = [product_key]
            if product_label:
                select_parts.append(f"any({product_label}) AS product_title")
            select_parts.append("COUNT(*) AS total_reviews")
            if votes_column:
                select_parts.append(f"SUM({votes_column}) AS total_votes")
            if rating_column:
                select_parts.append(f"AVG({rating_column}) AS avg_rating")

            sql_parts = [
                "SELECT " + ", ".join(select_parts),
                f"FROM {table}",
                f"GROUP BY {product_key}",
            ]

            having_parts = []
            if query_pattern["needs_popularity"]:
                having_parts.append("total_reviews > 100")
            if query_pattern["needs_low_rating"] and rating_column:
                having_parts.append("avg_rating < 3")
            if query_pattern["needs_high_rating"] and rating_column:
                having_parts.append("avg_rating >= 4")
            if having_parts:
                sql_parts.append("HAVING " + " AND ".join(having_parts))

            order_parts = []
            if query_pattern["needs_popularity"]:
                order_parts.append("total_reviews DESC")
            if votes_column:
                order_parts.append("total_votes DESC")
            if query_pattern["needs_low_rating"] and rating_column and not query_pattern["needs_popularity"]:
                order_parts.append("avg_rating ASC")
            if query_pattern["needs_high_rating"] and rating_column and not query_pattern["needs_popularity"]:
                order_parts.append("avg_rating DESC")
            if order_parts:
                sql_parts.append("ORDER BY " + ", ".join(order_parts))
            sql_parts.append("LIMIT 20")
            return " ".join(sql_parts)

        if query_pattern["needs_time_grain"] and time_column:
            period_expr = (
                f"toStartOfMonth({time_column})" if {"month", "monthly"} & tokens
                else f"toStartOfYear({time_column})" if {"year", "yearly", "annual"} & tokens
                else f"toDate({time_column})"
            )
            grouping_dimension = category_column or dimension_column
            metric_expr = "COUNT(*) AS total_reviews"
            if rating_column and {"average", "avg", "mean"} & tokens:
                metric_expr = f"AVG({rating_column}) AS avg_rating"
            elif votes_column and "votes" in tokens:
                metric_expr = f"SUM({votes_column}) AS total_votes"

            dimension_sql = f", {grouping_dimension}" if grouping_dimension else ""
            group_by = f"GROUP BY period{', ' + grouping_dimension if grouping_dimension else ''}"
            order_by = f"ORDER BY period{', ' + grouping_dimension if grouping_dimension else ''}"
            return (
                f"SELECT {period_expr} AS period{dimension_sql}, {metric_expr} "
                f"FROM {table} "
                f"{group_by} "
                f"{order_by} "
            
            )

        if category_column and rating_column and query_pattern["needs_low_rating"]:
            return (
                f"SELECT {category_column} AS category, COUNT(*) AS total_reviews, AVG({rating_column}) AS avg_rating "
                f"FROM {table} "
                "GROUP BY category "
                "HAVING total_reviews > 20 AND avg_rating < 3 "
                "ORDER BY total_reviews DESC "
                "LIMIT 20"
            )

        if dimension_column:
            metric_expr = "COUNT(*) AS total_count"
            if votes_column and "votes" in tokens:
                metric_expr = f"SUM({votes_column}) AS total_votes"
            elif rating_column and {"average", "avg", "mean"} & tokens:
                metric_expr = f"AVG({rating_column}) AS avg_rating"
            return (
                f"SELECT {dimension_column} AS category, {metric_expr} "
                f"FROM {table} "
                "GROUP BY category "
                "ORDER BY 2 DESC "
                "LIMIT 20"
            )

        return f"SELECT * FROM {table} LIMIT 50"
    def _fix_having_clause_aliases(self, sql: str) -> str:
        sql_lower = sql.lower()

        if "having" not in sql_lower:
            return sql

        # Replace aggregate functions with aliases
        sql = sql.replace("COUNT(*)", "total_reviews")
        sql = sql.replace("AVG(star_rating)", "avg_rating")

        return sql
