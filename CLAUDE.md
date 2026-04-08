# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make install        # pip install -e ".[dev]"
make run            # start Gradio UI at http://localhost:7860
make test           # run all tests
make test-unit      # run unit tests only
make test-coverage  # run tests with coverage report
make lint           # ruff + black --check + isort --check
make format         # black + isort (auto-fix)
make docker-build   # docker compose build
make docker-up      # docker compose up
make docker-down    # docker compose down
make setup-kb       # build FAISS vectorstores from PDFs

# Run a single test file / specific test
pytest tests/unit/test_planner.py
pytest tests/unit/test_planner.py::test_function_name
```

## Architecture

### Graph flow

```
START → planner → supervisor ⇄ specialists → synthesis → END
```

`graph.py` builds the StateGraph. The supervisor reads `state["next"]` (set by `route_supervisor()`) to decide which specialist runs next. All specialists loop back to the supervisor; only `synthesis_agent` routes to END.

**Agents and their roles:**
| Agent | Pattern | Key dependency |
|---|---|---|
| `planner_agent` | Structured output | Pydantic schema → plan steps |
| `supervisor_agent` | Structured output | Routes via `state["next"]` |
| `patient_data_agent` | ReAct | Neon MCP tools (SQL) |
| `cardiovascular_agent` | ReAct | FAISS + reranker RAG tool |
| `neurological_agent` | ReAct | FAISS + reranker RAG tool |
| `pharmacy_finder_agent` | ReAct | Google Maps MCP + custom tools |
| `synthesis_agent` | Plain LLM call | All prior messages in state |

### State

`state/schemas.py` defines the shared `State(TypedDict)`:
- `messages` — accumulated via `Annotated[list, add_messages]`
- `next` — supervisor's routing target
- `agents_called` — execution history list

### Agent patterns

**Planner / Supervisor (structured output):**
```python
llm.with_structured_output(Schema).invoke([("system", PROMPT), *state["messages"]])
return {"next": decision.next, "agents_called": [...]}
```

**Specialist agents (ReAct):**
```python
agent = create_react_agent(model=llm, tools=[...], prompt=PROMPT, checkpointer=MemorySaver())
result = agent.invoke({"messages": state["messages"]}, config={"configurable": {"thread_id": f".._{uuid4()}"}})
return {"messages": [result["messages"][-1]], "agents_called": [...]}
```

Each specialist uses a **unique `uuid4()` thread ID per invocation** to prevent stale `MemorySaver` checkpoints from carrying over broken tool call state across runs.

### RAG pipeline (two-stage)

`knowledge_bases/cardiovascular_kb.py` and `neurological_kb.py`:
1. **FAISS** retrieves `fetch_k=20` candidates by vector similarity
2. **CrossEncoderReranker** (`BAAI/bge-reranker-base`) scores all 20 and returns top `k=4`

```python
base_retriever = vectorstore.as_retriever(search_kwargs={"k": fetch_k})
reranker = CrossEncoderReranker(model=HuggingFaceCrossEncoder("BAAI/bge-reranker-base"), top_n=k)
return ContextualCompressionRetriever(base_compressor=reranker, base_retriever=base_retriever)
```

Vectorstores are cached with `@lru_cache(maxsize=1)`. They are auto-created from PDFs in `data/knowledge_bases/` if not already present in `data/knowledge_bases/vectorstores/`.

### MCP tools

Tools are loaded **eagerly at import time** from Smithery-hosted MCP servers:
- `mcp/neon_tools.py` — Neon PostgreSQL (manual JSON-RPC via `httpx`)
- `mcp/google_map_tools.py` — Google Maps (`langchain-mcp-adapters`, `MultiServerMCPClient`)

Google Maps tools are loaded with a graceful fallback: if the MCP server is unreachable, `google_map_tools` is an empty list and the pharmacy agent falls back to non-MCP tools (`get_coordinates_batch`, `street_distance_osrm`).

The async→sync bridge used for MCP tools:
```python
def _run_async(coro):
    try:
        asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)
```

## Key conventions

**Settings:** Always access via the module-level singleton `from ..config import settings`. Never instantiate `Settings()` directly.

**LLM:** Always use `get_llm(temperature=0, model="gpt-5.2")` from `config/llm_config.py`. This applies SSL patches and uses `OPENAI_BASE_URL` for corporate proxy support.

**Imports:** All intra-package imports use relative paths (`from ..config import get_llm`).

**SSL bypass:** `llm_config.py` patches `ssl.create_default_context` and `requests.Session.request` at module load time for corporate proxy compatibility. This applies globally once `get_llm()` or `get_embeddings()` is called.

**LangSmith tracing:** Enabled by setting `LANGCHAIN_TRACING_V2=true` and `LANGSMITH_API_KEY` in `.env`. `setup_langsmith()` is called at app startup; LangChain/LangGraph pick up the env vars automatically.
