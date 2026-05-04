# Stage 2 Aggregation Architecture — Design Document

> Decision Date: 2026-05-02
> Status: DESIGN COMPLETE — Ready for implementation
> Location: `prism/stage2/aggregation/`
> Dependencies: spaCy (default), fastembed + e5-small (default)

---

## 1. Problem Statement

Stage 2 currently has 5 aggregation gaps:
- No heading sequence validation or pattern detection
- No cross-detector correlation (detectors work independently)
- No reverse token index (TokenSpanMapper is one-directional)
- No table/list matrix indexing (parsed but not structured for query)
- No indentation pattern analysis for heading grouping

All aggregation tasks fall into two categories:
1. **Rules/Regex only** (8 tasks, 90-100% reliability)
2. **NLP-enhanced** (2 tasks, 95-98%+ reliability with spaCy/e5-small as defaults)

---

## 2. FileSystem Structure

```
prism/stage2/
├── aggregation/                      ← NEW: aggregation package
│   ├── __init__.py                   ← exports all aggregators + AggregatorOutput
│   ├── protocols.py                  ← IAggregator Protocol definitions
│   │
│   ├── rules/                        ← Rules/Regex-only aggregators
│   │   ├── __init__.py
│   │   ├── table_aggregator.py       ← Table matrix parsing (100%)
│   │   ├── list_aggregator.py        ← List matrix parsing (100%)
│   │   ├── codeblock_aggregator.py   ← Code block line parsing (100%)
│   │   ├── token_range_aggregator.py ← Token↔Component bidirectional (100%)
│   │   ├── indentation_analyzer.py   ← Heading indentation patterns (90%)
│   │   ├── nesting_validator.py      ← NestingMatrix enforcement (100%)
│   │   └── topology_assembler.py     ← Final Stage2Output assembly (100%)
│   │
│   └── nlp/                          ← NLP-enhanced aggregators (spaCy + e5-small default)
│       ├── __init__.py
│       ├── heading_sequence.py       ← Heading sequence + spaCy POS (98%+)
│       └── detector_correlation.py   ← Cross-detector + e5-small (85%+)
│
├── pipeline_models.py                ← updated: aggregation wrapper models
├── protocols.py                      ← updated: IAggregator Protocol
├── pipeline.py                       ← updated: pipeline includes aggregation steps
├── pipeline_config.py                ← updated: includes aggregation config
└── graph/                            ← updated: aggregation nodes + edges
    ├── nodes.py                      ← aggregation node creators
    ├── edges.py                      ← aggregation routing
    └── builder.py                    ← includes aggregation steps

tests/
├── test_stage2_aggregation.py        ← Aggregation integration tests
├── test_aggregation_rules/           ← Rules-only aggregator unit tests
│   ├── test_table_aggregator.py
│   ├── test_list_aggregator.py
│   ├── test_codeblock_aggregator.py
│   ├── test_token_range_aggregator.py
│   ├── test_indentation_analyzer.py
│   ├── test_nesting_validator.py
│   └── test_topology_assembler.py
└── test_aggregation_nlp/             ← NLP-enhanced aggregator tests
    ├── test_heading_sequence.py
    └── test_detector_correlation.py
```

---

## 3. Aggregation Tasks — Full Inventory

### Category A: NLP-Enhanced (spaCy + e5-small default)

| # | Task | Processor | Reliability | File |
|---|------|-----------|-------------|------|
| A1 | Heading sequence validation | Rules + spaCy POS | 98%+ | `heading_sequence.py` |
| A2 | Cross-detector correlation | Rules + e5-small | 85%+ | `detector_correlation.py` |

### Category B: Rules/Regex Only

