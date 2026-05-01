# PRISM — Complete Project State Snapshot

> Generated: 2026-04-30
> Purpose: Cross-session context continuity. Feed this file + all planning docs to any new context window.

---

## 1. Project Identity

**Name:** Prism — Hybrid Neuro-Symbolic NLP Pipeline
**Goal:** Transform Markdown documents into rich Property Graphs with entities, causal/argumentative relationships, and confidence levels.
**Core Philosophy:** Replace single-step LLM extraction with a transparent, multi-stage, auditable, swappable pipeline.

---

## 2. Architecture Overview

### 4 Pipeline Stages

| Stage | Name | Input | Output | Key Tech |
|-------|------|-------|--------|----------|
| **Stage 1** | Holistic Tokenization | Raw Markdown | `Stage1Output` (tokens T0..TN + metadata) | spaCy |
| **Stage 2** | Physical Topology | `Stage1Output` | `Stage2Output` (PhysicalComponents + hierarchy) | markdown-it-py |
| **Stage 3** | Semantic Topology | `Stage2Output` | `Stage3Output` (MiniPGs per layer) | Stanza SRL, spaCy NER, GLiNER, LLM |
| **Stage 4** | Aggregation | All `Stage3Output`s | `Stage4Output` (GlobalPG) | fastembed (e5-base), LLM |

### Core Design Patterns

1. **ProcessingUnit[InputT, OutputT, ConfigT]** — Abstract base for every pipeline step
2. **ValidationUnit** — Inter-stage validation gates (V0-V4)
3. **3-Tier Cascade** — Python NLP (T0) → ML models (T1) → LLM (T2, last resort)
4. **Fan-out/Fan-in** — Stage 3 processes layers in parallel via LangGraph
5. **Global Token IDs** — T0..TN across entire document, topological position as metadata only
6. **LangGraph Orchestration** — StateGraph with conditional_edges, checkpointing via SqliteSaver

### LLM Provider Priority Chain

OpenCode → KiloCode → Cline → Codex → OpenRouter (auto-fallback)

### Embedding Models (bundled, loaded at startup)

- `multilingual-e5-base` (768d) — primary, in `data/models/multilingual-e5-base/`
- `multilingual-e5-small` (384d) — fallback, in `data/models/multilingual-e5-small/`
- Format: ONNX, compatible with `fastembed`

### Constraints (NON-NEGOTIABLE)

- NO external data transmission — LangSmith banned, local structlog + SQLite only
- Phase 1 scope: Markdown ONLY (Docling deferred to PDF phase)
- TDD mandatory: Tests before code, RED → GREEN → REFACTOR
- Development cycle: DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP (never skip)

---

## 3. Schema Architecture

### Shared Enums (`prism/schemas/enums.py`)

- **LayerType**: paragraph, list, table, diagram, heading, code_block, footnote, metadata, figure, blockquote
- **EntityType**: PERSON, ORG, LOC, DATE, CONCEPT, EVENT, PRODUCT, CUSTOM
- **SemanticLevel**: document, section, layer, unit

### Stage 1 Schemas (`prism/schemas/token.py`) ✅ COMPLETE

- `Token`: id (T{n}), text (min 1), lemma, pos, ner_label
- `TokenMetadata`: token_id, char_start, char_end (>= char_start), source_line (>=1), bounding_box
- `TokenizationConfig`: tokenizer, include_whitespace, language
- `Stage1Input`: source, source_type, config
- `Stage1Output`: tokens dict, metadata dict, source_text, helpers (token_count, token_ids)

### Stage 2 Schemas (`prism/schemas/physical.py`) ✅ COMPLETE

- `PhysicalComponent`: component_id (layer_type:identifier), layer_type (enum), raw_content, token_span, parent_id, children, attributes
- `TopologyConfig`: layer_types_to_detect, nesting_depth_limit
- `Stage2Input`: source_text, token_ids, config
- `Stage2Output`: discovered_layers, layer_types, is_single_layer, component_to_tokens

### Stage 3 Schemas (`prism/schemas/semantic.py`) ✅ COMPLETE

