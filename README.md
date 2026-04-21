# Business Intelligence Agent

An agentic BI application for answering questions from:

- `ClickHouse` warehouse data through schema-aware SQL generation
- uploaded `PDF / DOCX / TXT / MD` files through hybrid RAG with persistent Chroma storage

It combines a `Streamlit` frontend, `FastAPI` backend, `Groq`-powered reasoning, SQL planning, result summarization, visualization selection, and document retrieval.

## Highlights

- Schema-aware SQL generation for ClickHouse
- Agentic workflow for planning, SQL generation, analysis, reflection, and visualization
- Hybrid RAG using:
  - dense retrieval with ChromaDB
  - sparse keyword retrieval
  - score fusion
- Persistent local storage for:
  - uploaded documents
  - Chroma vectors
  - sparse retrieval index
- Streamlit UI for:
  - asking BI questions
  - viewing result tables
  - viewing generated SQL
  - uploading and indexing documents

## Demo Use Cases

### Database Questions

- `Show top 10 most reviewed products`
- `Which popular but poorly rated products should we investigate?`
- `Which marketplace has the highest average star rating?`

### Document Questions

- `Summarize the uploaded report`
- `What does the uploaded PDF say about customer churn?`
- `Give me the page references for pricing terms in the uploaded documents`

## How It Works

### SQL / Warehouse Flow

1. classify the question
2. inspect ClickHouse schema
3. infer the intended SQL pattern
4. generate SQL with Groq, with deterministic fallback logic
5. execute SQL against ClickHouse
6. summarize results
7. choose a chart based on returned columns
8. run a reflection check

### Document / RAG Flow

1. upload documents from the Streamlit sidebar
2. parse and chunk the text
3. create embeddings
4. persist vectors to ChromaDB
5. persist sparse keyword index to disk
6. retrieve relevant chunks with hybrid retrieval
7. answer only from retrieved context

## Architecture

### Core App Layers

- `frontend/streamlit_app.py`
  - Streamlit UI
  - file upload and indexing
  - question input and result rendering

- `backend/app/main.py`
  - FastAPI entrypoint

- `services/service.py`
  - main application service
  - routes questions into SQL or RAG behavior

- `backend/core/orchestrator.py`
  - wires together the SQL-focused agent graph

### Agents

- `planner.py`
  - identifies the likely question intent

- `sql_agent.py`
  - grounds on schema and generates ClickHouse SQL

- `analysis.py`
  - converts query output into a business summary

- `visulaization_agent.py`
  - selects chart type and axes

- `reflection_agent.py`
  - performs lightweight quality checks

- `rag_agent.py`
  - answers questions from uploaded documents

### Retrieval Layer

- `memory/document_store.py`
  - persistent Chroma-backed vector storage

- `memory/sparse_index.py`
  - sparse keyword retrieval index

- `memory/hybrid_retriever.py`
  - dense + sparse retrieval fusion

- `rag/ingest.py`
  - document ingestion pipeline

- `rag/chunker.py`
  - chunking logic

- `rag/parsers/`
  - PDF / DOCX / text parsing

## Project Structure

```text
backend/
  agents/
  api/
  app/
  core/
  services/

frontend/
  streamlit_app.py

graph/
  nodes.py
  routes.py
  state.py
  workflow.py

memory/
  document_store.py
  hybrid_retriever.py
  retriever.py
  short_term.py
  sparse_index.py
  vector_store.py

rag/
  chunker.py
  ingest.py
  schemas.py
  parsers/
    pdf_parser.py
    docx_parser.py
    text_parser.py

services/
  service.py

tools/
  inspect_rag_store.py
  rebuild_rag_index.py

data/
  uploads/
  vector_store/
  sparse_index/

tests/
```

## Tech Stack

- Python 3.13
- Streamlit
- FastAPI
- LangGraph
- ClickHouse
- Groq API
- ChromaDB
- Pandas

## Environment Variables

Create a `.env` file in the project root.

```.env
CLICKHOUSE_HOST="your-clickhouse-host"
CLICKHOUSE_PORT="8443"
CLICKHOUSE_USER="your-clickhouse-user"
CLICKHOUSE_PASSWORD="your-clickhouse-password"
CLICKHOUSE_DATABASE="default"
CLICKHOUSE_SECURE="true"

GROQ_API_KEY="your-groq-api-key"
GROQ_MODEL="llama-3.3-70b-versatile"

CHROMA_PATH="data/vector_store/chroma"
UPLOADS_PATH="data/uploads"
SPARSE_INDEX_PATH="data/sparse_index/index.json"
RAG_CHUNK_SIZE="800"
RAG_CHUNK_OVERLAP="120"
RAG_TOP_K="5"
```

## Local Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit Frontend

```bash
streamlit run frontend/streamlit_app.py
```

### 3. Run the FastAPI Backend

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 4. Run Tests

```bash
pytest tests -q
```

## Docker

The repo includes:

- `Dockerfile`
  - builds the shared application image

- `docker-compose.yml`
  - runs:
    - `api` service on port `8000`
    - `frontend` service on port `8501`

Start both services:

```bash
docker compose up --build
```

Available endpoints:

- Streamlit UI: `http://localhost:8501`
- FastAPI API: `http://localhost:8000`

## CI

GitHub Actions workflow:

- `.github/workflows/main.yml`

The pipeline currently:

- installs dependencies
- runs tests
- verifies Docker image build

## Persistent Runtime Data

Generated runtime data is stored in:

- `data/uploads/`
  - uploaded original files

- `data/vector_store/chroma/`
  - persistent Chroma vectors

- `data/sparse_index/`
  - persisted sparse retrieval index

These directories are ignored by Git.

## Tools

Helper scripts in `tools/`:

- `rebuild_rag_index.py`
  - re-index files already present in `data/uploads`

- `inspect_rag_store.py`
  - inspect indexed document IDs and file names

## Current Limitations

- Streamlit currently imports the service directly instead of calling FastAPI over HTTP
- mixed SQL + RAG synthesis is scaffolded but not yet a full combined reasoning workflow
- the local embedding service is lightweight and deterministic, not a production embedding model
- document indexing requires `chromadb` to be installed in the runtime environment

## Roadmap

- route frontend requests through FastAPI instead of direct service imports
- add reranking for document retrieval
- improve mixed SQL + RAG synthesis
- add richer document citations in the UI
- add benchmark-based evaluation for SQL accuracy and RAG faithfulness

## License

Add your preferred license before publishing publicly.