| # | Task | Processor | Reliability | File |
|---|------|-----------|-------------|------|
| B1 | Table matrix parsing | markdown-it-py AST | 100% | `table_aggregator.py` |
| B2 | List matrix parsing | markdown-it-py AST | 100% | `list_aggregator.py` |
| B3 | Code block line parsing | fence tokens + split | 100% | `codeblock_aggregator.py` |
| B4 | Token↔Component bidirectional | Binary search + range lookup | 100% | `token_range_aggregator.py` |
| B5 | Heading indentation analysis | Regex + whitespace | 90% | `indentation_analyzer.py` |
| B6 | Nesting validation | NestingMatrix rules | 100% | `nesting_validator.py` |
| B7 | Topological assembly | Dictionary assembly | 100% | `topology_assembler.py` |

---

## 4. Category A: NLP-Enhanced Aggregators

### A1: Heading Sequence Analyzer

**File:** `prism/stage2/aggregation/nlp/heading_sequence.py`

**Purpose:** Validate heading hierarchy and detect structural patterns.

**Input:** `list[HeadingComponent]` (from ComponentMapper, already sorted by char_start)

**Output:** `HeadingSequenceReport`

**HeadingSequenceReport Fields:**
```python
class HeadingSequenceReport(BaseModel):
    headings: list[HeadingComponent]          # Ordered headings
    sequence: list[int]                        # [1, 2, 2, 3, 2, 1] levels
    is_valid: bool                             # True if no level skips
    violations: list[HeadingViolation]         # Invalid skips found
    groups: list[HeadingGroup]                 # Grouped by parent heading
    indentation_pattern: IndentationPattern    # Consistent/Inconsistent
    max_depth: int                             # Deepest heading level used
    avg_siblings: float                        # Average headings per section
```

**HeadingViolation Fields:**
```python
class HeadingViolation(BaseModel):
    heading: HeadingComponent
    expected_levels: list[int]    # [1, 2] for H3 after H1
    actual_level: int             # 3
    severity: str                 # "skip" | "jump_back"
```

**HeadingGroup Fields:**
```python
class HeadingGroup(BaseModel):
    parent: HeadingComponent
    siblings: list[HeadingComponent]
    children: list[HeadingGroup]
    depth: int
```

**Algorithm (3 phases):**

**Phase 1: Rules-based (95%)**
1. Sort headings by `char_start`
2. Build sequence: `[h.level for h in headings]`
3. Validate: level[i+1] must be ≤ level[i] + 1
4. Detect violations: level[i+1] > level[i] + 1 → "skip"
5. Detect jump-back: level[i+1] < level[i] and difference > 1 → "jump_back"
6. Group: each heading belongs to nearest ancestor at level-1

**Phase 2: spaCy POS enhancement (+3% → 98%)**
For each heading's `raw_content`:
1. Parse with spaCy (`en_core_web_sm` or `xx_ent_wiki_sm`)
2. Check POS distribution:
   - NOUN-heavy (≥60% nouns/proper nouns) → confident heading
   - VERB present as ROOT → may not be a heading (likely paragraph misclassified)
   - PUNCT at end (`.`, `!`, `?`) → likely paragraph, not heading
3. Re-score confidence: downgrade headings that look like sentences
4. Update `HeadingComponent.confidence` based on POS analysis

**Phase 3: Indentation pattern analysis**
1. Extract leading whitespace from each heading's `raw_content`
2. Compare indentation levels:
   - Consistent (all 0 spaces) → standard markdown
   - Indented (varying spaces) → non-standard, may indicate outline format
3. Flag inconsistencies

**spaCy Model:** `en_core_web_sm` (12MB) — already in Prism dependencies.
**Performance:** ~5ms per heading, ~50ms for 10 headings.

---

### A2: Cross-Detector Correlator

**File:** `prism/stage2/aggregation/nlp/detector_correlation.py`

**Purpose:** Detect overlapping/correlated detections across independent detectors and unify them.

**Input:** `DetectedLayersReport` (from LayerClassifier)

**Output:** `CorrelatedReport`

**CorrelatedReport Fields:**
```python
class CorrelatedReport(BaseModel):
    instances: dict[LayerType, list]       # Original instances (unchanged)
    correlations: list[Correlation]         # Detected correlations
    unified_instances: list[UnifiedInstance] # Merged instances
    conflicts: list[Conflict]              # Overlapping but incompatible
    deduplicated_count: int                # How many were merged
```

