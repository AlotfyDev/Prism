# Stage 2 LangGraph Subgraph — Architectural Design

> Decision Date: 2026-05-02
> Status: DESIGN COMPLETE — Phase 5 (depends on Pipeline abstraction being implemented first)
> Location: `prism/stage2/graph/`
> Dependency: Requires `prism/stage2/protocols.py` and `prism/stage2/pipeline_models.py` (Phase 1-2)

---

## 1. Problem Statement

The current top-level LangGraph architecture (per `05_LANGGRAPH_ARCHITECTURE.md`) is too flat:

```
Flat: START → tokenize → validate_v1 → topology → validate_v2 → fan_out → ...
```

Here `topology` is **one node** that internally calls 6 ProcessingUnits sequentially.
This means:

- **No checkpointing between internal steps** — if TokenSpanMapper fails, you can't resume from ComponentMapper
- **No conditional routing inside the node** — can't route to fallback implementations
- **No visibility** — LangGraph can't observe individual step progress
- **No parallelism preparation** — Stage 3 fan-out needs Stage 2 output as individual layer units

### Solution: Subgraph Architecture

```
Top-Level:
  START → Stage1_Subgraph → Stage2_Subgraph → Stage3_Subgraph → Stage4_Subgraph → END

Stage2_Subgraph (internal):
  START → parse → validate_parser → classify → validate_classifier
    → build_hierarchy → validate_hierarchy → map_components → validate_mapper
    → map_tokens → validate_tokens → build_topology → validate_topology → END
                                              ↓
                                           HALT (on any validation failure)
```

Each step inside the subgraph is:
- A LangGraph node (checkpointable)
- Has conditional edges (validation pass/fail)
- Supports fallback routing (swappable implementations via PipelineConfig)
- Produces structured state for the next step

---

## 2. FileSystem Structure

```
prism/stage2/graph/
├── __init__.py     → build_stage2_subgraph(), get_stage2_state_class()
├── state.py        → Stage2GraphState (Pydantic state model)
├── nodes.py        → create_node(unit, step_name) + individual node functions
├── edges.py        → route_validation(), route_fallback() conditional edges
├── builder.py      → assemble StateGraph: add nodes, edges, conditional edges
└── config.py       → GraphConfig (extends Stage2PipelineConfig with graph-specific options)

tests/
├── test_stage2_subgraph.py   → LangGraph subgraph integration tests
└── test_stage2_graph_state.py → State model tests
```

---

## 3. State Model (`state.py`)

### Design Principle

Pydantic model that accumulates results from each pipeline step.
Every field is optional (except `source_text`) — populated progressively.

```python
from pydantic import BaseModel, Field
from prism.schemas.physical import (
    MarkdownNode,
    DetectedLayersReport,
    HierarchyTree,
    PhysicalComponent,
    Stage2Output,
)
from prism.stage2.pipeline_models import (
    ParserOutput,
    MapperOutput,
    TokenSpanOutput,
)


class Stage2GraphState(BaseModel):
    """Accumulated state for Stage 2 LangGraph subgraph.

    Each pipeline step reads from and writes to this state.
    Fields are populated progressively as the graph executes.
    """

    # Input (from Stage 1)
    source_text: str = Field(default="", description="Original Markdown source")

    # Step 1: Parser
    nodes: list[MarkdownNode] = Field(default_factory=list, description="AST root nodes")

    # Step 2: Classifier
    report: DetectedLayersReport | None = Field(default=None, description="Layer detection report")

    # Step 3: HierarchyBuilder
    tree: HierarchyTree | None = Field(default=None, description="Component hierarchy tree")

    # Step 4: ComponentMapper
    components: list[PhysicalComponent] = Field(default_factory=list, description="Typed components")

    # Step 5: TokenSpanMapper
    token_mapping: dict[str, list[str]] = Field(
        default_factory=dict,
        description="component_id -> list of global token IDs",
    )

    # Step 6: TopologyBuilder (final output)
    stage2_output: Stage2Output | None = Field(default=None, description="Final Stage 2 output")

    # Cross-cutting
    errors: list[str] = Field(default_factory=list, description="Accumulated errors")
    current_step: str = Field(default="init", description="Current pipeline step name")
    retry_count: dict[str, int] = Field(default_factory=dict, description="Retry count per step")

    def has_error(self) -> bool:
        return len(self.errors) > 0

    def last_error(self) -> str | None:
        return self.errors[-1] if self.errors else None
```

