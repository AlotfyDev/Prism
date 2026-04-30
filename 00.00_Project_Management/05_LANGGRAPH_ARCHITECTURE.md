# 05_LANGGRAPH_ARCHITECTURE — Prism Orchestration Layer

## Decision

> **LangGraph** is the foundational orchestration engine for Prism. All stages (1-4) use LangGraph `StateGraph` for workflow management.
>
> **LangSmith** is permanently excluded (cloud-only). Local observability via structured logging + SQLite.
>
> **All data stays local 100%.**

---

## Architectural Mapping

### ProcessingUnit → LangGraph Node

Every `ProcessingUnit` maps directly to a LangGraph node:

```python
from langgraph.graph import StateGraph
from pydantic import BaseModel

class PrismState(BaseModel):
    # Stage 1
    stage1_input: Stage1Input | None = None
    stage1_output: Stage1Output | None = None

    # Stage 2
    stage2_output: Stage2Output | None = None

    # Stage 3
    stage3_output: Stage3Output | None = None
    semantic_results: dict[str, MiniPG] = {}  # Layer ID → MiniPG

    # Stage 4
    stage4_output: Stage4Output | None = None
    global_pg: GlobalPG | None = None

    # Cross-cutting
    validation_reports: list[ValidationReport] = []
    errors: list[str] = []
    current_stage: str = "init"
```

### Node Wrapper Pattern

```python
class PrismNode:
    """Wraps any ProcessingUnit into a LangGraph-compatible node function."""

    def __init__(self, unit: ProcessingUnit, validator: ValidationUnit):
        self.unit = unit
        self.validator = validator

    def __call__(self, state: PrismState) -> dict:
        # 1. Extract input from state
        input_data = self._extract_input(state)

        # 2. Validate input
        valid, msg = self.validator.validate_input(input_data)
        if not valid:
            return {"errors": [f"{self.unit.name()} input validation failed: {msg}"]}

        # 3. Process
        config = self._get_config(state)
        output = self.unit.process(input_data, config)

        # 4. Validate output
        valid, msg = self.validator.validate_output(output)
        if not valid:
            return {"errors": [f"{self.unit.name()} output validation failed: {msg}"]}

        # 5. Return state update
        return self._map_output(output)
```

---

## Graph Topology

```
┌──────────────┐
│    START     │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────────┐
│  tokenize    │────→│  validate_v1     │
│  (Stage 1)   │     │  (V1 checks)     │
└──────────────┘     └────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    │  passed?          │
                    └─────────┬─────────┘
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼ (halt)
┌──────────────┐  Yes              ┌──────────────────┐
│  topology    │                  │     HALT           │
│  (Stage 2)   │                  │  (log errors)     │
└──────┬───────┘                  └──────────────────┘
       │
       ▼
┌──────────────┐     ┌──────────────────┐
│  validate_v2 │────→│  passed?          │
│  (V2 checks) │     └────────┬─────────┘
└──────────────┘              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
┌──────────────────────────────────────────────────────────────┐
│  fan_out_layers                                              │
│  (Splits state by discovered physical layers)                │
└──────┬───────┬───────┬───────────────────────────────────────┘
       │       │       │
       ▼       ▼       ▼
┌──────────┐┌──────────┐┌──────────┐
│analyze_1 ││analyze_2 ││analyze_N │  ← PARALLEL EXECUTION
│(Stage 3) ││(Stage 3) ││(Stage 3) │
└────┬─────┘└────┬─────┘└────┬─────┘
     │           │           │
     ▼           ▼           ▼
┌──────────┐┌──────────┐┌──────────┐
│validate_1││validate_2││validate_N│  ← PER-LAYER VALIDATION (V3)
└────┬─────┘└────┬─────┘└────┬─────┘
     │           │           │
     └─────┬─────┘─────┬─────┘
           │           │
           ▼           ▼
┌──────────────────────────────────────────────────────────────┐
│  fan_in_layers                                               │
│  (Collects all MiniPGs → stage3_output)                      │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  aggregate   │────→│  validate_v4     │────→│   END        │
│  (Stage 4)   │     │  (V4 checks)     │     │ (GlobalPG)   │
└──────────────┘     └──────────────────┘     └──────────────┘
```

