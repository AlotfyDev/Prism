# Stage 2 Pipeline Abstraction — Architectural Design

> Decision Date: 2026-05-02
> Status: DESIGN COMPLETE — Ready for Phase 1 implementation
> Location: `prism/stage2/`

---

## 1. Problem Statement

Stage 2 currently has 6 ProcessingUnits that work independently:
- `MarkdownItParser` — parses Markdown to AST
- `LayerClassifier` — dispatches 15 detectors
- `HierarchyBuilder` — builds parent-child tree
- `ComponentMapper` — converts to typed components
- `TokenSpanMapper` — maps char offsets to token IDs
- `TopologyBuilder` — assembles Stage2Output

**Gaps identified:**
| Gap | Severity | Description |
|-----|----------|-------------|
| G1 | 🔴 High | No unit inherits ProcessingUnit ABC |
| G2 | 🔴 High | Method names inconsistent: `process()`, `classify()`, `build()`, `map()` |
| G3 | 🟡 Medium | 3 units use multi-parameter inputs instead of single input model |
| G4 | 🟡 Medium | 3 units return non-Pydantic types (`list`, `dict`) |
| G5 | 🟡 Medium | No per-step `typing.Protocol` for static type checking |
| G6 | 🟢 Low | `config` always Optional (acceptable) |

---

## 2. Solution: Three-Phase Plan

### Phase 1: Interface Unification
- **G2:** Rename `classify()`, `build()`, `map()` → `process()`
- **G3:** Create Input wrapper Pydantic models for multi-param units
- **G4:** Create Output wrapper Pydantic models for non-Pydantic returns

### Phase 2: Protocol Definitions
- **G5:** Create 6 `typing.Protocol` classes in `protocols.py`
- **G1:** Each unit becomes Protocol-compliant (structural subtyping, no inheritance)

### Phase 3: Stage2Pipeline
- `Stage2PipelineConfig` — swappable unit registry
- `Stage2Pipeline` — sync orchestrator with validation gates
- Integration tests

---

## 3. FileSystem Structure

```
prism/stage2/
├── __init__.py                    ← updated exports
├── protocols.py                   ← NEW: 6 typing.Protocol definitions
├── pipeline_config.py             ← NEW: Stage2PipelineConfig
├── pipeline.py                    ← NEW: Stage2Pipeline class
├── parser.py                      ← EXISTING (G2: classify→process)
├── classifier.py                  ← EXISTING (G2, G3, G4 fixes)
├── hierarchy.py                   ← EXISTING (G2 fix)
├── mapper.py                      ← EXISTING (G2, G3, G4 fixes)
├── token_span.py                  ← EXISTING (G2, G3, G4 fixes)
├── topology.py                    ← EXISTING (G2 fix)
├── validation_v2.py               ← EXISTING
├── char_offset.py                 ← EXISTING
└── layers/                        ← EXISTING (detectors, CRUDs)
    └── ...

tests/
├── test_stage2_pipeline.py        ← NEW: Pipeline integration tests
└── ...existing tests...           ← updated for G2 method renames
```

### LangGraph Subgraph (Phase 5 — future)

```
prism/stage2/
└── graph/                         ← NEW: LangGraph subgraph package
    ├── __init__.py                ← exports build_stage2_subgraph
    ├── state.py                   ← Stage2GraphState (Pydantic)
    ├── nodes.py                   ← node wrappers per step
    ├── edges.py                   ← conditional edges (validation, fallback)
    └── builder.py                 ← build_stage2_subgraph() → CompiledStateGraph

tests/
└── test_stage2_subgraph.py        ← NEW: subgraph tests
```

---

## 4. Protocol Definitions (Phase 2)

### Design Principle: `typing.Protocol` (Structural Subtyping)

No inheritance required. Any class matching the signature is Protocol-compliant.
`@runtime_checkable` enables `isinstance()` checks at runtime.

### Protocol: `IParser`