---

## 4. Node Wrappers (`nodes.py`)

### Design Principle

Each node is a function `state: Stage2GraphState -> dict[str, Any]` that:
1. Reads required input from state
2. Calls the ProcessingUnit's `process()` method
3. Validates output
4. Returns state update dict

### Node Creator Pattern

```python
from typing import Any, Callable
from prism.stage2.graph.state import Stage2GraphState
from prism.stage2.protocols import (
    IParser, IClassifier, IHierarchyBuilder,
    IComponentMapper, ITokenSpanMapper, ITopologyBuilder,
)


def create_parse_node(parser: IParser) -> Callable[[Stage2GraphState], dict]:
    """Creates a LangGraph node that wraps an IParser implementation."""
    def parse_node(state: Stage2GraphState) -> dict[str, Any]:
        from prism.schemas.token import Stage1Output
        input_data = Stage1Output(source_text=state.source_text)
        output = parser.process(input_data)
        return {
            "nodes": output.nodes,
            "current_step": "parsed",
        }
    return parse_node


def create_classify_node(classifier: IClassifier) -> Callable[[Stage2GraphState], dict]:
    """Creates a LangGraph node that wraps an IClassifier implementation."""
    def classify_node(state: Stage2GraphState) -> dict[str, Any]:
        from prism.stage2.pipeline_models import ClassifierInput
        input_data = ClassifierInput(nodes=state.nodes, source_text=state.source_text)
        output = classifier.process(input_data)
        return {
            "report": output,
            "current_step": "classified",
        }
    return classify_node


def create_hierarchy_node(builder: IHierarchyBuilder) -> Callable[[Stage2GraphState], dict]:
    def hierarchy_node(state: Stage2GraphState) -> dict[str, Any]:
        from prism.stage2.pipeline_models import HierarchyInput
        input_data = HierarchyInput(report=state.report)
        output = builder.process(input_data)
        return {
            "tree": output,
            "current_step": "hierarchy_built",
        }
    return hierarchy_node


def create_mapper_node(mapper: IComponentMapper) -> Callable[[Stage2GraphState], dict]:
    def mapper_node(state: Stage2GraphState) -> dict[str, Any]:
        from prism.stage2.pipeline_models import MapperInput
        input_data = MapperInput(tree=state.tree)
        output = mapper.process(input_data)
        return {
            "components": output.components,
            "current_step": "components_mapped",
        }
    return mapper_node


def create_token_span_node(span_mapper: ITokenSpanMapper) -> Callable[[Stage2GraphState], dict]:
    def token_span_node(state: Stage2GraphState) -> dict[str, Any]:
        from prism.stage2.pipeline_models import TokenSpanInput
        from prism.schemas.token import Stage1Output
        input_data = TokenSpanInput(
            components=state.components,
            stage1_output=Stage1Output(source_text=state.source_text),
        )
        output = span_mapper.process(input_data)
        return {
            "token_mapping": output.component_to_tokens,
            "current_step": "tokens_mapped",
        }
    return token_span_node


def create_topology_node(builder: ITopologyBuilder) -> Callable[[Stage2GraphState], dict]:
    def topology_node(state: Stage2GraphState) -> dict[str, Any]:
        from prism.stage2.pipeline_models import TopologyInput
        input_data = TopologyInput(
            components=state.components,
            token_mapping=state.token_mapping,
        )
        output = builder.process(input_data)
        return {
            "stage2_output": output,
            "current_step": "topology_built",
        }
    return topology_node
```

### Validation Nodes