**Correlation Fields:**
```python
class Correlation(BaseModel):
    type: str                               # "caption" | "diagram" | "table_title" | "figure_content"
    source_type: LayerType                  # The primary layer
    target_type: LayerType                  # The correlated layer
    source_instance: LayerInstance
    target_instance: LayerInstance
    confidence: float                       # 0.0-1.0
    method: str                             # "proximity" | "keyword" | "embedding" | "both"
```

**UnifiedInstance Fields:**
```python
class UnifiedInstance(BaseModel):
    primary_type: LayerType
    primary_instance: LayerInstance
    correlated: list[LayerInstance]
    attributes: dict                        # Enriched attributes from correlation
    correlation_ids: list[str]             # IDs of correlated instances
```

**Conflict Fields:**
```python
class Conflict(BaseModel):
    instances: list[LayerInstance]          # Overlapping but incompatible
    reason: str                             # "char_overlap" | "type_conflict"
    char_overlap_pct: float                 # Percentage of overlap
    resolution: str                         # "keep_larger" | "keep_first" | "flag"
```

**Correlation Patterns (4 types):**

**Type 1: Table Caption (Rules + Embedding)**
```
Input:
  - TABLE: char_start=100, char_end=500
  - PARAGRAPH: char_start=50, char_end=95, content="Table 1: Summary"

Detection:
  1. Proximity: paragraph within 50 chars before table → +0.4 confidence
  2. Keyword: "Table N:" or "الجدول N:" pattern → +0.5 confidence
  3. Embedding: e5-small similarity between paragraph and table context → +0.1
  4. Total: ≥0.8 → correlate as table_caption

Output:
  Correlation(type="table_caption", source=TABLE, target=PARAGRAPH, confidence=0.9)
  UnifiedInstance(primary_type=TABLE, attributes={"caption": "Table 1: Summary"})
```

**Type 2: Diagram in Code Block (Rules + Embedding)**
```
Input:
  - CODE_BLOCK: content="```mermaid\ngraph TD; A-->B;\n```"
  - No DIAGRAM detected

Detection:
  1. Keyword: "mermaid" or "graphviz" or "plantuml" in content → +0.7 confidence
  2. Embedding: e5-small similarity with known diagram patterns → +0.2
  3. Total: ≥0.8 → create DIAGRAM instance linked to CODE_BLOCK

Output:
  Correlation(type="diagram", source=CODE_BLOCK, target=new DIAGRAM, confidence=0.9)
  UnifiedInstance(primary_type=CODE_BLOCK, attributes={"diagram_type": "mermaid"})
```

**Type 3: Figure with Caption (Proximity + Embedding)**
```
Input:
  - FIGURE: char_start=200, char_end=400 (image tag)
  - PARAGRAPH: char_start=405, char_end=450 (caption text)

Detection:
  1. Proximity: paragraph within 50 chars after figure → +0.5
  2. Embedding: e5-small similarity confirms caption relevance → +0.3
  3. Total: ≥0.7 → correlate as figure_caption

Output:
  Correlation(type="figure_caption", source=FIGURE, target=PARAGRAPH, confidence=0.8)
```

**Type 4: Footnote Definition↔Reference (Rules — already exists)**
```
Already handled by UnifiedFootnoteDetector.
Enrich with correlation metadata.
```

**Conflict Detection:**
```
Input:
  - PARAGRAPH: char_start=100, char_end=200
  - TABLE: char_start=150, char_end=250

Detection:
  1. Char overlap: 50 chars (50% of paragraph, 33% of table)
  2. Overlap > 10% AND types incompatible → flag as conflict

Resolution:
  - Keep larger (by char range)
  - Or keep first (by char_start)
  - Or flag for manual review (confidence < 0.5)
```

