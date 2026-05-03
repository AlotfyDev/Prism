# TASKS — Prism Implementation: Atomic Task List

> Each task is completable in a single focused session. Tasks are ordered by dependency.

---

## Phase P0: Foundation — Scaffolding, Schemas, Contracts

### Task P0.1: Project Scaffold & Dependencies

**Description:** Create the project directory structure, `pyproject.toml`, virtual environment, and install all dependencies.

**Acceptance Criteria:**
- [ ] `pyproject.toml` with all dependencies defined
- [ ] Virtual environment created and activated
- [ ] All dependencies installable (`pip install -e .`)
- [ ] `prism/` package with `__init__.py`
- [ ] `tests/` directory with `conftest.py`
- [ ] `data/models/` contains bundled e5-base and e5-small

**Verify:**
```bash
cd D:\MCPs\Prism
python -m venv .venv
.venv\Scripts\pip install -e .
.venv\Scripts\python -c "import prism; print(prism.__version__)"
```

**Files:**
- `pyproject.toml`
- `prism/__init__.py`
- `tests/__init__.py`
- `tests/conftest.py`

**Dependencies:** None (first task)

---

### Task P0.2: Pydantic Schema Models — Token & Metadata

**Description:** Define Pydantic models for Stage 1 schemas (Token, TokenMetadata, Stage1Input, Stage1Output).

**Acceptance Criteria:**
- [ ] `Token` model with id (T{n} pattern), text, lemma, pos, ner_label
- [ ] `TokenMetadata` model with token_id, char_start, char_end, source_line, bounding_box
- [ ] `TokenizationConfig` model with tokenizer, include_whitespace, language
- [ ] `Stage1Input` model with source, source_type, config
- [ ] `Stage1Output` model with tokens dict, metadata dict, source_text
- [ ] All models have validation (field patterns, required fields, type checks)
- [ ] Unit tests for each model (valid input, invalid input)

**Verify:**
```bash
.venv\Scripts\pytest tests/test_schemas_tokens.py -v
```

**Files:**
- `prism/schemas/token.py`
- `prism/schemas/__init__.py`
- `tests/test_schemas_tokens.py`

**Dependencies:** P0.1

---

### Task P0.3: Pydantic Schema Models — Physical Component

**Description:** Define Pydantic models for Stage 2 schemas (PhysicalComponent, Stage2Input, Stage2Output).

**Acceptance Criteria:**
- [ ] `PhysicalComponent` model with component_id pattern, layer_type, raw_content, token_span, parent_id, children, attributes
- [ ] `TopologyConfig` model with layer_types_to_detect, nesting_depth_limit
- [ ] `Stage2Input` model referencing Stage1Output + TopologyConfig
- [ ] `Stage2Output` model with discovered_layers, layer_types, is_single_layer, component_to_tokens
- [ ] Validation: component_id pattern matches `{layer_type}:{identifier}`
- [ ] Validation: layer_type is in enum of known types
- [ ] Unit tests for each model

**Verify:**
```bash
.venv\Scripts\pytest tests/test_schemas_physical.py -v
```

**Files:**
- `prism/schemas/physical.py`
- `tests/test_schemas_physical.py`

**Dependencies:** P0.2

---

### Task P0.4: Pydantic Schema Models — Semantic (MiniPG)

**Description:** Define Pydantic models for Stage 3 schemas (MiniTopic, PredicateFrame, Entity, Relationship, MiniPG, SemanticTreeNode, Stage3Input, Stage3Output, SemanticConfig).

**Acceptance Criteria:**
- [ ] `MiniTopic` with topic_id, label, token_span, confidence
- [ ] `PredicateFrame` with predicate, agent, patient, instrument, location, time, source_tokens, source_layer
- [ ] `Entity` with id (E_{TYPE}_{N} pattern), label, mentions, attributes, confidence, source_component
- [ ] `Relationship` with id (R_{N} pattern), source_entity_id, target_entity_id, relation_type (enum), predicate_text, confidence, evidence_tokens, alternative_hypotheses
- [ ] `MiniPG` with layer_id, parent_layer_id, topic_label, mini_topics, entities, predicates, relationships, child_pg_ids
- [ ] `SemanticTreeNode` with node_id, level (enum), children, data_ref
- [ ] `SemanticConfig` with all extractor/provider selections
- [ ] `Stage3Input` and `Stage3Output` models
- [ ] Relation type enum: CAUSES, DEPENDS_ON, PART_OF, LOCATED_IN, TEMPORAL, ARGUMENT_FOR, ARGUMENT_AGAINST, CONDITIONAL, OTHER
- [ ] Unit tests for each model

**Verify:**
```bash
.venv\Scripts\pytest tests/test_schemas_semantic.py -v
```

**Files:**
- `prism/schemas/semantic.py`
- `prism/schemas/enums.py` (RelationType, EntityType, etc.)
- `tests/test_schemas_semantic.py`

**Dependencies:** P0.3

---

### Task P0.5: Pydantic Schema Models — GlobalPG & Config

**Description:** Define Pydantic models for Stage 4 schemas (TopicCluster, GlobalPG, Stage4Input, Stage4Output, AggregationConfig) and the top-level PipelineConfig.

**Acceptance Criteria:**
- [ ] `TopicCluster` with cluster_id, topic_label, component_ids, entities, centroid_embedding
- [ ] `GlobalPG` with entities, relationships, predicates, topic_clusters, confidence_summary, provenance
- [ ] `AggregationConfig` with entity_merge_strategy, conflict_resolution, topic_clustering, confidence_scorer, min_confidence_threshold, embedding_model, llm_provider
- [ ] `Stage4Input` and `Stage4Output` models
- [ ] `PipelineConfig` top-level model combining all stage configs
- [ ] Unit tests for each model

**Verify:**
```bash
.venv\Scripts\pytest tests/test_schemas_global.py -v
```

**Files:**
- `prism/schemas/global.py`
- `prism/schemas/config.py`
- `tests/test_schemas_global.py`

**Dependencies:** P0.4

---

### Task P0.6: ProcessingUnit Abstract Interface

**Description:** Define the abstract `ProcessingUnit` base class that all processing units must implement.

**Acceptance Criteria:**
- [ ] `ProcessingUnit[InputT, OutputT, ConfigT]` abstract class with:
  - `process(input_data, config) -> OutputT`
  - `validate_input(input_data) -> tuple[bool, str]`
  - `validate_output(output_data) -> tuple[bool, str]`
  - `name() -> str`
  - `tier` property (python_nlp, ml, llm)
- [ ] Generic types constrained to Pydantic BaseModel subclasses
- [ ] Concrete stub implementation for testing the interface
- [ ] Unit tests verifying interface contract

**Verify:**
```bash
.venv\Scripts\pytest tests/test_processing_unit.py -v
```

**Files:**
- `prism/core/processing_unit.py`
- `prism/core/__init__.py`
- `tests/test_processing_unit.py`

**Dependencies:** P0.5

---

### Task P0.7: ValidationUnit Abstract Interface

**Description:** Define the abstract `ValidationUnit` base class for inter-stage validation gates.

**Acceptance Criteria:**
- [ ] `ValidationUnit` abstract class with:
  - `validate(data) -> ValidationReport`
  - `name() -> str`