```python
def create_validation_node(
    step_name: str,
    unit: IParser | IClassifier | IHierarchyBuilder | IComponentMapper | ITokenSpanMapper | ITopologyBuilder,
    input_extractor: Callable[[Stage2GraphState], Any],
    output_extractor: Callable[[Stage2GraphState], Any],
) -> Callable[[Stage2GraphState], dict]:
    """Creates a validation node that checks the previous step's output."""
    def validation_node(state: Stage2GraphState) -> dict[str, Any]:
        input_data = input_extractor(state)
        output_data = output_extractor(state)

        valid, msg = unit.validate_input(input_data)
        if not valid:
            return {
                "errors": state.errors + [f"{step_name} input validation failed: {msg}"],
                "current_step": f"validate_{step_name}_failed",
            }

        valid, msg = unit.validate_output(output_data)
        if not valid:
            return {
                "errors": state.errors + [f"{step_name} output validation failed: {msg}"],
                "current_step": f"validate_{step_name}_failed",
            }

        return {"current_step": f"validate_{step_name}_passed"}

    return validation_node
```

---

## 5. Conditional Edges (`edges.py`)

### Design Principle

After each validation node, route to either:
- Next processing step (validation passed)
- Halt node (validation failed)

### Validation Router

```python
from prism.stage2.graph.state import Stage2GraphState


def route_after_validate_parser(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "classify"


def route_after_validate_classifier(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "build_hierarchy"


def route_after_validate_hierarchy(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "map_components"


def route_after_validate_mapper(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "map_tokens"


def route_after_validate_tokens(state: Stage2GraphState) -> str:
    if state.has_error():
        return "halt"
    return "build_topology"


def route_after_validate_topology(state: Stage2GraphState) -> str:
    if state.has_error():
        return "end"
    return "end"
```

### Fallback Router (for future swappable implementations)

```python
def route_fallback(state: Stage2GraphState, step_name: str, available_fallbacks: list[str]) -> str:
    """Route to next fallback implementation if current step failed."""
    if not state.has_error():
        return f"validate_{step_name}"

    if state.retry_count.get(step_name, 0) >= len(available_fallbacks):
        return "halt"

    return available_fallbacks[state.retry_count.get(step_name, 0)]
```

---

## 6. Subgraph Builder (`builder.py`)

### Design Principle

Assembles the complete Stage 2 StateGraph from:
- State model
- ProcessingUnit implementations (from PipelineConfig)
- Node functions + validation nodes
- Conditional edges