---

## Conditional Routing (3-Tier Cascade)

Each Processing Unit that has fallback tiers uses conditional edges:

```python
def route_entity_extraction(state: PrismState) -> str:
    """Route to the best available entity extractor."""
    config = state.config.entity_extractor

    if config == "spacy" and _spacy_available():
        return "extract_spacy"
    elif config == "gliner" and _gliner_available():
        return "extract_gliner"
    elif config == "stanza" and _stanza_available():
        return "extract_stanza"
    elif config in ("spacy", "gliner", "stanza"):
        return "extract_llm_fallback"  # LLM tier
    elif config == "llm":
        return "extract_llm_fallback"
    else:
        return "extract_llm_fallback"

# In graph:
graph.add_conditional_edges(
    "route_entity_extraction",
    route_entity_extraction,
    {
        "extract_spacy": "extract_spacy",
        "extract_gliner": "extract_gliner",
        "extract_stanza": "extract_stanza",
        "extract_llm_fallback": "extract_llm_fallback",
    }
)

# All extractors converge to same validation:
graph.add_edge("extract_spacy", "validate_entities")
graph.add_edge("extract_gliner", "validate_entities")
graph.add_edge("extract_stanza", "validate_entities")
graph.add_edge("extract_llm_fallback", "validate_entities")
```

---

## Recursion (Sub-Component Processing)

LangGraph supports recursion via `__recurse` flag:

```python
def route_recursion(state: PrismState) -> str:
    """Check if sub-components need processing."""
    if state.current_depth >= state.config.max_recursion_depth:
        return "merge_results"

    pending = state.pending_subcomponents
    if not pending:
        return "merge_results"

    return "analyze_subcomponent"

# Graph structure:
graph.add_node("analyze_subcomponent", analyze_layer_node)
graph.add_node("check_subcomponents", check_subcomponents_node)
graph.add_node("merge_results", merge_results_node)

graph.add_edge("analyze_subcomponent", "check_subcomponents")
graph.add_conditional_edges(
    "check_subcomponents",
    route_recursion,
    {
        "analyze_subcomponent": "analyze_subcomponent",  # ← Recurse
        "merge_results": "merge_results",
    }
)
```

---

## Parallelism (Stage 3 Map-Reduce)

LangGraph's `Send` API for dynamic parallelism:

```python
from langgraph.constants import Send

def fan_out_layers(state: PrismState):
    """Dynamically create parallel tasks for each discovered layer."""
    for layer_id, component in state.stage2_output.discovered_layers.items():
        yield Send("analyze_layer", {"layer_id": layer_id, "component": component})

def fan_in_layers(results: list[MiniPG]) -> dict:
    """Collect all parallel results into state."""
    mini_pgs = {r.layer_id: r for r in results}
    return {"stage3_output": Stage3Output(mini_pgs=mini_pgs, semantic_tree={})}

# Graph:
graph.add_node("analyze_layer", analyze_layer_node)
graph.add_node("merge_layer_results", fan_in_layers)

# Dynamic fan-out:
graph.add_conditional_edges(
    "route_to_layers",
    fan_out_layers,
    ["analyze_layer"]  # All Sends go to this node
)

# All parallel results converge:
graph.add_edge("analyze_layer", "merge_layer_results")
```

---

## Checkpointing (Local SQLite)

```python
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# Local SQLite only — no cloud, no external service
conn = sqlite3.connect("data/prism_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

# Usage:
graph = workflow.compile(checkpointer=checkpointer)

# Run with thread ID (document ID):
result = graph.invoke(
    {"stage1_input": Stage1Input(source="doc.md", source_type="md")},
    config={"configurable": {"thread_id": "document_001"}}
)

# Resume from checkpoint (if pipeline was interrupted):
result = graph.invoke(None, config={"configurable": {"thread_id": "document_001"}})
```