- [ ] `ValidationReport` Pydantic model with stage, passed, timestamp, checks[]
- [ ] `ValidationCheck` model with id, name, passed, severity, message, details
- [ ] Severity enum: critical, warning, info
- [ ] Stub implementations for V0-V4
- [ ] Unit tests

**Verify:**
```bash
.venv\Scripts\pytest tests/test_validation_unit.py -v
```

**Files:**
- `prism/core/validation_unit.py`
- `tests/test_validation_unit.py`

**Dependencies:** P0.6

---

### Task P0.8: Behavioral Test Framework Setup

**Description:** Set up `pytest-bdd` + `hypothesis` for behavioral and property-based testing across all stages.

**Acceptance Criteria:**
- [ ] `pytest-bdd` installed and configured
- [ ] `hypothesis` installed and configured
- [ ] `tests/features/` directory created with base structure
- [ ] `tests/contract/` directory created
- [ ] `tests/property/` directory created
- [ ] `conftest.py` updated with shared BDD step definitions
- [ ] `tests/conftest.py` updated with shared fixtures for property tests
- [ ] Sample `.feature` file created as template

**Verify:**
```bash
.venv\Scripts\pip install pytest-bdd hypothesis
.venv\Scripts\pytest tests/features/ --collect-only
.venv\Scripts\pytest tests/property/ --collect-only
.venv\Scripts\pytest tests/contract/ --collect-only
```

**Files:**
- `tests/features/__init__.py`
- `tests/features/conftest.py`
- `tests/features/stage1_tokenization.feature` (template)
- `tests/contract/__init__.py`
- `tests/contract/conftest.py`
- `tests/property/__init__.py`
- `tests/property/conftest.py`
- `tests/conftest.py` (updated)

**Dependencies:** P0.1

---

## Phase P1: Stage 1 — Holistic Tokenization

### Task P1.1: DocumentConverter Interface + MarkdownLoader

**Description:** Implement the Markdown file loader — reads .md files and returns raw text. Docling is deferred to Phase 2.

**Acceptance Criteria:**
- [ ] `MarkdownLoader` class implements `ProcessingUnit[Stage1Input, str, TokenizationConfig]`
- [ ] Reads file path from Stage1Input.source
- [ ] Returns raw Markdown text string
- [ ] Validates file exists and is readable
- [ ] Raises clear errors for missing/invalid files
- [ ] Unit tests with sample .md files

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage1_loader.py -v
```

**Files:**
- `prism/stage1/__init__.py`
- `prism/stage1/loader.py`
- `tests/fixtures/sample_simple.md`
- `tests/test_stage1_loader.py`

**Dependencies:** P0.7

---

### Task P1.2: TokenStreamBuilder (spaCy)

**Description:** Implement spaCy-based tokenization — converts Markdown text into global sequential token stream (T0, T1, ...).

**Acceptance Criteria:**
- [ ] `SpacyTokenStreamBuilder` implements `ProcessingUnit`
- [ ] Uses spaCy English model (`en_core_web_sm`)
- [ ] Assigns global sequential IDs: T0, T1, T2, ...
- [ ] Populates Token.text for each entry
- [ ] Handles punctuation and whitespace per config
- [ ] Strips Markdown syntax tokens (headings markers, list markers) OR preserves them as metadata
- [ ] spaCy model loaded at startup
- [ ] Unit tests: basic text, multi-paragraph, tables, lists

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage1_tokenizer.py -v
```

**Files:**
- `prism/stage1/tokenizer.py`
- `tests/test_stage1_tokenizer.py`

**Dependencies:** P1.1

---

### Task P1.3: MetadataIndexer

**Description:** Build positional metadata per token — char offsets, source line.

**Acceptance Criteria:**
- [ ] `MetadataIndexer` implements `ProcessingUnit`
- [ ] Maps each token to char_start and char_end in source text
- [ ] Records source_line number
- [ ] Validates: no gaps between consecutive tokens
- [ ] Validates: no overlapping char ranges
- [ ] Validates: full coverage of source text
- [ ] Unit tests with known text → known offsets

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage1_metadata.py -v
```

**Files:**
- `prism/stage1/metadata.py`
- `tests/test_stage1_metadata.py`

**Dependencies:** P1.2

---

### Task P1.4: ValidationV1 — Token Integrity

**Description:** Implement V1 validation checks that run after Stage 1.

**Acceptance Criteria:**
- [ ] `ValidationV1` implements `ValidationUnit`
- [ ] V1.1: Sequential IDs check (no gaps: T0, T1, ... TN)
- [ ] V1.2: No empty tokens
- [ ] V1.3: Metadata completeness (every token has char_start/char_end)
- [ ] V1.4: No overlapping char ranges
- [ ] V1.5: Full coverage warning (all chars covered)
- [ ] Returns ValidationReport with pass/fail per check
- [ ] Critical failures halt pipeline
- [ ] Unit tests with valid and invalid Stage1Output

**Verify:**
```bash
.venv\Scripts\pytest tests/test_validation_v1.py -v
```

**Files:**
- `prism/validation/v1_token_integrity.py`
- `prism/validation/__init__.py`
- `tests/test_validation_v1.py`

**Dependencies:** P1.3

---

### Task P1.5: Behavioral Tests — Stage 1 (Tokenization)

**Description:** Write BDD feature tests and property-based tests for all Stage 1 Processing Units.

**Acceptance Criteria:**
- [ ] BDD feature: `TokenStreamBuilder` — sequential IDs, no gaps, deterministic output
- [ ] BDD feature: `MetadataIndexer` — char coverage, no overlaps, correct offsets
- [ ] BDD feature: `ValidationV1` — passes valid input, rejects invalid input
- [ ] Property test: Any tokenizer produces sequential IDs with no gaps for any non-empty text
- [ ] Property test: Token char ranges never overlap
- [ ] Property test: Token char ranges cover all source characters
- [ ] Contract test: All tokenizer implementations return `Stage1Output` type
- [ ] Contract test: All tokenizer implementations accept valid input and reject invalid

**Verify:**
```bash
.venv\Scripts\pytest tests/features/stage1_tokenization.feature -v
.venv\Scripts\pytest tests/property/test_token_properties.py -v
.venv\Scripts\pytest tests/contract/test_tokenizer_contract.py -v
```

**Files:**
- `tests/features/stage1_tokenization.feature`
- `tests/property/test_token_properties.py`
- `tests/contract/test_tokenizer_contract.py`

**Dependencies:** P1.4, P0.8

---

## Phase P2: Stage 2 — Physical Topology Analyzer

### Task P2.1: MarkdownParser (markdown-it-py)

**Description:** Parse Markdown into AST using markdown-it-py.

**Acceptance Criteria:**
- [ ] `MarkdownItParser` implements `ProcessingUnit`
- [ ] Parses Markdown text into markdown-it-py AST
- [ ] Returns serializable AST with node types: heading, paragraph, table, list, code_block, blockquote, hr, inline
- [ ] Handles nested lists and tables
- [ ] Unit tests with sample Markdown containing all node types

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage2_parser.py -v
```

**Files:**
- `prism/stage2/__init__.py`
- `prism/stage2/parser.py`
- `tests/test_stage2_parser.py`

**Dependencies:** P1.4 (Stage 1 must pass first)

---

### Task P2.2a: Detectors (15 layer types)