```python
from langgraph.graph import StateGraph, END
from prism.stage2.graph.state import Stage2GraphState
from prism.stage2.graph.nodes import (
    create_parse_node, create_classify_node, create_hierarchy_node,
    create_mapper_node, create_token_span_node, create_topology_node,
)
from prism.stage2.graph.edges import (
    route_after_validate_parser, route_after_validate_classifier,
    route_after_validate_hierarchy, route_after_validate_mapper,
    route_after_validate_tokens, route_after_validate_topology,
)
from prism.stage2.pipeline_config import Stage2PipelineConfig


def build_stage2_subgraph(
    config: Stage2PipelineConfig | None = None,
) -> StateGraph:
    """Build the Stage 2 LangGraph subgraph.

    Args:
        config: Pipeline config specifying which implementations to use.
                Defaults to current implementations.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    pipeline_config = config or Stage2PipelineConfig()

    # Instantiate all units
    parser = pipeline_config.parser()
    classifier = pipeline_config.classifier()
    hierarchy_builder = pipeline_config.hierarchy_builder()
    component_mapper = pipeline_config.component_mapper()
    token_span_mapper = pipeline_config.token_span_mapper()
    topology_builder = pipeline_config.topology_builder()

    # Create state graph
    graph = StateGraph(Stage2GraphState)

    # === Add processing nodes ===
    graph.add_node("parse", create_parse_node(parser))
    graph.add_node("classify", create_classify_node(classifier))
    graph.add_node("build_hierarchy", create_hierarchy_node(hierarchy_builder))
    graph.add_node("map_components", create_mapper_node(component_mapper))
    graph.add_node("map_tokens", create_token_span_node(token_span_mapper))
    graph.add_node("build_topology", create_topology_node(topology_builder))

    # === Add validation nodes ===
    from functools import partial

    graph.add_node(
        "validate_parser",
        lambda state: {"current_step": "validated_parser"}
        if parser.validate_output(state.nodes)[0]
        else {"errors": state.errors + [f"Parser output invalid: {parser.validate_output(state.nodes)[1]}"]}
    )
    graph.add_node(
        "validate_classifier",
        lambda state: {"current_step": "validated_classifier"}
        if classifier.validate_output(state.report)[0]
        else {"errors": state.errors + [f"Classifier output invalid: {classifier.validate_output(state.report)[1]}"]}
    )
    graph.add_node(
        "validate_hierarchy",
        lambda state: {"current_step": "validated_hierarchy"}
        if hierarchy_builder.validate_output(state.tree)[0]
        else {"errors": state.errors + [f"Hierarchy output invalid: {hierarchy_builder.validate_output(state.tree)[1]}"]}
    )
    graph.add_node(
        "validate_mapper",
        lambda state: {"current_step": "validated_mapper"}
        if component_mapper.validate_output(state.components)[0]
        else {"errors": state.errors + [f"Mapper output invalid"]}
    )
    graph.add_node(
        "validate_tokens",
        lambda state: {"current_step": "validated_tokens"}
        if token_span_mapper.validate_output(state.token_mapping)[0]
        else {"errors": state.errors + [f"TokenSpan output invalid"]}
    )
    graph.add_node(
        "validate_topology",
        lambda state: {"current_step": "validated_topology"}
        if topology_builder.validate_output(state.stage2_output)[0]
        else {"errors": state.errors + [f"Topology output invalid"]}
    )

    # === Add halt and end nodes ===
    graph.add_node("halt", lambda state: {"current_step": "halted"})
    graph.add_node("end", lambda state: {"current_step": "complete"})

    # === Add sequential edges ===
    graph.set_entry_point("parse")
    graph.add_edge("parse", "validate_parser")
    graph.add_edge("classify", "validate_classifier")
    graph.add_edge("build_hierarchy", "validate_hierarchy")
    graph.add_edge("map_components", "validate_mapper")
    graph.add_edge("map_tokens", "validate_tokens")
    graph.add_edge("build_topology", "validate_topology")

    # === Add conditional edges (validation routing) ===
    graph.add_conditional_edges(
        "validate_parser",
        route_after_validate_parser,
        {"classify": "classify", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_classifier",
        route_after_validate_classifier,
        {"build_hierarchy": "build_hierarchy", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_hierarchy",
        route_after_validate_hierarchy,
        {"map_components": "map_components", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_mapper",
        route_after_validate_mapper,
        {"map_tokens": "map_tokens", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_tokens",
        route_after_validate_tokens,
        {"build_topology": "build_topology", "halt": "halt"},
    )
    graph.add_conditional_edges(
        "validate_topology",
        route_after_validate_topology,
        {"end": "end"},
    )

    return graph.compile()
```

---

## 7. Graph Config (`config.py`)

```python
from pydantic import BaseModel, Field
from prism.stage2.pipeline_config import Stage2PipelineConfig


class GraphConfig(Stage2PipelineConfig):
    """Extends Stage2PipelineConfig with graph-specific options."""

    checkpoint_db_path: str = Field(
        default="data/prism_checkpoints.db",
        description="SQLite database path for LangGraph checkpointing",
    )

    max_retries_per_step: int = Field(
        default=0,
        ge=0,
        description="Maximum retries per step on validation failure (0 = no retry)",
    )

    enable_fallback: bool = Field(
        default=False,
        description="Whether to enable fallback routing on step failure",
    )

    step_timeout_seconds: dict[str, int] = Field(
        default_factory=dict,
        description="Per-step timeout limits (e.g., {'parse': 30, 'classify': 60})",
    )
```

---

## 8. Integration with Top-Level Orchestrator

### How Stage 2 Subgraph plugs into the main pipeline