---

## LLM Provider Cascade (Local-Only)

```python
class LLMRouter:
    """Routes LLM requests through provider priority chain."""

    def __init__(self, config: PipelineConfig):
        self.providers = [
            OpenCodeProvider(),    # Priority 1
            KiloCodeProvider(),   # Priority 2
            ClineProvider(),      # Priority 3
            OpenRouterProvider(), # Priority 4
            CodexProvider(),      # Priority 5 (last resort)
        ]

    async def complete(self, prompt: str, system_prompt: str = "") -> str:
        last_error = None
        for provider in self.providers:
            try:
                return await provider.complete(prompt, system_prompt)
            except Exception as e:
                last_error = e
                continue
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
```

---

## Error Handling & Degradation

```python
def handle_unit_failure(state: PrismState, error: str, unit_name: str) -> str:
    """Determine next step based on failure severity."""
    config = state.config

    # Check if fallback tier exists
    if config.has_fallback(unit_name):
        # Route to next tier
        return config.get_fallback(unit_name)

    # No fallback → halt
    return "halt"

# In graph:
graph.add_conditional_edges(
    "handle_failure",
    lambda state: handle_unit_failure(state, state.errors[-1], state.current_stage),
    {
        "extract_gliner": "extract_gliner",    # Fallback tier
        "extract_stanza": "extract_stanza",    # Another fallback
        "extract_llm": "extract_llm",          # Last resort
        "halt": "halt",                        # No fallback available
    }
)
```

---

## Observability (Local — No LangSmith)

```python
import structlog
from dataclasses import dataclass

logger = structlog.get_logger()

@dataclass
class PipelineMetrics:
    stage: str
    duration_ms: float
    tokens_processed: int
    llm_calls: int
    llm_cost: float  # Estimated
    errors: list[str]
    timestamp: str

# SQLite metrics store
class LocalMetricsStore:
    def __init__(self, db_path: str = "data/prism_metrics.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()

    def record(self, metrics: PipelineMetrics):
        self.conn.execute(
            "INSERT INTO metrics (stage, duration_ms, tokens, llm_calls, errors, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (metrics.stage, metrics.duration_ms, metrics.tokens_processed,
             metrics.llm_calls, str(metrics.errors), metrics.timestamp)
        )
        self.conn.commit()
```

---

## Dependency Requirements

```toml
# pyproject.toml — Prism dependencies

[project]
dependencies = [
    # Core orchestration
    "langgraph>=0.2.0",          # Workflow engine (local, open source)
    "pydantic>=2.0",             # Schema validation

    # NLP Tier 1
    "spacy>=3.7",
    "stanza>=1.7",
    "nltk>=3.8",
    "gliner>=0.2",               # Zero-shot NER

    # Embeddings (bundled models)
    "fastembed>=0.3",            # ONNX embedding engine
    "onnxruntime>=1.16",         # ONNX runtime (CPU)

    # Graph
    "networkx>=3.2",             # Property graph storage

    # Utilities
    "structlog>=23.1",           # Structured logging
    "pyyaml>=6.0",               # Config files
    "markdown-it-py>=3.0",       # Markdown AST parsing
]
```

---

## Summary: Why LangGraph from Day 1

| Reason | Impact |
|--------|--------|
| **Stage 3 parallelism** | `fan-out/fan-in` for per-layer analysis — no custom thread pool code |
| **Stage 4 DAG** | Declarative parallel sub-steps — no manual dependency tracking |
| **3-Tier cascade** | `conditional_edges` replace nested if/else chains |
| **Recursion** | Built-in recursion limits and state management |
| **Checkpointing** | SQLite checkpointer — resume interrupted pipelines |
| **Error routing** | Conditional edges route to fallback tiers automatically |
| **Visual graph** | `graph.get_graph().draw_mermaid()` — auto-generated pipeline diagram |
| **Testing** | `graph.invoke()` with mock state — no custom test harness needed |
| **Local 100%** | Open source, no cloud dependencies |