- `MiniTopic`: topic_id, label (min 1), token_span (start<=end), confidence [0,1]
- `PredicateFrame`: predicate (lowercase_underscores), agent/patient/instrument/location/time, source_tokens, source_layer, argument_count property
- `Entity`: id (E_{TYPE}_{N}), label (EntityType), mentions (min 1), attributes dict, confidence, source_component
- `AlternativeHypothesis`: relation_type, confidence, evidence
- `Relationship`: id (R_{N}), source_entity_id, target_entity_id (no self-loop), relation_type (9 types), predicate_text, confidence, evidence_tokens, alternative_hypotheses, tier (ExtractionTier)
- `MiniPG`: layer_id, parent_layer_id, topic_label, mini_topics, entities dict, predicates list, relationships dict, child_pg_ids — auto-validates relationship refs exist in entities
- `SemanticTreeNode`: node_id, level (SemanticLevel), children, data_ref
- `SemanticConfig`: topic_extractor, predicate_extractor, entity_extractor, relationship_extractor, entity_resolver, segmentation_threshold_words (>=50)
- `Stage3Input`: source_text, component_id, component_content, token_ids, config
- `Stage3Output`: mini_pgs, semantic_tree, total_entities/relationships (auto-computed via model_validator)

### Stage 4 Schemas (`prism/schemas/global_pg.py`) ✅ COMPLETE

- `TopicCluster`: cluster_id (TC_{N}), topic_label, component_ids (min 1), entities, centroid_embedding
- `MergedEntity`: extends Entity with layers list, aggregated_confidence
- `ConfidenceSummary`: entity/relationship/predicate_avg [0,1], total counts
- `GlobalPG`: entities (MergedEntity dict), relationships list, predicates list, topic_clusters list, confidence_summary, provenance dict — auto-validates rel refs, cluster refs, provenance completeness
- `AggregationConfig`: entity_merge_strategy, conflict_resolution, topic_clustering, confidence_scorer, min_confidence_threshold, embedding_model, llm_provider
- `Stage4Input`: mini_pgs dict (id->serialized), source_text, token_ids, config
- `Stage4Output`: global_pg
- `PipelineConfig`: all stage configs combined (tokenizer, language, nesting_depth_limit, all extractors, segmentation_threshold_words, aggregation, embedding_model, llm_provider, min_confidence_threshold, checkpoint_path)
- NOTE: Module is `global_pg.py` not `global.py` (reserved Python keyword)

### Core Interfaces — P0.6 DONE, P0.7 DONE

- `ProcessingUnit[InputT, OutputT, ConfigT]` — ✅ DONE (prism/core/processing_unit.py): process(), validate_input(), validate_output(), name, tier property. StubProcessingUnit concrete stub. 15 tests pass.
- `ValidationUnit` — ✅ DONE (prism/core/validation_unit.py): validate() → ValidationReport, name(). ValidationReport (stage, passed, timestamp, checks[]), ValidationCheck (id, name, passed, severity, message, details), ValidationSeverity enum (critical, warning, info), StubValidationUnit. 23 tests pass.

---

## 4. Task Status