```python
@runtime_checkable
class IParser(Protocol):
    def process(self, input_data: Stage1Output, config: TopologyConfig | None = None) -> list[MarkdownNode]: ...
    def validate_input(self, input_data: Stage1Output) -> tuple[bool, str]: ...
    def validate_output(self, output_data: list[MarkdownNode]) -> tuple[bool, str]: ...
    def name(self) -> str: ...
    @property
    def tier(self) -> str: ...
    @property
    def version(self) -> str: ...
```

### Protocol: `IClassifier`

```python
@runtime_checkable
class IClassifier(Protocol):
    def process(self, input_data: ClassifierInput, config: TopologyConfig | None = None) -> DetectedLayersReport: ...
    def validate_input(self, input_data: ClassifierInput) -> tuple[bool, str]: ...
    def validate_output(self, output_data: DetectedLayersReport) -> tuple[bool, str]: ...
    def name(self) -> str: ...
    @property
    def tier(self) -> str: ...
    @property
    def version(self) -> str: ...
```

### Protocol: `IHierarchyBuilder`

```python
@runtime_checkable
class IHierarchyBuilder(Protocol):
    def process(self, input_data: HierarchyInput, config: TopologyConfig | None = None) -> HierarchyTree: ...
    def validate_input(self, input_data: HierarchyInput) -> tuple[bool, str]: ...
    def validate_output(self, output_data: HierarchyTree) -> tuple[bool, str]: ...
    def name(self) -> str: ...
    @property
    def tier(self) -> str: ...
    @property
    def version(self) -> str: ...
```

### Protocol: `IComponentMapper`

```python
@runtime_checkable
class IComponentMapper(Protocol):
    def process(self, input_data: MapperInput, config: TopologyConfig | None = None) -> MapperOutput: ...
    def validate_input(self, input_data: MapperInput) -> tuple[bool, str]: ...
    def validate_output(self, output_data: MapperOutput) -> tuple[bool, str]: ...
    def name(self) -> str: ...
    @property
    def tier(self) -> str: ...
    @property
    def version(self) -> str: ...
```

### Protocol: `ITokenSpanMapper`

```python
@runtime_checkable
class ITokenSpanMapper(Protocol):
    def process(self, input_data: TokenSpanInput, config: TopologyConfig | None = None) -> TokenSpanOutput: ...
    def validate_input(self, input_data: TokenSpanInput) -> tuple[bool, str]: ...
    def validate_output(self, output_data: TokenSpanOutput) -> tuple[bool, str]: ...
    def name(self) -> str: ...
    @property
    def tier(self) -> str: ...
    @property
    def version(self) -> str: ...
```

### Protocol: `ITopologyBuilder`

```python
@runtime_checkable
class ITopologyBuilder(Protocol):
    def process(self, input_data: TopologyInput, config: TopologyConfig | None = None) -> Stage2Output: ...
    def validate_input(self, input_data: TopologyInput) -> tuple[bool, str]: ...
    def validate_output(self, output_data: Stage2Output) -> tuple[bool, str]: ...
    def name(self) -> str: ...
    @property
    def tier(self) -> str: ...
    @property
    def version(self) -> str: ...
```

---

## 5. Input/Output Wrapper Models (Phase 1)

### ClassifierInput (G3 fix for LayerClassifier)

```python
class ClassifierInput(BaseModel):
    """Wraps multi-param input for IClassifier.process()."""
    nodes: list[MarkdownNode] = Field(..., description="AST root nodes from parser")
    source_text: str = Field(..., min_length=1, description="Original Markdown source")
```

### HierarchyInput (G3 fix — currently single param, but wrapper for consistency)

```python
class HierarchyInput(BaseModel):
    """Wraps input for IHierarchyBuilder.process()."""
    report: DetectedLayersReport = Field(..., description="Classification report")
```

### MapperInput (G3 fix for ComponentMapper)

```python
class MapperInput(BaseModel):
    """Wraps multi-param input for IComponentMapper.process()."""
    tree: HierarchyTree = Field(..., description="Hierarchy tree from HierarchyBuilder")
```

### MapperOutput (G4 fix for ComponentMapper)

```python
class MapperOutput(BaseModel):
    """Wraps list[PhysicalComponent] for IComponentMapper output."""
    components: list[PhysicalComponent] = Field(
        default_factory=list,
        description="Typed physical components"
    )

    @property
    def component_count(self) -> int:
        return len(self.components)
```