**Description:** Implement 15 detector classes — one per physical layer type. Each detector walks the AST and identifies `LayerInstance` objects for its specific layer type.

**Acceptance Criteria:**
- [ ] `LayerDetector` abstract base class with `detect(nodes, source_text) -> list[LayerInstance]`
- [ ] 15 concrete detectors covering all LayerType values:
  - 6 direct AST detection (heading, paragraph, table, list, code_block, blockquote)
  - 2 plugin-based (metadata=front_matter, footnote)
  - 2 rule-based (diagram=mermaid in code_block, figure=images in inline)
  - 5 inline regex-scanning (inline_code, emphasis, link, html_block, html_inline)
- [ ] Each detector registered with `DetectorRegistry` on import
- [ ] Compositional detectors: UnifiedCodeBlockDetector (AST fenced + native indented), UnifiedListDetector (AST + task items), UnifiedLinkDetector (inline/auto + reference), UnifiedHTMLBlockDetector (CommonMark 7 types), UnifiedHTMLInlineDetector (regex + block filtering)
- [ ] Unit tests for each detector

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage2_detectors.py -v
.venv\Scripts\pytest tests/test_inline_detectors.py -v
```

**Files:**
- `prism/stage2/layers/detectors.py` — LayerDetector base + utilities
- `prism/stage2/layers/specific_detectors.py` — All 15 concrete detectors
- `tests/test_stage2_detectors.py`
- `tests/test_inline_detectors.py`

**Dependencies:** P2.1

---

### Task P2.2b: LayerClassifier (Orchestrator)

**Description:** `LayerClassifier` is the main ProcessingUnit for Stage 2. Orchestrates all detectors, collects `LayerInstance` results, and produces `DetectedLayersReport`.

**Acceptance Criteria:**
- [ ] `LayerClassifier` implements `ProcessingUnit[list[MarkdownNode], DetectedLayersReport, TopologyConfig]`
- [ ] Traverses AST once, dispatches each node to all registered detectors
- [ ] Aggregates `LayerInstance` results from all detectors
- [ ] Produces `DetectedLayersReport` (Pydantic) with all detected instances
- [ ] Auto-syncs `detected_types`, provides `instances_of()`, `has_type()`, `layer_counts()` helpers
- [ ] Unit tests with multi-layer Markdown documents

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage2_classifier.py -v
```

**Files:**
- `prism/stage2/classifier.py` — LayerClassifier ProcessingUnit
- `tests/test_stage2_classifier.py`

**Dependencies:** P2.2a

---

### Task P2.2c: HierarchyBuilder

**Description:** Builds parent-child hierarchy tree from detected layer instances using `NestingMatrix` validation rules.

**Acceptance Criteria:**
- [ ] `HierarchyBuilder` implements `ProcessingUnit[DetectedLayersReport, HierarchyTree, TopologyConfig]`
- [ ] Reads `NestingMatrix` rules to determine valid parent-child relationships
- [ ] Builds tree structure with parent references and child lists
- [ ] Validates: no cycles, max_depth respected, leaf types have no children
- [ ] Assigns `depth`, `sibling_index`, `parent_id` to each instance
- [ ] Returns `HierarchyTree` (Pydantic) with validated parent-child structure
- [ ] Unit tests: valid hierarchies, invalid hierarchies (cycles, depth violations, leaf violations)

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage2_hierarchy.py -v
```

**Files:**
- `prism/stage2/hierarchy.py` — HierarchyBuilder + HierarchyTree schema
- `tests/test_stage2_hierarchy.py`

**Dependencies:** P2.2b

---

### Task P2.2d: ComponentMapper

**Description:** Converts `LayerInstance` objects into typed `PhysicalComponent`/`TableComponent`/`ListComponent` objects using CRUD operations.

**Acceptance Criteria:**
- [ ] `ComponentMapper` implements `ProcessingUnit[DetectedLayersReport, list[PhysicalComponent], TopologyConfig]`
- [ ] For each `LayerInstance`, dispatches to correct CRUD via `LayerRegistry.get(layer_type)`
- [ ] Creates typed components: `PhysicalComponent` for simple types, `TableComponent` for tables, `ListComponent` for lists
- [ ] Builds structured sub-elements: Table rows/cells, List items
- [ ] Maps hierarchy parent-child references from string IDs to component references
- [ ] Transfers `char_start/char_end` from LayerInstance to PhysicalComponent (for TokenSpanMapper)
- [ ] Unit tests: each layer type produces correct component type, nested structures preserved

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage2_component_mapper.py -v
```

**Files:**
- `prism/stage2/mapper.py` — ComponentMapper ProcessingUnit
- `tests/test_stage2_component_mapper.py`

**Dependencies:** P2.2c

---

### Task P2.2e: TokenSpanMapper

**Description:** Maps each PhysicalComponent to its global token ID range using `char_start/char_end` and Stage 1 metadata index.

**Acceptance Criteria:**
- [ ] `TokenSpanMapper` implements `ProcessingUnit[list[PhysicalComponent], dict[str, list[str]], TopologyConfig]`
- [ ] For each component, reads `char_start/char_end` from PhysicalComponent
- [ ] Maps char range to global token IDs using `Stage1Output.metadata` index (binary search for efficiency)
- [ ] Populates `PhysicalComponent.token_span` with `(token_start, token_end)` tuple
- [ ] Handles nested components: parent's token span includes all children's tokens
- [ ] Handles edge cases: char span overlaps multiple tokens, partial token coverage
- [ ] Unit tests: verify each component's tokens match expected range

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage2_token_span.py -v
```

**Files:**
- `prism/stage2/token_span.py` — TokenSpanMapper ProcessingUnit
- `tests/test_stage2_token_span.py`

**Dependencies:** P2.2d + Stage 1 output (token metadata)

---

### Task P2.3: TopologyBuilder

**Description:** Assemble final `Stage2Output` from all components and token mappings.

**Acceptance Criteria:**
- [ ] `TopologyBuilder` implements `ProcessingUnit[list[PhysicalComponent], Stage2Output, TopologyConfig]`
- [ ] Groups components by layer type into `discovered_layers` dict
- [ ] Sets `is_single_layer` flag (True if only paragraphs exist)
- [ ] Builds `component_to_tokens` dict from token spans
- [ ] Validates: no empty components, all components have valid IDs, no orphan tokens
- [ ] Unit tests: verify output schema compliance

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage2_topology.py -v
```

**Files:**
- `prism/stage2/topology.py` — TopologyBuilder ProcessingUnit
- `tests/test_stage2_topology.py`

**Dependencies:** P2.2e

---

### Task P2.4: ValidationV2 — Component Integrity

**Description:** Implement V2 validation checks that run after Stage 2.

**Acceptance Criteria:**
- [ ] V2.1: Component ID validity (format: `{layer_type}:{identifier}`)
- [ ] V2.2: Layer type consistency (component_id prefix matches layer_type field)
- [ ] V2.3: Token span consistency (no overlaps between sibling components)
- [ ] V2.4: Parent-child integrity (parent_ids reference existing components, no cycles)
- [ ] V2.5: Nesting validation (parent-child relationships valid per NestingMatrix)
- [ ] V2.6: Component-to-token mapping completeness (all components with spans mapped)
- [ ] Critical severity: V2.1-V2.4 (pipeline halts)
- [ ] Warning severity: V2.5-V2.6 (structural issues)
- [ ] Unit tests with valid and invalid Stage2Output