| Task | Status | Details |
|------|--------|---------|
| **P0.1** Scaffold & Dependencies | ✅ DONE | pyproject.toml, venv, 15 packages, all deps |
| **P0.2** Token Schemas | ✅ DONE | 5 models, 24 tests, all pass |
| **P0.3** Physical Schemas | ✅ DONE | 4 models + 3 enums, 24 tests, all pass |
| **P0.4** Semantic Schemas | ✅ DONE | 10 models + 2 enums, 51 tests, all pass |
| **P0.5** Global Schemas | ✅ DONE | 8 models + 5 enums, 43 tests, all pass |
| **P0.6** ProcessingUnit | ✅ DONE | 15 tests, all pass (157 total) |
| **P0.7** ValidationUnit | ✅ DONE | 23 tests, all pass (180 total) |
| **P0.8** BDD Framework | ✅ DONE | pytest-bdd + hypothesis directories, conftest.py, feature template |
| **P1.1** MarkdownLoader | ✅ DONE | RawMarkdown wrapper, MarkdownLoader ProcessingUnit, 21 tests |
| **P1.2** TokenStreamBuilder | ✅ DONE | SpacyTokenStreamBuilder, spaCy tokenizer, global T{n} IDs, include_whitespace, 37 tests |
| **P1.2x** Architectural Gap Fixes | ✅ DONE | TokenType enum, Full Coverage Invariant, Round-trip, BOM, Version — 20 tests |
| **P1.2xx** Full Coverage Config Fix | ✅ DONE | Stage1Output.config field, is_config_full_coverage property |
| **P1.3** MetadataIndexer | ✅ DONE | Wraps SpacyTokenStreamBuilder, 5-layer validation, 48 tests |
| **P1.4** ValidationV1 | ✅ DONE | ValidationUnit, 5 checks (V1.1-V1.5), 31 tests |
| **P1.5** Behavioral + Property Tests | ✅ DONE | _StructuralGapFiller (Unicode-aware), 62 unit + 9 BDD + 15 Hypothesis tests |
| **P1.x** Stage 1 (Tokenization) | ✅ COMPLETE | All 5 sub-tasks done. 455 total tests pass. |
| **P2.x** Stage 2 (Topology) | pending | Parser, classifier, mapper, V2 |
| **P3.x** Stage 3 (Semantic) | pending | Topic, SRL, NER, coref, relations, V3 |
| **P4.x** Stage 4 (Aggregation) | pending | Cross-layer ER, merge, conflict, V4 |
| **P5.x** Infrastructure | pending | LLM providers, embeddings, LangGraph |
| **P6.x** CLI & E2E | pending | CLI, benchmarks, integration tests |

---

## 5. Directory Structure (foundation worktree)

```
D:\MCPs\Prism\worktrees\foundation\
├── pyproject.toml
├── Portable_ICM/          ← Copied for cross-session context
│   ├── bin/icm.exe
│   ├── config/
│   ├── data/models/
│   ├── mcp-configs/
│   ├── scripts/
│   └── skills/
├── data/models/
│   ├── multilingual-e5-base/onnx/model.onnx
│   └── multilingual-e5-small/onnx/
├── prism/
│   ├── __init__.py (v0.1.0)
│   ├── core/
│   │   ├── __init__.py (exports ProcessingUnit, StubProcessingUnit, ValidationUnit, ValidationReport, ValidationCheck, ValidationSeverity, StubValidationUnit)
│   │   ├── processing_unit.py (ProcessingUnit ABC + StubProcessingUnit)
│   │   └── validation_unit.py (ValidationUnit ABC, ValidationReport, ValidationCheck, ValidationSeverity, StubValidationUnit)
│   ├── schemas/
│   │   ├── __init__.py (exports all 27 models + 14 enums)
│   │   ├── enums.py (14 enums)
│   │   ├── token.py (5 models: Token, TokenMetadata, TokenizationConfig, S1 Input/Output)
│   │   ├── physical.py (4 models: PhysicalComponent, TopologyConfig, S2 Input/Output)
│   │   ├── semantic.py (10 models: MiniTopic, PredicateFrame, Entity, AlternativeHypothesis, Relationship, MiniPG, SemanticTreeNode, SemanticConfig, S3 Input/Output)
│   │   └── global_pg.py (8 models: TopicCluster, MergedEntity, ConfidenceSummary, GlobalPG, AggregationConfig, S4 Input/Output, PipelineConfig)
│   ├── stage1/
│   │   ├── __init__.py (exports MarkdownLoader, RawMarkdown, SpacyTokenStreamBuilder)
│   │   ├── converter.py (RawMarkdown: content + source_path)
│   │   ├── loader.py (MarkdownLoader ProcessingUnit)
│   │   └── tokenizer.py (SpacyTokenStreamBuilder ProcessingUnit)
│   ├── stage2/ through stage4/ (empty __init__.py placeholders)
│   ├── validation/
│   ├── llm/ + providers/
│   ├── embedding/
│   ├── observability/
│   ├── orchestrator/
│   ├── config/
│   └── cli/
└── tests/
    ├── __init__.py
    ├── conftest.py (fixtures: fixtures_dir, sample_markdown, empty_text, single_word_text, multi_paragraph_text)
    ├── fixtures/sample_simple.md
    ├── test_schemas_tokens.py (24 tests)
    ├── test_schemas_physical.py (24 tests)
    ├── test_schemas_semantic.py (51 tests)
    ├── test_schemas_global.py (43 tests)
    ├── test_processing_unit.py (15 tests)
    ├── test_validation_unit.py (23 tests)
    ├── test_stage1_loader.py (21 tests — RawMarkdown + MarkdownLoader)
    ├── test_stage1_tokenizer.py (37 tests — SpacyTokenStreamBuilder)
    ├── features/
    │   ├── __init__.py
    │   ├── conftest.py (BDD shared step definitions)
    │   └── stage1_tokenization.feature (template: 5 scenarios)
    ├── contract/
    │   ├── __init__.py
    │   └── conftest.py (contract test fixtures)
    ├── property/
    │   ├── __init__.py
    │   └── conftest.py (Hypothesis strategies + property fixtures)
    └── benchmarks/expected/ (empty)
```