### TokenSpanInput (G3 fix for TokenSpanMapper)

```python
class TokenSpanInput(BaseModel):
    """Wraps multi-param input for ITokenSpanMapper.process()."""
    components: list[PhysicalComponent] = Field(..., description="Components to map")
    stage1_output: Stage1Output = Field(..., description="Stage 1 tokens and metadata")
```

### TokenSpanOutput (G4 fix for TokenSpanMapper)

```python
class TokenSpanOutput(BaseModel):
    """Wraps dict[str, list[str]] for ITokenSpanMapper output."""
    component_to_tokens: dict[str, list[str]] = Field(
        default_factory=dict,
        description="component_id -> list of global token IDs"
    )
```

### TopologyInput (G3 fix for TopologyBuilder)

```python
class TopologyInput(BaseModel):
    """Wraps multi-param input for ITopologyBuilder.process()."""
    components: list[PhysicalComponent] = Field(..., description="Typed components")
    token_mapping: dict[str, list[str]] = Field(
        default_factory=dict,
        description="component_id -> token IDs"
    )
```

### ParserOutput (G4 fix for MarkdownItParser)

```python
class ParserOutput(BaseModel):
    """Wraps list[MarkdownNode] for IParser output."""
    nodes: list[MarkdownNode] = Field(
        default_factory=list,
        description="AST root nodes"
    )

    @property
    def node_count(self) -> int:
        return len(self.nodes)
```

---

## 6. Stage2PipelineConfig (Phase 3)

```python
class Stage2PipelineConfig(BaseModel):
    """Configuration for Stage2Pipeline — defines which implementation
    to use for each processing step. All defaults are the current implementations.

    To swap any unit, replace the class reference:
        config = Stage2PipelineConfig(token_span_mapper=MLTokenSpanMapper)
    """
    parser: type = Field(default=MarkdownItParser, description="IParser implementation")
    classifier: type = Field(default=LayerClassifier, description="IClassifier implementation")
    hierarchy_builder: type = Field(default=HierarchyBuilder, description="IHierarchyBuilder implementation")
    component_mapper: type = Field(default=ComponentMapper, description="IComponentMapper implementation")
    token_span_mapper: type = Field(default=TokenSpanMapper, description="ITokenSpanMapper implementation")
    topology_builder: type = Field(default=TopologyBuilder, description="ITopologyBuilder implementation")
```

---

## 7. Stage2Pipeline (Phase 3)

```python
class Stage2Pipeline:
    """Orchestrates Stage 2 as a single pipeline.

    Each step is swappable via Stage2PipelineConfig.
    Validation gates run between each step.
    On validation failure, raises PipelineStepError with details.

    Usage:
        pipeline = Stage2Pipeline()  # default config
        # OR
        pipeline = Stage2Pipeline(config=custom_config)

        output = pipeline.process(stage1_output, topology_config)
    """

    def __init__(self, config: Stage2PipelineConfig | None = None):
        self.config = config or Stage2PipelineConfig()
        self._units = self._instantiate_units()

    def _instantiate_units(self) -> dict[str, Any]:
        return {
            "parser": self.config.parser(),
            "classifier": self.config.classifier(),
            "hierarchy_builder": self.config.hierarchy_builder(),
            "component_mapper": self.config.component_mapper(),
            "token_span_mapper": self.config.token_span_mapper(),
            "topology_builder": self.config.topology_builder(),
        }

    def process(self, input_data: Stage1Output, config: TopologyConfig | None = None) -> Stage2Output:
        # Step 1: Parse
        nodes = self._units["parser"].process(input_data, config)
        self._validate_step("parser", input_data, nodes)

        # Step 2: Classify
        classifier_input = ClassifierInput(nodes=nodes, source_text=input_data.source_text)
        report = self._units["classifier"].process(classifier_input, config)
        self._validate_step("classifier", classifier_input, report)

        # Step 3: Build hierarchy
        hierarchy_input = HierarchyInput(report=report)
        tree = self._units["hierarchy_builder"].process(hierarchy_input, config)
        self._validate_step("hierarchy_builder", hierarchy_input, tree)

        # Step 4: Map components
        mapper_input = MapperInput(tree=tree)
        mapper_output = self._units["component_mapper"].process(mapper_input, config)
        self._validate_step("component_mapper", mapper_input, mapper_output)

        # Step 5: Map tokens
        token_span_input = TokenSpanInput(
            components=mapper_output.components,
            stage1_output=input_data,
        )
        token_span_output = self._units["token_span_mapper"].process(token_span_input, config)
        self._validate_step("token_span_mapper", token_span_input, token_span_output)

        # Step 6: Build topology
        topology_input = TopologyInput(
            components=mapper_output.components,
            token_mapping=token_span_output.component_to_tokens,
        )
        output = self._units["topology_builder"].process(topology_input, config)
        self._validate_step("topology_builder", topology_input, output)

        return output

    def _validate_step(self, step_name: str, input_data: Any, output_data: Any) -> None:
        unit = self._units[step_name]
        valid, msg = unit.validate_input(input_data)
        if not valid:
            raise PipelineStepError(step_name, "input", msg)
        valid, msg = unit.validate_output(output_data)
        if not valid:
            raise PipelineStepError(step_name, "output", msg)
```