```python
from langgraph.graph import StateGraph
from prism.orchestrator.state import PrismState
from prism.stage2.graph import build_stage2_subgraph


def create_top_level_graph():
    """Creates the full Prism pipeline graph with Stage 2 as a subgraph."""
    graph = StateGraph(PrismState)

    # Stage 1 (simple node or subgraph)
    graph.add_node("stage1", stage1_node)

    # Stage 2 as a subgraph (compiled)
    stage2_subgraph = build_stage2_subgraph()
    graph.add_node("stage2", stage2_subgraph)

    # Stage 3 (will be its own subgraph later)
    graph.add_node("stage3", stage3_node)

    # Stage 4 (will be its own subgraph later)
    graph.add_node("stage4", stage4_node)

    # Wire stages together
    graph.add_edge("stage1", "stage2")
    graph.add_edge("stage2", "stage3")
    graph.add_edge("stage3", "stage4")

    graph.set_entry_point("stage1")
    graph.set_finish_point("stage4")

    return graph.compile()
```

### State Conversion (PrismState ↔ Stage2GraphState)

```python
def prism_to_stage2_state(prism_state: PrismState) -> dict:
    """Convert PrismState to Stage2GraphState input."""
    return {
        "source_text": prism_state.stage1_output.source_text,
    }


def stage2_to_prism_state(stage2_result: Stage2GraphState, prism_state: PrismState) -> dict:
    """Convert Stage2GraphState output back to PrismState update."""
    return {
        "stage2_output": stage2_result.stage2_output,
    }
```

---

## 9. Checkpointing

### SQLite Checkpointer

```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

def build_stage2_with_checkpointing(config: GraphConfig | None = None):
    """Build Stage 2 subgraph with SQLite checkpointing."""
    graph_config = config or GraphConfig()
    graph = build_stage2_subgraph(graph_config.pipeline_config)

    # SQLite checkpointer — local, no cloud
    conn = sqlite3.connect(graph_config.checkpoint_db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return graph.compile(checkpointer=checkpointer)


# Usage:
subgraph = build_stage2_with_checkpointing()

# Run with thread_id (document ID)
result = subgraph.invoke(
    {"source_text": "# Hello\n\nWorld"},
    config={"configurable": {"thread_id": "doc_001"}},
)

# Resume from checkpoint (if interrupted)
result = subgraph.invoke(None, config={"configurable": {"thread_id": "doc_001"}})
```

---

## 10. Testing Strategy

### Unit Tests for Individual Nodes

```python
class TestParseNode:
    def test_parse_node_produces_nodes(self):
        parser = MarkdownItParser()
        node_fn = create_parse_node(parser)
        state = Stage2GraphState(source_text="# Hello\n\nWorld")
        result = node_fn(state)
        assert "nodes" in result
        assert len(result["nodes"]) > 0
```

### Integration Test for Full Subgraph

```python
class TestStage2Subgraph:
    def test_full_subgraph_execution(self):
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke(
            {"source_text": "# Heading\n\nParagraph text"}
        )
        assert result["stage2_output"] is not None
        assert result["current_step"] == "complete"

    def test_subgraph_halts_on_parser_failure(self):
        subgraph = build_stage2_subgraph()
        result = subgraph.invoke({"source_text": ""})
        assert result["has_error"]()
        assert result["current_step"] == "halted"

    def test_subgraph_checkpointing(self):
        subgraph = build_stage2_with_checkpointing()
        # Run with thread_id, interrupt, resume
        ...
```

---

## 11. Implementation Order

```
Prerequisite: Phase 1-3 must be complete (Protocols + Pipeline)

Phase 5a: State + Nodes
  1. Implement state.py (Stage2GraphState)
  2. Implement nodes.py (6 node creators + validation nodes)
  3. Write unit tests for each node

Phase 5b: Edges + Builder
  4. Implement edges.py (routing functions)
  5. Implement builder.py (assemble StateGraph)
  6. Write integration tests for full subgraph

Phase 5c: Checkpointing + Config
  7. Implement config.py (GraphConfig)
  8. Add SQLite checkpointer support
  9. Write checkpointing tests

Phase 5d: Integration
  10. Wire into top-level orchestrator (when orchestrator exists)
  11. State conversion tests (PrismState ↔ Stage2GraphState)
```