---

## 6. Key Decisions & Rationale

1. **LangGraph as Orchestrator** — Solves fan-out/fan-in, conditional routing, checkpointing natively
2. **Load ALL models at startup** — Hardware has enough RAM/VRAM, eliminates lazy-loading complexity
3. **Global sequential token IDs (T0..TN)** — Single namespace across document; position is metadata only
4. **LLM is PRIMARY for semantic reasoning** (relations, arguments, implicit causality), FALLBACK for structural tasks (tokenization, NER, SRL)
5. **NO LangSmith** — All observability via structlog (JSON) + SQLite local metrics store
6. **e5-base as primary embedding** — Higher accuracy (768d), loaded from local ONNX via fastembed
7. **Relation taxonomy is fixed** — CAUSES, DEPENDS_ON, PART_OF, LOCATED_IN, TEMPORAL, ARGUMENT_FOR, ARGUMENT_AGAINST, CONDITIONAL, OTHER
8. **Conflict resolution formula** — `score = confidence × (evidence_tokens / max_tokens_in_layer)`, tiebreaker: richer layer > more predicates

---

## 7. Planning Documents (Master Prism Repo)

All 6 planning docs in `D:\MCPs\Prism\00.00_Project_Management\`:
- `01_DEFINE.md` — 4 stages, design principles, data models
- `02_PLAN.md` — Alternative matrix, cascade patterns, LLM/memory decisions
- `03_STAGE_MATRIX.md` — 26 sub-steps with critical evaluation
- `04_SCHEMA_PROTOCOL.md` — Pydantic schemas, Validation Units (V0-V4), Relation Taxonomy, ProcessingUnit contract
- `05_LANGGRAPH_ARCHITECTURE.md` — StateGraph layout, conditional routing, parallelism, local checkpointer
- `06_TASKS.md` — 48 atomic tasks with dependencies, acceptance criteria, verification commands

---

## 8. Worktree Architecture

```
D:\MCPs\Prism\worktrees\
├── foundation/    ← P0 (Scaffolding, Schemas, Contracts) — ACTIVE
├── stage1/        ← P1 (Tokenization)
├── stage2/        ← P2 (Physical Topology)
├── stage3/        ← P3 (Semantic Topology)
├── stage4/        ← P4 (Aggregation)
├── orchestrator/  ← P5 (LangGraph Graph)
└── cli-e2e/       ← P6 (CLI, Benchmarks, E2E)
```

Each worktree has its own `CLAUDE.md` with session context.

---

## 9. Test Pyramid (Target: 48 tasks)

```
                    ┌─────────────┐
                    │   E2E (4)   │
                    ├─────────────┤
                    │ BDD (5)     │
                    ├─────────────┤
                    │ Property (3)│
                    ├─────────────┤
                    │ Contract (3)│
                    ├─────────────┤
                    │  Unit (28)  │
                    └─────────────┘
```

Current: 238 unit tests written (P0.2: 24, P0.3: 24, P0.4: 51, P0.5: 43, P0.6: 15, P0.7: 23, P1.1: 21, P1.2: 37), all passing.
BDD/Contract/Property frameworks ready (P0.8).
ICM: 21 memories stored in Portable_ICM topic "prism".

**P0 FOUNDATION PHASE: COMPLETE** — All 8 tasks done.