**Verify:**
```bash
.venv\Scripts\pytest tests/test_validation_v2.py -v
```

**Files:**
- `prism/stage2/validation_v2.py` — ValidationV2
- `tests/test_validation_v2.py`

**Dependencies:** P2.3

---

### Task P2.5: Behavioral Tests — Stage 2 (Physical Topology)

**Description:** Write BDD feature tests and property-based tests for all Stage 2 Processing Units.

**Acceptance Criteria:**
- [ ] BDD feature: `LayerClassifier` — detects all layer types, assigns valid component IDs
- [ ] BDD feature: `HierarchyBuilder` — builds valid tree, detects cycles, respects nesting rules
- [ ] BDD feature: `ComponentMapper` — maps instances to typed components, preserves hierarchy
- [ ] BDD feature: `TokenSpanMapper` — maps tokens correctly, handles nesting
- [ ] BDD feature: `TopologyBuilder` — assembles valid report, correct is_single_layer flag
- [ ] BDD feature: `ValidationV2` — detects unassigned tokens, detects cycles
- [ ] Property test: Every global token appears in at least one component (for complete documents)
- [ ] Property test: Component hierarchy has no cycles for any valid Markdown
- [ ] Contract test: All classifier implementations return `Stage2Output` type
- [ ] Contract test: Component IDs always match `{layer_type}:{identifier}` pattern

**Verify:**
```bash
.venv\Scripts\pytest tests/features/stage2_topology.feature -v
.venv\Scripts\pytest tests/property/test_topology_properties.py -v
.venv\Scripts\pytest tests/contract/test_topology_contract.py -v
```

**Files:**
- `tests/features/stage2_topology.feature`
- `tests/property/test_topology_properties.py`
- `tests/contract/test_topology_contract.py`

**Dependencies:** P2.4, P0.8

---

## Phase P2.7: Stage 2 — TokenSpan Integrity Fix

### Task P2.7a: Add char offsets to PhysicalComponent

**Description:** Add `char_start` and `char_end` fields to `PhysicalComponent` model so TokenSpanMapper can map components to global tokens.

**Acceptance Criteria:**
- [ ] `PhysicalComponent.char_start: int` field added (ge=0)
- [ ] `PhysicalComponent.char_end: int` field added (gt=char_start)
- [ ] All 15 typed component models inherit these fields
- [ ] ComponentMapper transfers `char_start/char_end` from LayerInstance to PhysicalComponent during creation
- [ ] Existing tests updated to provide char offsets
- [ ] Schema version bump if applicable

**Verify:**
```bash
.venv\Scripts\pytest tests/test_schemas_physical.py -v
.venv\Scripts\pytest tests/test_schemas_typed_components.py -v
```

**Files:**
- `prism/schemas/physical.py` — PhysicalComponent + 15 typed models
- `prism/stage2/mapper.py` — ComponentMapper (transfer char offsets)
- `tests/test_schemas_physical.py`
- `tests/test_schemas_typed_components.py`

**Dependencies:** P2.6 (typed components complete)

---

### Task P2.7b: Reorder TokenSpanMapper in pipeline

**Description:** Ensure `TokenSpanMapper` runs before `TopologyBuilder` and receives `Stage1Output` metadata. Fix pipeline ordering so char→token mapping happens correctly.

**Acceptance Criteria:**
- [ ] `TopologyBuilder` receives pre-populated token spans from TokenSpanMapper
- [ ] Pipeline order: ComponentMapper → TokenSpanMapper → TopologyBuilder
- [ ] `TokenSpanMapper` accepts `Stage1Output` as input (for metadata index)
- [ ] Integration test: full Stage 2 pipeline produces valid component_to_tokens

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage2_orchestration.py -v
```

**Files:**
- `prism/stage2/__init__.py` — exports
- `prism/stage2/topology.py` — TopologyBuilder (uses pre-mapped spans)
- `tests/test_stage2_orchestration.py`

**Dependencies:** P2.7a

---

### Task P2.7c: Fix TokenSpanMapper._find_tokens_in_range

**Description:** Rewrite `TokenSpanMapper._find_tokens_in_range` to use component `char_start/char_end` for precise token range lookup via Stage 1 metadata index.

**Acceptance Criteria:**
- [ ] Uses `component.char_start` and `component.char_end` (not estimated range)
- [ ] Binary search or sorted scan over Stage1Output.metadata for efficiency
- [ ] Returns `(token_start_id, token_end_id)` tuple (not list)
- [ ] Handles components with no token overlap (returns None)
- [ ] Handles nested components correctly (parent includes children's tokens)
- [ ] Unit tests with known char ranges → known token IDs

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage2_token_span.py -v
```

**Files:**
- `prism/stage2/token_span.py` — TokenSpanMapper (rewrite _find_tokens_in_range)
- `tests/test_stage2_token_span.py`

**Dependencies:** P2.7a + Stage 1 output (token metadata)

---

## Phase P3: Stage 3 — Semantic Topology Analyzer

### Task P3.1: TopicDetector (heading-based + KeyBERT fallback)

**Description:** Detect topic label for a physical layer — from heading if available, KeyBERT if not.

**Acceptance Criteria:**
- [ ] `TopicDetector` implements `ProcessingUnit`
- [ ] If heading exists for component → use as topic_label
- [ ] If no heading → use KeyBERT to extract top keyword phrase
- [ ] Identifies mini_topics (sub-components like table cells, list items)
- [ ] Each MiniTopic has topic_id, label, token_span, confidence
- [ ] Unit tests with heading components and headingless components

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage3_topic.py -v
```

**Files:**
- `prism/stage3/__init__.py`
- `prism/stage3/topic.py`
- `tests/test_stage3_topic.py`

**Dependencies:** P2.5

---

### Task P3.2: SemanticParagraphSegmenter

**Description:** Detect semantic paragraph units within a physical layer.

**Acceptance Criteria:**
- [ ] `SemanticParagraphSegmenter` implements `ProcessingUnit`
- [ ] Default: 1 physical paragraph = 1 semantic unit
- [ ] If paragraph > 150 words + discourse markers → split
- [ ] Discourse markers: however, therefore, furthermore, in contrast, on the other hand
- [ ] Table cells = individual semantic units
- [ ] List items = individual semantic units
- [ ] Each unit has unit_id, token_span, component_id, confidence
- [ ] Unit tests

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage3_segmenter.py -v
```

**Files:**
- `prism/stage3/segmenter.py`
- `tests/test_stage3_segmenter.py`

**Dependencies:** P3.1

---

### Task P3.3: PredicateExtractor (Stanza SRL)

**Description:** Extract predicate frames from semantic units using Stanza SRL.