**Embedding Model:** `e5-small` (235MB) — already in Prism via fastembed.
**Performance:** ~50ms per correlation pair, ~200ms for 10 pairs.

---

## 5. Category B: Rules/Regex Aggregators

### B1: Table Aggregator

**File:** `prism/stage2/aggregation/rules/table_aggregator.py`

**Purpose:** Build structured table index from markdown-it-py AST tokens.

**Input:** `list[MarkdownNode]` (AST nodes for table type)

**Output:** `TableIndex`

**TableIndex Fields:**
```python
class TableIndex(BaseModel):
    table: TableComponent
    dimensions: tuple[int, int]              # (rows, cols)
    has_header: bool
    header_cells: list[str]                  # Header cell texts
    cell_matrix: list[list[dict]]            # 2D matrix of cell metadata
    merged_cells: list[tuple]                # [(row_start, col_start, row_end, col_end)]
    raw_markdown: str                        # Original markdown source
```

**Algorithm:**
1. Parse markdown-it-py AST: `table_open` → `tbody_open` → `tr_open` → `td_open` → inline → `td_close` → ...
2. Build 2D cell matrix from `td` tokens
3. Detect header: first row before `thead_separator` or first `th` tokens
4. Extract cell content from inline tokens
5. Detect merged cells (if `colspan`/`rowspan` attributes present)
6. Return TableIndex with all metadata

**Reliability:** 100% — AST tokens are explicit.

---

### B2: List Aggregator

**File:** `prism/stage2/aggregation/rules/list_aggregator.py`

**Purpose:** Build structured list index with nesting hierarchy.

**Input:** `list[MarkdownNode]` (AST nodes for list type)

**Output:** `ListIndex`

**ListIndex Fields:**
```python
class ListIndex(BaseModel):
    list_component: ListComponent
    style: str                               # "ordered" | "unordered"
    total_items: int                         # All items (including nested)
    top_level_items: int                     # Direct children only
    max_depth: int                           # Deepest nesting level
    items: list[ListItemIndex]               # Flat list with depth info
    nesting_tree: list[NestedItem]           # Hierarchical structure
    indentation_levels: list[int]            # [0, 2, 4] spaces used
```

**Algorithm:**
1. Parse markdown-it-py AST: `bullet_list_open`/`ordered_list_open` → `list_item_open` → ...
2. Track depth via `token.level` (markdown-it-py nesting level)
3. Build flat list with depth info
4. Convert to nesting tree: each item's children are items at depth+1 before next sibling
5. Extract indentation levels from raw content

**Reliability:** 100% — AST tokens are explicit.

---

### B3: Code Block Aggregator

**File:** `prism/stage2/aggregation/rules/codeblock_aggregator.py`

**Purpose:** Build structured code block index with line numbers.

**Input:** `list[MarkdownNode]` (AST nodes for code block/fence type)

**Output:** `CodeBlockIndex`

**CodeBlockIndex Fields:**
```python
class CodeBlockIndex(BaseModel):
    component: CodeBlockComponent
    language: str
    total_lines: int
    non_empty_lines: int
    lines: list[CodeLine]                    # Line-by-line breakdown
    indentation_pattern: list[int]           # Indentation per line
    has_syntax_markers: bool                 # Line numbers, highlights, etc.
```