---

## 8. Backward Compatibility Plan

### Method Renames (G2) — Impact on Tests

| File | Current | After |
|------|---------|-------|
| `classifier.py` | `classify()` | `process()` |
| `hierarchy.py` | `build()` | `process()` |
| `mapper.py` | `map()` | `process()` |
| `token_span.py` | `map()` | `process()` |
| `topology.py` | `build()` | `process()` |

**Test impact:** All tests calling `.classify()`, `.build()`, `.map()` must be updated.
**Strategy:** Add `classify = process` alias during transition, then remove.

### Input/Output Wrappers (G3/G4) — Impact on Tests

Tests that construct units with individual params must wrap them:
```python
# Before
report = classifier.classify(nodes, source_text, config)

# After
report = classifier.process(ClassifierInput(nodes=nodes, source_text=source_text), config)
```

---

## 9. LangGraph Subgraph Architecture (Phase 5 — Future)

### Structure
```
prism/stage2/graph/
├── __init__.py     → build_stage2_subgraph()
├── state.py        → Stage2GraphState (Pydantic state for LangGraph)
├── nodes.py        → create_node(unit, step_name) wrappers
├── edges.py        → route_validation(state) → "next" | "halt"
└── builder.py      → assemble StateGraph with nodes + edges
```

### State Model
```python
class Stage2GraphState(BaseModel):
    source_text: str = ""
    nodes: list[MarkdownNode] = []
    report: DetectedLayersReport | None = None
    tree: HierarchyTree | None = None
    components: list[PhysicalComponent] = []
    token_mapping: dict[str, list[str]] = {}
    stage2_output: Stage2Output | None = None
    errors: list[str] = []
    current_step: str = "init"
```

### Graph Topology
```
START → parse → validate_parser → classify → validate_classifier
    → build_hierarchy → validate_hierarchy → map_components → validate_mapper
    → map_tokens → validate_tokens → build_topology → validate_topology → END
                                              ↓
                                           HALT (on any validation failure)
```

Each step has:
- Conditional edge to next step (validation passed) or halt (failed)
- Fallback edge to alternative implementation (if configured)
- SQLite checkpointing via LangGraph SqliteSaver

---

## 10. Implementation Order

```
Phase 1 (G2/G3/G4):
  1. Create Input/Output wrapper models in pipeline_models.py
  2. Rename methods in existing units (add aliases for transition)
  3. Update all tests

Phase 2 (G5):
  4. Create protocols.py with 6 Protocol definitions
  5. Verify Protocol compliance (runtime isinstance checks)

Phase 3 (Pipeline):
  6. Create pipeline_config.py
  7. Create pipeline.py (Stage2Pipeline class)
  8. Create test_stage2_pipeline.py
  9. Run full regression suite

Phase 5 (LangGraph Subgraph — future):
  10. Create graph/ package
  11. Implement state.py, nodes.py, edges.py, builder.py
  12. Integrate with top-level orchestrator
```