**Acceptance Criteria:**
- [ ] `StanzaPredicateExtractor` implements `ProcessingUnit`
- [ ] Uses Stanza English pipeline with SRL processor
- [ ] Extracts PROPBANK predicate frames per sentence
- [ ] Maps each frame to PredicateFrame schema (predicate, agent, patient, instrument, location, time)
- [ ] Maps source tokens to global token IDs
- [ ] Handles sentences with no predicates (returns empty list)
- [ ] Handles sentences with multiple predicates
- [ ] Stanza model loaded at startup
- [ ] Unit tests with known sentences → known frames

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage3_predicate.py -v
```

**Files:**
- `prism/stage3/predicate.py`
- `tests/test_stage3_predicate.py`

**Dependencies:** P3.2

---

### Task P3.4: EntityExtractor (spaCy NER + GLiNER fallback)

**Description:** Extract entities within layer scope using spaCy NER, with GLiNER for zero-shot labels.

**Acceptance Criteria:**
- [ ] `SpacyEntityExtractor` implements `ProcessingUnit`
- [ ] Uses spaCy NER to extract entities
- [ ] Maps spaCy entities to Prism Entity schema (id, label, mentions, confidence, source_component)
- [ ] Assigns entity IDs with pattern E_{TYPE}_{N}
- [ ] Maps entity mentions to global token IDs
- [ ] `GLiNEREntityExtractor` as alternative implementation (same interface)
- [ ] Config selects which extractor to use
- [ ] Unit tests with known text → known entities

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage3_entity.py -v
```

**Files:**
- `prism/stage3/entity.py`
- `tests/test_stage3_entity.py`

**Dependencies:** P3.2

---

### Task P3.5: EntityResolver (Stanza Coref)

**Description:** Resolve entity ambiguity within layer scope — merge duplicate mentions using Stanza coref.

**Acceptance Criteria:**
- [ ] `StanzaEntityResolver` implements `ProcessingUnit`
- [ ] Uses Stanza coref pipeline
- [ ] Merges entity mentions that refer to same entity
- [ ] Assigns unified entity ID to merged mentions
- [ ] Handles pronouns (he, she, it, they)
- [ ] Confidence based on coref cluster quality
- [ ] Stanza coref loaded at startup
- [ ] Unit tests with text containing coreferences

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage3_resolver.py -v
```

**Files:**
- `prism/stage3/resolver.py`
- `tests/test_stage3_resolver.py`

**Dependencies:** P3.4

---

### Task P3.6: RelationshipExtractor (LLM-first)

**Description:** Extract relationships between resolved entities — LLM is primary, patterns as fallback.

**Acceptance Criteria:**
- [ ] `LLMRelationshipExtractor` implements `ProcessingUnit`
- [ ] Sends entities + context to LLM provider with constrained prompt (fixed relation taxonomy)
- [ ] Parses LLM response into Relationship objects
- [ ] Validates all relation types are in canonical taxonomy
- [ ] Maps evidence to global token IDs
- [ ] `PatternRelationshipExtractor` as fallback implementation
- [ ] Dependency tree patterns: nsubj→ROOT→dobj, nmod→nmod
- [ ] Predefined taxonomy + regex patterns per relation type
- [ ] Config selects primary/fallback
- [ ] Unit tests with known entity pairs → known relations

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage3_relationship.py -v
```

**Files:**
- `prism/stage3/relationship.py`
- `tests/test_stage3_relationship.py`

**Dependencies:** P3.5, P3.3 (needs resolved entities + predicates)

---

### Task P3.7: MiniPGBuilder

**Description:** Assemble all Stage 3 outputs into a MiniPG object.

**Acceptance Criteria:**
- [ ] `MiniPGBuilder` implements `ProcessingUnit`
- [ ] Takes: topic_label, mini_topics, entities, predicates, relationships
- [ ] Validates: entity IDs unique, all relationship refs valid, all token refs valid
- [ ] Assigns layer_id and parent_layer_id
- [ ] Unit tests: valid assembly, invalid assembly (duplicate entities, bad refs)

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage3_minipg.py -v
```

**Files:**
- `prism/stage3/minipg.py`
- `tests/test_stage3_minipg.py`

**Dependencies:** P3.1, P3.3, P3.5, P3.6

---

### Task P3.8: ValidationV3 — Mini-PG Completeness

**Description:** Implement V3 validation checks that run after Stage 3 (per layer).

**Acceptance Criteria:**
- [ ] V3.1: Topic exists (non-empty topic_label)
- [ ] V3.2: Unique entity IDs within MiniPG
- [ ] V3.3: Valid entity refs in relationships
- [ ] V3.4: Valid token refs (all are Stage 1 IDs)
- [ ] V3.5: Valid child_pg refs
- [ ] Unit tests

**Verify:**
```bash
.venv\Scripts\pytest tests/test_validation_v3.py -v
```

**Files:**
- `prism/validation/v3_minipg_completeness.py`
- `tests/test_validation_v3.py`

**Dependencies:** P3.7

---

### Task P3.9: Behavioral Tests — Stage 3 (Semantic Analysis)

**Description:** Write BDD feature tests and property-based tests for all Stage 3 Processing Units.

**Acceptance Criteria:**
- [ ] BDD feature: `TopicDetector` — heading extraction, KeyBERT fallback
- [ ] BDD feature: `SemanticParagraphSegmenter` — splits on discourse markers, cells = units
- [ ] BDD feature: `PredicateExtractor` — extracts predicates, maps to schema
- [ ] BDD feature: `EntityExtractor` — extracts entities, assigns IDs, maps mentions
- [ ] BDD feature: `EntityResolver` — merges coreferences, assigns unified IDs
- [ ] BDD feature: `RelationshipExtractor` — extracts typed relations, evidence mapping
- [ ] BDD feature: `ValidationV3` — detects duplicates, invalid refs
- [ ] Property test: All entity IDs within a MiniPG are unique
- [ ] Property test: All relationship source/target refs exist in the same MiniPG
- [ ] Property test: All token refs in predicates are valid Stage 1 IDs
- [ ] Contract test: All extractor implementations produce valid MiniPG schema
- [ ] Contract test: LLM-based extractors constrain output to relation type taxonomy

**Verify:**
```bash
.venv\Scripts\pytest tests/features/stage3_semantic.feature -v
.venv\Scripts\pytest tests/property/test_semantic_properties.py -v
.venv\Scripts\pytest tests/contract/test_semantic_contract.py -v
```

**Files:**
- `tests/features/stage3_semantic.feature`
- `tests/property/test_semantic_properties.py`
- `tests/contract/test_semantic_contract.py`

**Dependencies:** P3.8, P0.8

---

## Phase P4: Stage 4 — Aggregation Layer

### Task P4.1: CrossLayerEntityResolver

**Description:** Merge same entities across multiple physical layers into global entities.

**Acceptance Criteria:**
- [ ] `CrossLayerEntityResolver` implements `ProcessingUnit`
- [ ] Takes all MiniPG entities from Stage 3
- [ ] Uses e5-base embeddings for entity similarity matching
- [ ] Merges entities with same label + high similarity + overlapping mentions
- [ ] Assigns global entity ID
- [ ] Merges mentions from all layers
- [ ] Tracks which layers each entity appears in
- [ ] Aggregates confidence scores
- [ ] e5-base model loaded at startup
- [ ] Unit tests with entities appearing in multiple layers

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage4_crosslayer_er.py -v
```

**Files:**
- `prism/stage4/__init__.py`
- `prism/stage4/crosslayer_er.py`
- `tests/test_stage4_crosslayer_er.py`

**Dependencies:** P3.8

---

### Task P4.2: MiniPGMerger

**Description:** Union all MiniPG elements into a draft GlobalPG.