**Algorithm:**
1. Extract raw content from fence/code_block token
2. Split by `\n` → lines
3. Count non-empty lines
4. Extract indentation per line (leading spaces/tabs)
5. Detect language from `info` attribute (e.g., `python` in ````python`)

**Reliability:** 100% — fence tokens are explicit.

---

### B4: Token Range Aggregator (Bidirectional)

**File:** `prism/stage2/aggregation/rules/token_range_aggregator.py`

**Purpose:** Build bidirectional Token↔Component index.

**Input:** 
- `list[PhysicalComponent]` (with char_start/char_end)
- `dict[str, TokenMetadata]` (from Stage1Output)

**Output:** `TokenRangeIndex`

**TokenRangeIndex Fields:**
```python
class TokenRangeIndex(BaseModel):
    # Forward: component → tokens
    component_to_tokens: dict[str, list[str]]
    
    # Reverse: token → component
    token_to_component: dict[str, str]
    
    # Gaps: tokens not belonging to any component
    unassigned_tokens: list[str]
    
    # Coverage statistics
    coverage_pct: float                      # % of tokens assigned to components
    component_coverage: dict[str, float]     # Per-component coverage
```

**Algorithm:**
1. **Forward (existing):** Binary search for each component's char range → list of token IDs
2. **Reverse (new):** For each token, find which component contains it:
   - Build interval tree from component ranges (or sorted list + binary search)
   - For each token: search for component where token.char_start ∈ [comp.char_start, comp.char_end)
   - If multiple components overlap: assign to smallest (most specific)
   - If no component: mark as unassigned
3. **Coverage:** Calculate % of tokens assigned

**Reliability:** 100% — pure math, deterministic.

---

### B5: Indentation Analyzer

**File:** `prism/stage2/aggregation/rules/indentation_analyzer.py`

**Purpose:** Analyze heading indentation patterns for grouping.

**Input:** `list[HeadingComponent]` (with raw_content)

**Output:** `IndentationPattern`

**IndentationPattern Fields:**
```python
class IndentationPattern(BaseModel):
    headings: list[HeadingWithIndent]
    is_consistent: bool                      # True if all use same indentation style
    levels: list[int]                        # [0, 2, 4] indentation levels found
    pattern_type: str                        # "standard" | "indented" | "mixed"
    groups_by_indent: dict[int, list]        # {0: [h1, h2], 2: [h3, h4]}
    anomalies: list[HeadingAnomaly]          # Inconsistent indentation
```

**Algorithm:**
1. For each heading, extract leading whitespace from `raw_content`
2. Count spaces/tabs → indentation level
3. Group headings by indentation level
4. Check consistency:
   - All level 0 → "standard" (normal markdown)
   - Mixed levels with pattern (0, 2, 4, 6) → "indented" (outline format)
   - Random levels → "mixed" (anomalies)
5. Flag anomalies: headings that break the pattern

**Reliability:** 90% — 10% uncertainty from markdown that uses non-space indentation.

---

### B6: Nesting Validator

**File:** `prism/stage2/aggregation/rules/nesting_validator.py`

**Purpose:** Validate and enforce NestingMatrix rules across the component hierarchy.

**Input:** `list[PhysicalComponent]` (with parent_id, children)

**Output:** `NestingValidationReport`

**NestingValidationReport Fields:**
```python
class NestingValidationReport(BaseModel):
    is_valid: bool
    violations: list[NestingViolation]
    max_depth: int
    avg_depth: float
    depth_distribution: dict[int, int]       # {0: 5, 1: 3, 2: 1}
    container_stats: dict[str, dict]         # Per-container: children_count, types
```

**Algorithm:**
1. Build parent-child graph from component relationships
2. Validate each parent-child pair against NestingMatrix
3. Detect cycles (A → B → A)
4. Calculate depth for each node (BFS from roots)
5. Flag violations: invalid nesting, cycles, depth limit exceeded
6. Generate statistics

**Reliability:** 100% — deterministic rules.

---

### B7: Topological Assembler

**File:** `prism/stage2/aggregation/rules/topology_assembler.py`

**Purpose:** Assemble all aggregation results into final `Stage2Output`.

**Input:** All aggregation outputs

**Output:** `Stage2Output` (enhanced)

**Enhanced Stage2Output Fields (new):**
```python
class Stage2Output(BaseModel):  # Updated
    discovered_layers: dict[str, PhysicalComponent]
    layer_types: set[LayerType]
    is_single_layer: bool
    component_to_tokens: dict[str, tuple[int, int]]
    
    # NEW: Aggregation results
    heading_sequence: HeadingSequenceReport | None
    correlations: CorrelatedReport | None
    table_indices: dict[str, TableIndex]
    list_indices: dict[str, ListIndex]
    codeblock_indices: dict[str, CodeBlockIndex]
    token_range_index: TokenRangeIndex | None
    indentation_pattern: IndentationPattern | None
    nesting_validation: NestingValidationReport | None
```

**Algorithm:**
1. Collect all aggregation outputs
2. Build component dictionary
3. Calculate layer_types from components
4. Build component_to_tokens from token_range_index
5. Assemble all aggregation results into Stage2Output
6. Validate final output

**Reliability:** 100% — dictionary assembly.

---

## 6. Protocol Definitions

### IAggregator Protocol

**File:** `prism/stage2/aggregation/protocols.py`

```python
from typing import Protocol, runtime_checkable, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@runtime_checkable
class IAggregator(Protocol[InputT, OutputT]):
    """Protocol for Stage 2 aggregation operations."""

    def aggregate(self, input_data: InputT) -> OutputT: ...

    def validate_input(self, input_data: InputT) -> tuple[bool, str]: ...

    def validate_output(self, output_data: OutputT) -> tuple[bool, str]: ...

    def name(self) -> str: ...

    @property
    def tier(self) -> str: ...

    @property
    def version(self) -> str: ...
```

### Specific Aggregator Protocols

```python
@runtime_checkable
class IHeadingSequenceAggregator(IAggregator[list[HeadingComponent], HeadingSequenceReport], Protocol): ...

@runtime_checkable
class IDetectorCorrelationAggregator(IAggregator[DetectedLayersReport, CorrelatedReport], Protocol): ...

@runtime_checkable
class ITableAggregator(IAggregator[list[MarkdownNode], TableIndex], Protocol): ...

@runtime_checkable
class IListAggregator(IAggregator[list[MarkdownNode], ListIndex], Protocol): ...

@runtime_checkable
class ICodeBlockAggregator(IAggregator[list[MarkdownNode], CodeBlockIndex], Protocol): ...

@runtime_checkable
class ITokenRangeAggregator(IAggregator[TokenRangeInput, TokenRangeIndex], Protocol): ...

@runtime_checkable
class IIndentationAggregator(IAggregator[list[HeadingComponent], IndentationPattern], Protocol): ...

@runtime_checkable
class INestingValidator(IAggregator[list[PhysicalComponent], NestingValidationReport], Protocol): ...

@runtime_checkable
class ITopologyAssembler(IAggregator[AssemblyInput, Stage2Output], Protocol): ...
```

---

## 7. Pipeline Integration

### Updated Pipeline Order

```
Stage1Input
  ↓
[1] Parser (markdown-it-py)              → list[MarkdownNode]
  ↓
[2] Classifier (15 detectors)            → DetectedLayersReport
  ↓
[3] Cross-Detector Correlator            → CorrelatedReport ⚡ NLP (e5-small)
  ↓
[4] HierarchyBuilder                     → HierarchyTree
  ↓
[5] ComponentMapper                      → list[PhysicalComponent]
  ↓
[6] Token Range Aggregator               → TokenRangeIndex
  ↓
[7] Table Aggregator                     → TableIndex
  ↓
[8] List Aggregator                      → ListIndex
  ↓
[9] Code Block Aggregator                → CodeBlockIndex
  ↓
[10] Heading Sequence Analyzer           → HeadingSequenceReport ⚡ NLP (spaCy)
  ↓
[11] Indentation Analyzer                → IndentationPattern
  ↓
[12] Nesting Validator                   → NestingValidationReport
  ↓
[13] Topological Assembler               → Stage2Output (enhanced)
```

### Updated Stage2PipelineConfig

```python
class Stage2PipelineConfig(BaseModel):
    # Existing processing units
    parser: type = Field(default=MarkdownItParser)
    classifier: type = Field(default=LayerClassifier)
    hierarchy_builder: type = Field(default=HierarchyBuilder)
    component_mapper: type = Field(default=ComponentMapper)

    # NEW: Aggregation units
    detector_correlator: type = Field(default=DetectorCorrelator)
    token_range_aggregator: type = Field(default=TokenRangeAggregator)
    table_aggregator: type = Field(default=TableAggregator)
    list_aggregator: type = Field(default=ListAggregator)
    codeblock_aggregator: type = Field(default=CodeBlockAggregator)
    heading_sequence_analyzer: type = Field(default=HeadingSequenceAnalyzer)
    indentation_analyzer: type = Field(default=IndentationAnalyzer)
    nesting_validator: type = Field(default=NestingValidator)
    topology_assembler: type = Field(default=TopologyAssembler)

    # NLP configuration (default = enabled)
    enable_spacy: bool = Field(default=True)
    enable_embeddings: bool = Field(default=True)
    spacy_model: str = Field(default="en_core_web_sm")
    embedding_model: str = Field(default="e5-small")
```

---

## 8. NLP Dependencies

### spaCy (default, not optional)

| Property | Value |
|----------|-------|
| Model | `en_core_web_sm` |
| Size | ~12MB |
| CPU Performance | ~5ms per heading |
| Already in Prism | ✅ Yes (Stage 1 dependency) |
| Purpose | POS tagging for heading-like detection |

### e5-small via fastembed (default, not optional)

| Property | Value |
|----------|-------|
| Model | `BAAI/bge-small-en-v1.5` (via e5-small) |
| Size | ~235MB |
| CPU Performance | ~50ms per text pair |
| Already in Prism | ✅ Yes (Stage 3 dependency) |
| Purpose | Semantic similarity for cross-detector correlation |

### Performance Impact

| Operation | Cost |
|-----------|------|
| spaCy: 10 headings | ~50ms |
| e5-small: 10 correlation pairs | ~200ms |
| **Total NLP overhead** | **~250ms per document** |

---

## 9. LangGraph Subgraph Integration

### Updated State Model

```python
class Stage2GraphState(BaseModel):
    # Existing fields
    source_text: str = ""
    nodes: list[MarkdownNode] = []
    report: DetectedLayersReport | None = None
    tree: HierarchyTree | None = None
    components: list[PhysicalComponent] = []
    token_mapping: dict[str, list[str]] = {}
    stage2_output: Stage2Output | None = None
    errors: list[str] = []
    current_step: str = "init"
    retry_count: dict[str, int] = {}

    # NEW: Aggregation fields
    correlated_report: CorrelatedReport | None = None
    heading_sequence: HeadingSequenceReport | None = None
    table_indices: dict[str, TableIndex] = {}
    list_indices: dict[str, ListIndex] = {}
    codeblock_indices: dict[str, CodeBlockIndex] = {}
    token_range_index: TokenRangeIndex | None = None
    indentation_pattern: IndentationPattern | None = None
    nesting_validation: NestingValidationReport | None = None
```

### Updated Graph Topology

```
START → parse → validate_parser → classify → correlate → validate_correlate
    → build_hierarchy → validate_hierarchy → map_components → validate_mapper
    → map_tokens → aggregate_ranges → aggregate_tables → aggregate_lists
    → aggregate_codeblocks → analyze_headings → analyze_indentation
    → validate_nesting → assemble_topology → validate_topology → END
```

---

## 10. Testing Strategy

### Unit Tests (per aggregator)

| Aggregator | Test Count | Focus |
|------------|-----------|-------|
| Table | 10+ | AST parsing, matrix building, header detection |
| List | 10+ | Nesting depth, item counting, tree building |
| CodeBlock | 8+ | Line counting, language detection, indentation |
| TokenRange | 12+ | Forward mapping, reverse mapping, gap detection |
| HeadingSequence | 15+ | Valid sequences, violations, spaCy POS, grouping |
| DetectorCorrelation | 15+ | Caption detection, diagram detection, conflicts |
| Indentation | 8+ | Pattern detection, anomaly flagging |
| NestingValidator | 10+ | Valid nesting, violations, cycle detection |
| TopologyAssembler | 5+ | Assembly completeness, field population |

### Integration Tests

| Test | Count | Focus |
|------|-------|-------|
| Full aggregation pipeline | 3 | End-to-end with sample documents |
| NLP-enhanced pipeline | 3 | With spaCy and e5-small enabled |
| Performance benchmarks | 2 | Overhead measurement |

### Total Expected Tests: **~100+**

---

## 11. Implementation Order

```
Phase 4a: Rules-based aggregators (B1-B7)
  1. token_range_aggregator.py + tests
  2. table_aggregator.py + tests
  3. list_aggregator.py + tests
  4. codeblock_aggregator.py + tests
  5. indentation_analyzer.py + tests
  6. nesting_validator.py + tests
  7. topology_assembler.py + tests

Phase 4b: NLP-enhanced aggregators (A1-A2)
  8. heading_sequence.py + tests (spaCy integration)
  9. detector_correlation.py + tests (e5-small integration)

Phase 4c: Integration
  10. protocols.py (IAggregator definitions)
  11. pipeline_models.py (aggregation wrapper models)
  12. pipeline_config.py (aggregation config)
  13. pipeline.py (updated orchestrator)
  14. graph/ (updated state, nodes, edges, builder)
  15. Full regression suite (909+ tests)
```

---

## 12. Schema Updates Required

### HeadingComponent (enhanced)

```python
class HeadingComponent(BaseModel):
    # Existing
    component_id: str
    layer_type: LayerType = LayerType.HEADING
    raw_content: str
    char_start: int
    char_end: int
    level: int
    text: str
    anchor_id: str

    # NEW
    parent_heading_id: str | None = None          # ID of parent heading
    heading_path: list[str] = []                   # [h1_id, h2_id, current_id]
    sequence_position: int = 0                     # Position in document sequence
    indentation: int = 0                           # Leading spaces
    confidence: float = 1.0                        # spaCy-enhanced confidence
    is_violation: bool = False                     # Has sequence violation
    violation_type: str | None = None              # "skip" | "jump_back"
```

### TableComponent (enhanced)

```python
class TableComponent(BaseModel):
    # Existing
    component_id: str
    layer_type: LayerType = LayerType.TABLE
    raw_content: str
    char_start: int
    char_end: int
    rows: list[TableRow]
    num_cols: int
    has_header: bool

    # NEW
    caption: str | None = None                     # Correlated caption text
    caption_id: str | None = None                  # ID of correlated paragraph
    cell_matrix: list[list[dict]] = []             # 2D cell metadata
    merged_cells: list[tuple] = []                 # Merged cell ranges
```

### Stage2Output (enhanced)

```python
class Stage2Output(BaseModel):
    # Existing
    discovered_layers: dict[str, PhysicalComponent]
    layer_types: set[LayerType]
    is_single_layer: bool
    component_to_tokens: dict[str, tuple[int, int]]

    # NEW
    heading_sequence: HeadingSequenceReport | None = None
    correlations: CorrelatedReport | None = None
    table_indices: dict[str, TableIndex] = {}
    list_indices: dict[str, ListIndex] = {}
    codeblock_indices: dict[str, CodeBlockIndex] = {}
    token_range_index: TokenRangeIndex | None = None
    indentation_pattern: IndentationPattern | None = None
    nesting_validation: NestingValidationReport | None = None
```

---

## 13. Summary

| Category | Tasks | Files | Tests | Reliability |
|----------|-------|-------|-------|-------------|
| **NLP-Enhanced** | 2 | 2 | 30+ | 95-98%+ |
| **Rules/Regex** | 7 | 7 | 70+ | 90-100% |
| **Integration** | 4 | 4 | 5+ | 100% |
| **TOTAL** | **13** | **13** | **105+** | |

**Key Decisions:**
- spaCy and e5-small are **default, not optional**
- Accuracy > Speed (250ms NLP overhead is acceptable)
- All existing aggregation logic is preserved, new logic is additive
- No new dependencies (both NLP libraries already in Prism)
