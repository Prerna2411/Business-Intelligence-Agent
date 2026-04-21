from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make project packages importable when Streamlit runs this file directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.service import BIService


def ensure_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def render_chart(dataframe: pd.DataFrame, visualization: dict) -> None:
    chart_type = visualization.get("chart_type")
    x_axis = visualization.get("x_axis")
    y_axis = visualization.get("y_axis")
    other_columns = [column for column in dataframe.columns if column not in {x_axis, y_axis}]

    if chart_type == "line" and x_axis in dataframe.columns and y_axis in dataframe.columns:
        if other_columns:
            chart_df = dataframe.pivot_table(index=x_axis, columns=other_columns[0], values=y_axis, aggfunc="mean")
        else:
            chart_df = dataframe.set_index(x_axis)[[y_axis]]
        st.line_chart(chart_df)
        return
    if chart_type == "bar" and x_axis in dataframe.columns and y_axis in dataframe.columns:
        if other_columns:
            chart_df = dataframe.pivot_table(index=x_axis, columns=other_columns[0], values=y_axis, aggfunc="mean")
        else:
            chart_df = dataframe.set_index(x_axis)[[y_axis]]
        st.bar_chart(chart_df)
        return
    if chart_type == "scatter" and x_axis in dataframe.columns and y_axis in dataframe.columns:
        st.scatter_chart(dataframe[[x_axis, y_axis]])
        return

    st.info("No native chart could be rendered for this result shape, so the table below is the primary output.")


st.set_page_config(page_title="BI Agent", layout="wide")
st.title("Business Intelligence Agent")
st.caption("Ask DB questions and get schema-aware SQL, ClickHouse results, charts, and a Groq-generated summary.")

service = BIService()
runtime = service.runtime_status()
if "document_index_status" not in st.session_state:
    st.session_state["document_index_status"] = []


def get_indexed_documents() -> list[dict]:
    if hasattr(service, "list_documents"):
        try:
            return service.list_documents()
        except Exception:
            return []
    return []

with st.sidebar:
    st.subheader("Runtime")
    st.write(f"Groq configured: `{runtime.get('has_api_key', False)}`")
    st.write(f"ClickHouse configured: `{runtime.get('has_database', False)}`")
    st.write(f"Chroma available: `{runtime.get('has_chroma', False)}`")
    st.write(f"Model: `{runtime.get('groq_model', 'unknown')}`")
    st.write(runtime.get("reason", "Runtime status unavailable."))

    st.subheader("Document RAG")
    uploaded_files = st.file_uploader(
        "Upload PDF, DOCX, or TXT files",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
    )
    if st.button("Index uploaded documents", use_container_width=True):
        if not uploaded_files:
            st.session_state["document_index_status"] = [{"message": "No files selected.", "status": "skipped"}]
        elif not hasattr(service, "ingest_documents"):
            st.session_state["document_index_status"] = [{"message": "Document indexing is unavailable until the app is restarted with the updated BIService.", "status": "error"}]
        else:
            st.session_state["document_index_status"] = service.ingest_documents(
                [(uploaded_file.name, uploaded_file.getvalue()) for uploaded_file in uploaded_files]
            )
    for item in st.session_state["document_index_status"]:
        if item.get("status") == "indexed":
            st.success(item.get("message", "Indexed"))
        else:
            st.warning(item.get("message", "No update"))

    indexed_docs = get_indexed_documents()
    st.write(f"Indexed documents: `{len(indexed_docs)}`")
    for doc in indexed_docs:
        st.caption(doc["file_name"])

with st.form("bi-question-form"):
    question = st.text_area(
        "Ask a question about your ClickHouse data",
        placeholder="Show monthly revenue trend by region for the last 6 months",
        height=110,
    )
    use_rag = st.checkbox(
        "Use uploaded documents (Hybrid RAG)",
        value=bool(get_indexed_documents()),
        disabled=not bool(get_indexed_documents()),
    )
    submitted = st.form_submit_button("Run analysis", use_container_width=True)

if submitted and question.strip():
    with st.spinner("Planning, grounding on schema, generating SQL, executing ClickHouse query, and summarizing..."):
        try:
            result = service.ask(question.strip(), use_rag=use_rag)
        except TypeError:
            result = service.ask(question.strip())

    sql_payload = result.get("sql") or {}
    analysis = result.get("analysis") or {}
    visualization = result.get("visualization") or {}
    reflection = result.get("reflection") or {}
    result_payload = sql_payload.get("result") or {}
    dataframe = pd.DataFrame(result_payload.get("rows", []))

    st.subheader("Summary")
    st.write(analysis.get("summary", "No summary was produced."))

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Result Table")
        if dataframe.empty:
            st.info("The query returned no rows.")
        else:
            st.dataframe(dataframe, use_container_width=True)
    with col2:
        st.subheader("Visualization")
        st.caption(visualization.get("reason", ""))
        if dataframe.empty:
            st.info("A chart will appear here when the query returns rows.")
        else:
            render_chart(dataframe, visualization)

    st.subheader("Generated SQL")
    if sql_payload.get("sql"):
        st.code(sql_payload.get("sql", ""), language="sql")
    else:
        st.info("No SQL was generated for this document-grounded answer.")

    details_col1, details_col2 = st.columns(2)
    with details_col1:
        st.subheader("Schema Grounding")
        if result.get("rag"):
            citations = result["rag"].get("citations", [])
            if citations:
                st.dataframe(pd.DataFrame(citations), use_container_width=True)
            else:
                st.info("No document citations were available.")
        else:
            st.write("Selected tables:", sql_payload.get("selected_tables", []))
            selected_columns = sql_payload.get("selected_columns", [])
            if selected_columns:
                st.dataframe(pd.DataFrame(selected_columns), use_container_width=True)
            else:
                st.info("No columns were selected.")
    with details_col2:
        st.subheader("Checks")
        st.write("Confidence:", analysis.get("confidence", "unknown"))
        for insight in ensure_list(analysis.get("insights", [])):
            st.write(f"- {insight}")
        for follow_up in ensure_list(analysis.get("follow_ups", [])):
            st.write(f"- Follow-up: {follow_up}")
        if reflection.get("risks"):
            st.warning("\n".join(reflection["risks"]))

    with st.expander("Agent Details"):
        st.json(
            {
                "plan": result.get("plan"),
                "reflection": reflection,
                "runtime": result.get("runtime"),
                "conversation": result.get("conversation"),
            }
        )