**Acceptance Criteria:**
- [ ] `MiniPGMerger` implements `ProcessingUnit`
- [ ] Unions all entities (using merged global entities from P4.1)
- [ ] Unions all relationships
- [ ] Unions all predicates
- [ ] Preserves provenance (which MiniPG produced each element)
- [ ] Remaps entity IDs from local to global
- [ ] Unit tests

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage4_merger.py -v
```

**Files:**
- `prism/stage4/merger.py`
- `tests/test_stage4_merger.py`

**Dependencies:** P4.1

---

### Task P4.3: ConflictResolver

**Description:** Resolve contradictory relationships using confidence-weighted voting.

**Acceptance Criteria:**
- [ ] `ConflictResolver` implements `ProcessingUnit`
- [ ] Detects contradictory relationships (same source+target, different relation_type)
- [ ] Applies formula: `score = confidence × (evidence_tokens / max_tokens_in_layer)`
- [ ] Tiebreaker: richer layer > more predicates > both kept at 0.7× confidence
- [ ] Stores alternatives in `alternative_hypotheses`
- [ ] Unit tests with known conflicts

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage4_conflict.py -v
```

**Files:**
- `prism/stage4/conflict.py`
- `tests/test_stage4_conflict.py`

**Dependencies:** P4.2

---

### Task P4.4: CrossLayerLinker

**Description:** Detect causal/argument/conditional relationships spanning multiple layers.

**Acceptance Criteria:**
- [ ] `CrossLayerLinker` implements `ProcessingUnit`
- [ ] Discourse marker patterns: because, since, therefore, thus, consequently
- [ ] Predicate frame chaining: predicate_A(patient) == predicate_B(agent)
- [ ] LLM-based implicit causality detection (fallback)
- [ ] Adds new cross-layer relationships with cross-layer provenance
- [ ] Assigns confidence
- [ ] Unit tests with multi-layer causal chains

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage4_linker.py -v
```

**Files:**
- `prism/stage4/linker.py`
- `tests/test_stage4_linker.py`

**Dependencies:** P4.2

---

### Task P4.5: TopicClusterer

**Description:** Cluster semantically related paragraphs across different layers into topic clusters.

**Acceptance Criteria:**
- [ ] `TopicClusterer` implements `ProcessingUnit`
- [ ] Uses e5-base embeddings for all layer content
- [ ] Clusters using cosine similarity + hierarchical clustering
- [ ] Assigns cluster topic labels (from most representative layer's topic)
- [ ] Calculates centroid embedding
- [ ] Links entities to clusters
- [ ] Unit tests with known related paragraphs

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage4_clustering.py -v
```

**Files:**
- `prism/stage4/clustering.py`
- `tests/test_stage4_clustering.py`

**Dependencies:** P4.2

---

### Task P4.6: ConfidenceScorer

**Description:** Assign and aggregate confidence scores to all global graph elements.

**Acceptance Criteria:**
- [ ] `ConfidenceScorer` implements `ProcessingUnit`
- [ ] Aggregates per-element confidence from all layers
- [ ] Tier-based weighting: spaCy=1.0, Stanza=0.95, LLM=0.7
- [ ] Evidence-based scaling: `confidence × log(evidence_count+1) / log(max+1)`
- [ ] Generates confidence_summary (entity_avg, relationship_avg, predicate_avg, counts)
- [ ] Filters below min_confidence_threshold
- [ ] Unit tests

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage4_confidence.py -v
```

**Files:**
- `prism/stage4/confidence.py`
- `tests/test_stage4_confidence.py`

**Dependencies:** P4.3, P4.4, P4.5

---

### Task P4.7: GlobalPGBuilder

**Description:** Assemble final Global Property Graph from all merged components.

**Acceptance Criteria:**
- [ ] `GlobalPGBuilder` implements `ProcessingUnit`
- [ ] Takes merged entities, resolved relationships, all predicates, clusters, confidence
- [ ] Validates: no duplicate entities, all refs valid, provenance complete
- [ ] Generates final GlobalPG matching Stage4Output schema
- [ ] Unit tests

**Verify:**
```bash
.venv\Scripts\pytest tests/test_stage4_globalpg.py -v
```

**Files:**
- `prism/stage4/globalpg.py`
- `tests/test_stage4_globalpg.py`

**Dependencies:** P4.6

---

### Task P4.8: ValidationV4 — Merge Consistency

**Description:** Implement V4 validation checks that run after Stage 4.

**Acceptance Criteria:**
- [ ] V4.1: No duplicate entities
- [ ] V4.2: All conflicts resolved
- [ ] V4.3: Provenance complete
- [ ] V4.4: Confidence consistency
- [ ] V4.5: Valid relationship refs
- [ ] Unit tests

**Verify:**
```bash
.venv\Scripts\pytest tests/test_validation_v4.py -v
```

**Files:**
- `prism/validation/v4_merge_consistency.py`
- `tests/test_validation_v4.py`

**Dependencies:** P4.7

---

### Task P4.9: Behavioral Tests — Stage 4 (Aggregation)

**Description:** Write BDD feature tests and property-based tests for all Stage 4 Processing Units.

**Acceptance Criteria:**
- [ ] BDD feature: `CrossLayerEntityResolver` — merges same entities across layers
- [ ] BDD feature: `MiniPGMerger` — unions elements, preserves provenance
- [ ] BDD feature: `ConflictResolver` — resolves contradictions, stores alternatives
- [ ] BDD feature: `CrossLayerLinker` — detects causal chains, arguments across layers
- [ ] BDD feature: `TopicClusterer` — clusters related paragraphs, assigns labels
- [ ] BDD feature: `ConfidenceScorer` — aggregates scores, filters below threshold
- [ ] BDD feature: `ValidationV4` — detects duplicates, incomplete provenance
- [ ] Property test: No duplicate entities in GlobalPG after cross-layer ER
- [ ] Property test: All conflict pairs have exactly one primary + stored alternatives
- [ ] Property test: Confidence summary values are consistent with individual scores
- [ ] Property test: Provenance covers every entity and relationship
- [ ] Contract test: All merger implementations produce valid `GlobalPG` schema
- [ ] Contract test: Conflict resolution formula is deterministic for same input

**Verify:**
```bash
.venv\Scripts\pytest tests/features/stage4_aggregation.feature -v
.venv\Scripts\pytest tests/property/test_aggregation_properties.py -v
.venv\Scripts\pytest tests/contract/test_aggregation_contract.py -v
```

**Files:**
- `tests/features/stage4_aggregation.feature`
- `tests/property/test_aggregation_properties.py`
- `tests/contract/test_aggregation_contract.py`

**Dependencies:** P4.8, P0.8

---

## Phase P5: Orchestration & Infrastructure

### Task P5.1: LLM Provider Abstraction

**Description:** Implement the LLM provider interface with priority chain (OpenCode → KiloCode → Cline → Codex → OpenRouter).

**Acceptance Criteria:**
- [ ] `LLMProvider` abstract base class with `complete(prompt, system_prompt) -> str`
- [ ] `OpenCodeProvider`, `KiloCodeProvider`, `ClineProvider`, `CodexProvider`, `OpenRouterProvider` implementations
- [ ] `LLMRouter` with priority chain and automatic fallback
- [ ] Each provider logs calls to local metrics store
- [ ] Configurable via PipelineConfig
- [ ] Unit tests with mock providers

**Verify:**
```bash
.venv\Scripts\pytest tests/test_llm_provider.py -v
```

**Files:**
- `prism/llm/__init__.py`
- `prism/llm/provider.py`
- `prism/llm/providers/opencode.py`
- `prism/llm/providers/kilocode.py`
- `prism/llm/providers/cline.py`
- `prism/llm/providers/codex.py`
- `prism/llm/providers/openrouter.py`
- `prism/llm/router.py`
- `tests/test_llm_provider.py`

**Dependencies:** P0.6

---

### Task P5.2: Embedding Engine (fastembed)

**Description:** Initialize fastembed with bundled ONNX models (e5-base, e5-small).

**Acceptance Criteria:**
- [ ] `EmbeddingEngine` class loads bundled models from `data/models/`
- [ ] Supports e5-base (768d) and e5-small (384d)
- [ ] `embed(texts: list[str]) -> list[np.ndarray]`
- [ ] `similarity(text_a, text_b) -> float` (cosine)
- [ ] Models loaded at startup
- [ ] Unit tests with known text pairs → known similarity

**Verify:**
```bash
.venv\Scripts\pytest tests/test_embedding.py -v
```

**Files:**
- `prism/embedding/__init__.py`
- `prism/embedding/engine.py`
- `tests/test_embedding.py`

**Dependencies:** P0.1

---

### Task P5.3: Local Observability (Logging + SQLite)

**Description:** Implement structured logging and local SQLite metrics store.

**Acceptance Criteria:**
- [ ] structlog configured with JSON output
- [ ] `PipelineMetrics` dataclass with stage, duration_ms, tokens, llm_calls, errors, timestamp
- [ ] `LocalMetricsStore` with SQLite backend
- [ ] Records metrics per stage execution
- [ ] Query API: get metrics by stage, by time range, error summary
- [ ] Log rotation and file size limits
- [ ] Unit tests

**Verify:**
```bash
.venv\Scripts\pytest tests/test_observability.py -v
```

**Files:**
- `prism/observability/__init__.py`
- `prism/observability/logging.py`
- `prism/observability/metrics.py`
- `tests/test_observability.py`

**Dependencies:** P0.1

---

### Task P5.4: LangGraph Pipeline Orchestrator

**Description:** Build the LangGraph StateGraph that wires all stages together.

**Acceptance Criteria:**
- [ ] `PrismState` Pydantic model as LangGraph state
- [ ] Graph nodes for: tokenize, validate_v1, topology, validate_v2, fan_out, analyze_layer (per layer), fan_in, aggregate, validate_v4
- [ ] Conditional edges for validation pass/fail → continue or halt
- [ ] Fan-out/fan-in for parallel Stage 3 layer analysis
- [ ] SQLite checkpointer for resume capability
- [ ] `PipelineOrchestrator` class with `run(source, source_type) -> GlobalPG`
- [ ] Error handling per unit → fallback routing
- [ ] Integration test with sample document

**Verify:**
```bash
.venv\Scripts\pytest tests/test_orchestrator.py -v
```

**Files:**
- `prism/orchestrator/__init__.py`
- `prism/orchestrator/state.py`
- `prism/orchestrator/graph.py`
- `prism/orchestrator/nodes.py`
- `prism/orchestrator/orchestrator.py`
- `tests/test_orchestrator.py`

**Dependencies:** P1.4, P2.5, P3.8, P4.8, P5.1, P5.2, P5.3

---

### Task P5.5: PipelineConfig Loader

**Description:** Load and validate pipeline configuration from YAML/JSON/TOML.

**Acceptance Criteria:**
- [ ] `ConfigLoader` reads pipeline.yaml
- [ ] Validates against PipelineConfig Pydantic model
- [ ] Defaults for all optional fields
- [ ] Environment variable overrides
- [ ] Clear error messages for invalid config
- [ ] Sample config file included
- [ ] Unit tests

**Verify:**
```bash
.venv\Scripts\pytest tests/test_config.py -v
```

**Files:**
- `prism/config/__init__.py`
- `prism/config/loader.py`
- `config/pipeline.yaml` (sample)
- `tests/test_config.py`

**Dependencies:** P0.5

---

### Task P5.6: Contract Tests — ProcessingUnit Interface

**Description:** Write contract tests that verify ANY ProcessingUnit implementation satisfies the abstract interface contract.

**Acceptance Criteria:**
- [ ] Contract test: All ProcessingUnits return correct output type for `process()`
- [ ] Contract test: All ProcessingUnits validate valid input as `True`
- [ ] Contract test: All ProcessingUnits validate invalid input as `False`
- [ ] Contract test: All ProcessingUnits return non-empty name string
- [ ] Contract test: All ProcessingUnits have valid tier value
- [ ] Contract test: All ValidationUnits return `ValidationReport` type
- [ ] Contract test: All LLM Providers return string for `complete()`
- [ ] Test matrix: runs every concrete implementation through the same contract checks
- [ ] CI: contract tests run before unit tests (fail fast if contract broken)

**Verify:**
```bash
.venv\Scripts\pytest tests/contract/test_processing_unit_contract.py -v
.venv\Scripts\pytest tests/contract/test_validation_unit_contract.py -v
.venv\Scripts\pytest tests/contract/test_llm_provider_contract.py -v
```

**Files:**
- `tests/contract/test_processing_unit_contract.py`
- `tests/contract/test_validation_unit_contract.py`
- `tests/contract/test_llm_provider_contract.py`

**Dependencies:** P0.6, P0.7, P5.1

---

### Task P5.7: Property-Based Tests — Schema Invariants

**Description:** Write property-based tests that verify schema invariants hold for ANY valid input.

**Acceptance Criteria:**
- [ ] Property test: Token IDs are always sequential (T0, T1, ... TN) for any input text
- [ ] Property test: Token char ranges never overlap for any input
- [ ] Property test: Component IDs always match pattern for any Markdown
- [ ] Property test: Entity IDs always match pattern for any extracted entities
- [ ] Property test: Relationship types are always in taxonomy for any relation
- [ ] Property test: Confidence values are always in [0.0, 1.0] range
- [ ] Property test: Provenance is always complete for any merged GlobalPG
- [ ] Uses `hypothesis` strategies to generate random valid/invalid inputs
- [ ] Edge cases: empty text, single token, massive document (10K+ tokens)

**Verify:**
```bash
.venv\Scripts\pytest tests/property/test_schema_invariants.py -v
.venv\Scripts\pytest tests/property/test_graph_properties.py -v
```

**Files:**
- `tests/property/test_schema_invariants.py`
- `tests/property/test_graph_properties.py`
- `tests/property/strategies.py` (Hypothesis strategies for Prism types)

**Dependencies:** P0.5, P0.8

---

## Phase P6: CLI, Tests, & Benchmark

### Task P6.1: CLI Entry Point

**Description:** Create CLI tool for running the pipeline on documents.

**Acceptance Criteria:**
- [ ] `prism run <file>` — runs full pipeline
- [ ] `prism run <file> --stage <stage_id>` — runs specific stage
- [ ] `prism config` — shows current config
- [ ] `prism validate <file>` — validates document without processing
- [ ] Output: JSON graph, or pretty-printed summary
- [ ] `--verbose` flag for detailed logging
- [ ] `--output <path>` for output file
- [ ] Uses argparse or click
- [ ] Unit tests for CLI commands

**Verify:**
```bash
.venv\Scripts\python -m prism run tests/fixtures/sample_simple.md
```

**Files:**
- `prism/cli/__init__.py`
- `prism/cli/main.py`
- `prism/__main__.py`
- `tests/test_cli.py`

**Dependencies:** P5.4

---

### Task P6.2: Benchmark Documents

**Description:** Create test documents for end-to-end validation.

**Acceptance Criteria:**
- [ ] `tests/benchmarks/simple.md` — single paragraph, known entities
- [ ] `tests/benchmarks/multi_layer.md` — paragraphs + tables + lists
- [ ] `tests/benchmarks/causal.md` — document with explicit causal relationships
- [ ] `tests/benchmarks/arguments.md` — document with premise/conclusion structure
- [ ] `tests/benchmarks/coref.md` — document with pronouns and references
- [ ] Expected output (gold standard) for each benchmark
- [ ] Benchmark runner script

**Verify:**
```bash
.venv\Scripts\python -m prism benchmark
```

**Files:**
- `tests/benchmarks/*.md`
- `tests/benchmarks/expected/*.json`
- `tests/test_benchmarks.py`

**Dependencies:** P5.4, P6.1

---

### Task P6.3: End-to-End Integration Tests

**Description:** Run full pipeline on all benchmark documents and validate output.

**Acceptance Criteria:**
- [ ] Each benchmark document runs end-to-end without errors
- [ ] Output matches expected gold standard (entity count, relationship count, topic clusters)
- [ ] Performance metrics recorded (duration, memory, LLM calls)
- [ ] All validation gates pass (V1-V4)
- [ ] Test report generated

**Verify:**
```bash
.venv\Scripts\pytest tests/test_e2e.py -v --tb=short
```

**Files:**
- `tests/test_e2e.py`

**Dependencies:** P6.2

### Task P6.4: E2E per Stage — Independent Stage Validation

**Description:** Run each stage independently with mock inputs and validate outputs match expected behavior, before full pipeline E2E.

**Acceptance Criteria:**
- [ ] Stage 1 E2E: Raw Markdown → valid Stage1Output with correct tokens and metadata
- [ ] Stage 2 E2E: Stage1Output → valid Stage2Output with correct layer classification
- [ ] Stage 3 E2E: Stage2Output + Stage1Output → valid Stage3Output with MiniPGs
- [ ] Stage 4 E2E: Stage3Output + Stage1Output → valid Stage4Output with GlobalPG
- [ ] Each stage E2E runs WITHOUT the orchestrator (isolated execution)
- [ ] Each stage E2E validates against its schema
- [ ] Each stage E2E records performance metrics (duration, memory)
- [ ] Per-stage E2E catches which stage fails (before full pipeline E2E)
- [ ] Test report shows per-stage pass/fail

**Verify:**
```bash
.venv\Scripts\pytest tests/e2e/test_e2e_per_stage.py -v --tb=short
```

**Files:**
- `tests/e2e/test_e2e_per_stage.py`
- `tests/e2e/fixtures/` (stage-specific mock inputs and expected outputs)

**Dependencies:** P6.1, P0.8

---

## Task Dependency Graph

```
P0.1 ──→ P0.2 ──→ P0.3 ──→ P0.4 ──→ P0.5 ──→ P0.6 ──→ P0.7
  │                                       │            │
  ├────→ P0.8 (BDD framework) ────────────┤            │
  │                                       │            │
  ├─────────────────→ P5.2 (embedding)    │            │
  │                                       │            │
  └─────────────────→ P5.3 (observability)│            │
                                          │            │
P0.7 ──→ P1.1 ──→ P1.2 ──→ P1.3 ──→ P1.4 ──→ P1.5     │
                                            │          │
P1.4 ──→ P2.1 ──→ P2.2a ──→ P2.2b ──→ P2.2c ──→ P2.2d ──→ P2.2e ──→ P2.3 ──→ P2.4 ──→ P2.5
                                                                                                                                                           │
P2.6 (typed components) ──→ P2.7a ──→ P2.7b ──→ P2.7c ───────────────────────────────────────────────────────────────────────────────────────────────────┤
                                                                                                                                                           │
P2.5, P2.7c ──→ P3.1 ──→ P3.2 ──→ P3.3 ──→ P3.4 ──→ P3.5 ──→ P3.6 ──→ P3.7 ──→ P3.8 ──→ P3.9
                                                                                          │
P3.9 ──→ P4.1 ──→ P4.2 ──→ P4.3 ──→ P4.4 ──→ P4.5 ──→ P4.6 ──→ P4.7 ──→ P4.8 ──→ P4.9
                                                                                          │
P0.6 ──→ P5.1 (LLM) ──────────────────────────────────────────────────────────────────────┤
P5.2 ─────────────────────────────────────────────────────────────────────────────────────┤
P5.3 ─────────────────────────────────────────────────────────────────────────────────────┤
P0.5 ──→ P5.7 (property-based schemas) ──────────────────────────────────────────────────┤
                                                                                          │
P0.6, P0.7, P5.1 ──→ P5.6 (contract tests) ─────────────────────────────────────────────┤
                                                                                          │
P1.5, P2.5, P2.7c, P3.9, P4.9, P5.1, P5.2, P5.3 ──→ P5.4 (LangGraph Orchestrator)
                                              │
P5.5 (Config) ────────────────────────────────┘
                                              │
P5.4 ──→ P6.1 (CLI) ──→ P6.2 (Benchmarks) ──→ P6.3 (E2E Tests) ──→ P6.4 (E2E per Stage)
```

## Task Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| **P0: Foundation** | 8 tasks | Scaffolding, schemas, abstract interfaces, BDD framework |
| **P1: Tokenization** | 5 tasks | Document loader, tokenizer, metadata, V1 validation, behavioral tests |
| **P2: Physical Topology** | 6 tasks | Parser, classifier, mapper, topology builder, V2, behavioral tests |
| **P2.6: Typed Components** | 5 inline types | InlineCode, Emphasis, Link, HTMLBlock, HTMLInline + 15 typed models + CRUDs + schemas |
| **P2.7: TokenSpan Fix** | 3 tasks | char offsets on PhysicalComponent, pipeline reorder, TokenSpanMapper rewrite |
| **P3: Semantic Analysis** | 9 tasks | Topic, segmentation, SRL, NER, coref, relationships, MiniPG, V3, behavioral tests |
| **P4: Aggregation** | 9 tasks | Cross-layer ER, merge, conflict, linking, clustering, confidence, GlobalPG, V4, behavioral tests |
| **P5: Infrastructure** | 7 tasks | LLM providers, embeddings, observability, LangGraph orchestrator, config, contract tests, property tests |
| **P6: CLI & Tests** | 4 tasks | CLI, benchmarks, E2E tests, E2E per stage |
| **Total** | **51 tasks** | |

## Test Pyramid

```
                    ┌─────────────┐
                    │   E2E (4)   │  ← Full pipeline + per-stage
                    ├─────────────┤
                    │ BDD (5)     │  ← Given/When/Then per stage
                    ├─────────────┤
                    │ Property (3)│  ← Schema invariants, graph properties
                    ├─────────────┤
                    │ Contract (3)│  ← Interface compliance for all implementations
                    ├─────────────┤
                    │  Unit (28)  │  ← Individual function/class tests
                    └─────────────┘
                         48 tasks
```
