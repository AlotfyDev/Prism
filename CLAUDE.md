# Prism — Foundation Worktree Context Memory

## Worktree Identity

| Property | Value |
|----------|-------|
| **Worktree** | `worktrees/foundation` |
| **Branch** | `wt/foundation` |
| **Focus** | P0: Scaffolding, Schemas, Interfaces + P1: Stage 1 Tokenization |
| **Tasks** | P0.1 — P1.5 (14 tasks) |

## Session State

### Current Phase: P1 — Stage 1 (Holistic Tokenization)
**Status:** ✅ COMPLETE — All 5 tasks done
**Total Tests:** 455 passing, zero regressions

### Next Task: P2.1 — MarkdownParser (Physical Topology)
- Parse Markdown layers: headings, lists, tables, code blocks, paragraphs
- Produce PhysicalComponent with layer boundaries
- Route tokens to layers via char range mapping

## Tasks in This Worktree

| ID | Task | Status | Tests |
|----|------|--------|-------|
| P0.1 | Project Scaffold & Dependencies | ✅ DONE | — |
| P0.2 | Pydantic Schema Models — Token & Metadata | ✅ DONE | 24/24 pass |
| P0.3 | Pydantic Schema Models — Physical Component | ✅ DONE | 24/24 pass |
| P0.4 | Pydantic Schema Models — Semantic (MiniPG) | ✅ DONE | 51/51 pass |
| P0.5 | Pydantic Schema Models — GlobalPG & Config | ✅ DONE | 43/43 pass |
| P0.6 | ProcessingUnit Abstract Interface | ✅ DONE | 15/15 pass |
| P0.7 | ValidationUnit Abstract Interface | ✅ DONE | 23/23 pass |
| P0.8 | Behavioral Test Framework Setup (pytest-bdd + hypothesis) | ✅ DONE | structure ready |
| P1.1 | DocumentConverter Interface + MarkdownLoader | ✅ DONE | 21/21 pass |
| P1.2 | TokenStreamBuilder (spaCy) | ✅ DONE | 37/37 pass |
| P1.2x | Architectural Gap Fixes (TokenType, Full Coverage, Round-trip, BOM, Version) | ✅ DONE | 20/20 pass |
| P1.2xx | Full Coverage Invariant Fix (config-aware validation via is_config_full_coverage) | ✅ DONE | integrated |
| P1.3 | MetadataIndexer (char positions, line numbers, validation) | ✅ DONE | 48/48 pass |
| P1.4 | ValidationV1 — Token Integrity Gate (V1.1-V1.5) | ✅ DONE | 31/31 pass |
| P1.5 | Behavioral + Property Tests + Unicode Gap Filler | ✅ DONE | 86/86 pass |

## Completed Files

### Schemas
- `prism/schemas/__init__.py` — Re-exports all models + enums
- `prism/schemas/enums.py` — LayerType(10), EntityType(8), SemanticLevel(3), RelationType(9), ExtractionTier(3), EntityMergeStrategy(3), ConflictResolution(3), TopicClustering(3), ConfidenceScorer(2), LLMProvider(5)
- `prism/schemas/token.py` — Token, TokenMetadata, TokenizationConfig, Stage1Input, Stage1Output
- `prism/schemas/physical.py` — PhysicalComponent, TopologyConfig, Stage2Input, Stage2Output
- `prism/schemas/semantic.py` — MiniTopic, PredicateFrame, Entity, AlternativeHypothesis, Relationship, MiniPG, SemanticTreeNode, SemanticConfig, Stage3Input, Stage3Output
- `prism/schemas/global_pg.py` — TopicCluster, MergedEntity, ConfidenceSummary, GlobalPG, AggregationConfig, Stage4Input, Stage4Output, PipelineConfig (NOTE: global_pg not global — reserved keyword)

### Core
- `prism/core/__init__.py` — Exports ProcessingUnit, StubProcessingUnit, ValidationUnit, StubValidationUnit, ValidationReport, ValidationCheck, ValidationSeverity
- `prism/core/processing_unit.py` — ProcessingUnit[InputT, OutputT, ConfigT] ABC + StubProcessingUnit
- `prism/core/validation_unit.py` — ValidationUnit ABC, ValidationReport, ValidationCheck, ValidationSeverity, StubValidationUnit

### Stage 1
- `prism/stage1/__init__.py` — Exports MarkdownLoader, MetadataIndexer, RawMarkdown, SpacyTokenStreamBuilder
- `prism/stage1/converter.py` — RawMarkdown Pydantic wrapper (content + source_path)
- `prism/stage1/loader.py` — MarkdownLoader implements ProcessingUnit[Stage1Input, RawMarkdown, TokenizationConfig]
- `prism/stage1/metadata.py` — MetadataIndexer wraps SpacyTokenStreamBuilder + 5-layer validation
- `prism/stage1/tokenizer.py` — SpacyTokenStreamBuilder implements ProcessingUnit[Stage1Input, Stage1Output, TokenizationConfig]
- `prism/stage1/gap_filler.py` — _StructuralGapFiller: Unicode-aware gap filler (Zs/Zl/Zp + ASCII control + BOM), handles leading/inter-token/trailing gaps
- `prism/stage1/validation_v1.py` — ValidationV1: ValidationUnit with 5 checks (V1.1-V1.5)

### Tests
- `tests/test_schemas_tokens.py` — 24 tests
- `tests/test_schemas_physical.py` — 24 tests
- `tests/test_schemas_semantic.py` — 51 tests
- `tests/test_schemas_global.py` — 43 tests
- `tests/test_processing_unit.py` — 15 tests
- `tests/test_validation_unit.py` — 23 tests
- `tests/test_stage1_loader.py` — 21 tests (RawMarkdown wrapper + MarkdownLoader)
- `tests/test_stage1_metadata.py` — 48 tests (MetadataIndexer)
- `tests/test_stage1_tokenizer.py` — 37 tests (SpacyTokenStreamBuilder)
- `tests/test_validation_v1.py` — 31 tests (ValidationV1)
- `tests/test_gap_filler.py` — 62 tests (_StructuralGapFiller: Unicode whitespace, leading/inter/trailing gaps)
- `tests/features/test_stage1_bdd.py` — 9 BDD scenarios (real-world Markdown documents)
- `tests/property/test_token_properties.py` — 15 Hypothesis property tests (sequential IDs, no overlaps, full coverage, determinism, V1 consistency)
- `tests/conftest.py` — Shared fixtures (fixtures_dir, sample_markdown, empty_text, single_word_text, multi_paragraph_text)
- `tests/fixtures/sample_simple.md` — Sample markdown fixture
- `tests/features/` — BDD directory with `conftest.py` and `stage1_tokenization.feature`
- `tests/contract/` — Contract test directory with `conftest.py` fixtures
- `tests/property/` — Property test directory with `conftest.py` and Hypothesis strategies

### Config
- `pyproject.toml` — All deps: pydantic, spacy, stanza, gliner, fastembed, langgraph, keybert, openai, pytest-bdd, hypothesis, etc.
- `WINDOW_CONTEXT_PROTOCOL.md` — MANDATORY session start + task completion protocol

## Shared Decisions (Immutable — Do Not Change)

### Core Design Principles
1. **Separation of Logic from Interface:** Pipelines independent of MCP/CLI
2. **Global Token IDs First:** T0..TN assigned holistically BEFORE layer analysis
3. **Physical Layer Discovery:** Scan document to determine which layers exist
4. **Recursive Semantic Analysis per Layer:** Same steps for every physical layer
5. **Layer-First Entity Resolution:** Resolve locally before cross-layer aggregation
6. **Property Graph as Object:** Each layer produces MiniPG; aggregation merges them

### Language & Scope
- **Primary Language:** English
- **Phase 1 Scope:** Markdown files only (no OCR, no PDF, no raw images)
- **LLM Usage:** Primary for reasoning (Relations, Arguments, Causality), fallback for structural NLP

### Tool Stack
| Tier | Tools | Role |
|------|-------|------|
| Python NLP | spaCy, Stanza, NLTK, GLiNER | Tokenization, POS, NER, SRL, Coref |
| Embeddings | fastembed + e5-base (bundled) | Semantic similarity, clustering |
| ML | HuggingFace free models, AllenNLP | Enhanced SRL, embeddings fallback |
| LLM | OpenCode → KiloCode → Cline → Codex → OpenRouter | Reasoning, disambiguation, fallback |

### Orchestrator
- **LangGraph** for all stages (1-4) — foundational from day 1
- **LangSmith** permanently excluded (cloud-only)
- **Local observability:** structlog + SQLite

### Embedding Models (Bundled)
- `data/models/multilingual-e5-base` — 768d, ~1.1GB (primary)
- `data/models/multilingual-e5-small` — 384d, ~470MB + 235MB quantized (fallback)
- **Decision:** e5-base is the accuracy-first choice. No tolerance for accuracy loss.
- Models loaded at startup, not lazy-loaded.

### Schema Protocol (04_SCHEMA_PROTOCOL.md)
- All schemas are Pydantic models, versioned at `prism-schema/v1/`
- ProcessingUnit contract is the abstract interface for ALL implementations
- Relation Type Taxonomy is frozen for v1: CAUSES, DEPENDS_ON, PART_OF, LOCATED_IN, TEMPORAL, ARGUMENT_FOR, ARGUMENT_AGAINST, CONDITIONAL, OTHER

### Fallback Matrix (02_PLAN.md)
- LLM is FIRST for: Relationship Type, Argument Mining, Implicit Causal
- LLM is FALLBACK for: Tokenization, NER, SRL, Coref, Segmentation, Topic, Conflict, Confidence
- 3-tier cascade: Python NLP → ML → LLM (for fallback cases only)

## Dependencies on Other Worktrees

| Worktree | Dependency Type | What I Need |
|----------|----------------|-------------|
| All | Schema dependency | My schemas (P0.2-P0.5) are consumed by ALL worktrees |
| stage1, stage2, stage3, stage4 | Interface dependency | ProcessingUnit (P0.6) and ValidationUnit (P0.7) are used by all |
| stage1, stage2, stage3, stage4 | Test framework | BDD framework (P0.8) is used by all behavioral test tasks |
| orchestrator | Orchestrator dependency | LangGraph wiring depends on my schemas being complete |

## What I Produce for Others

| Output | Consumer | Used In |
|--------|----------|---------|
| `prism/schemas/` | All worktrees | Stage input/output models, config models |
| `prism/core/processing_unit.py` | All worktrees | Abstract interface for every processing unit |
| `prism/core/validation_unit.py` | All worktrees | Abstract interface for validation gates |
| `tests/features/` structure | All worktrees | BDD test framework structure |
| `tests/contract/` structure | All worktrees | Contract test framework structure |
| `tests/property/` structure | All worktrees | Property test framework structure |

## Portable ICM Reference

- **Location:** `D:\MCPs\Portable_ICM` (also copied to `Portable_ICM/` in this worktree)
- **Embedding Models:** Already copied to `data/models/` (e5-base, e5-small)
- **FastEmbed Compatibility:** Models use ONNX format, compatible with `pip install fastembed`
- **Note:** No functional dependency on ICM code — only embedding models are reused

## Progress Log

| Date | Session | What Changed |
|------|---------|-------------|
| 2026-04-30 | Initial | Worktree created. Tasks P0.1-P0.8 defined. Context memory initialized. |
| 2026-04-30 | P0.1 | pyproject.toml, venv, 15 prism/ packages, tests/ structure, data/models/, all deps installed |
| 2026-04-30 | P0.2 | Token, TokenMetadata, TokenizationConfig, Stage1Input/Output schemas — 24 tests pass |
| 2026-04-30 | P0.3 | PhysicalComponent, TopologyConfig, Stage2Input/Output + enums — 24 tests pass |
| 2026-04-30 | P0.4 | MiniTopic, PredicateFrame, Entity, Relationship, MiniPG, Stage3 I/O + semantic enums — 51 tests pass |
| 2026-04-30 | P0.5 | TopicCluster, MergedEntity, GlobalPG, AggregationConfig, Stage4 I/O, PipelineConfig + config enums — 43 tests pass |
| 2026-04-30 | ICM | 6 memories stored in Portable_ICM (P0.1-P0.5 details + summary) |
| 2026-04-30 | P0.6 | ProcessingUnit ABC + StubProcessingUnit — 15 tests pass, 157 total |
| 2026-04-30 | P0.7 | ValidationUnit ABC + ValidationReport/Check/Severity + StubValidationUnit — 23 tests pass, 180 total |
| 2026-04-30 | P0.8 | BDD framework setup — tests/features/, tests/contract/, tests/property/ with conftest.py + feature template. 180 tests pass. **P0 FOUNDATION COMPLETE** |
| 2026-05-01 | P1.2 | SpacyTokenStreamBuilder — spaCy tokenizer with global T{n} IDs, include_whitespace config, file/raw_text support, TokenMetadata with char positions and line numbers. 37 tests pass, 238 total. |
| 2026-05-01 | P1.2x | Architectural Gap Fixes: TokenType enum (semantic/structural), Full Coverage Invariant, Round-trip verification, BOM handling (utf-8-sig), ProcessingUnit version property. 20 new tests, 258 total. Created WINDOW_CONTEXT_PROTOCOL.md for mandatory session protocol. |
| 2026-05-01 | P1.2xx | Full Coverage Invariant Fix: Stage1Output.config field added, is_config_full_coverage property validates token text matches source positions even when whitespace excluded. validate_output uses config-aware check. |
| 2026-05-01 | P1.3 | MetadataIndexer — wraps SpacyTokenStreamBuilder, 5-layer validation (key match, text-position integrity, no overlaps, sequential IDs, config-aware gap detection). 48 tests pass. 306 total. |
| 2026-05-01 | P1.4 | ValidationV1 — ValidationUnit with 5 checks: V1.1 sequential IDs, V1.2 no empty tokens (config-aware), V1.3 metadata completeness, V1.4 no overlapping ranges, V1.5 full coverage (WARNING for whitespace gaps, CRITICAL for content gaps). 31 tests pass. 337 total. P1 now 4/5 complete (80%). |
| 2026-05-01 | P1.5 | Behavioral + Property tests complete. **Architectural fix:** `_StructuralGapFiller` — dedicated Unicode-aware gap filler (Zs/Zl/Zp + ASCII control + BOM), handles leading/inter-token/trailing gaps. Replaced ad-hoc gap logic in `_fill_structural_gaps`. Added 62 unit tests + 9 BDD scenarios + 15 Hypothesis property tests. **455 total tests pass.** P1 FOUNDATION COMPLETE (5/5). |

## Session Start Checklist

At the start of every session in this worktree:

### MANDATORY: Follow WINDOW_CONTEXT_PROTOCOL.md
This file defines the complete 7-step session start protocol + 6-step task completion protocol.
**DO NOT SKIP ANY STEP.** The protocol is at: `WINDOW_CONTEXT_PROTOCOL.md`

### Quick Reference:
1. Read: `prism-orchestrator/SKILL.md` → determine phase + active skills
2. Run: `Portable_ICM\bin\icm.exe recall --topic prism --limit 30 --no-embeddings "all"`
3. Read: `CLAUDE.md` → `PRISM_STATE.md` → `HANDOFF.md` → `06_TASKS.md`
4. Run: `pytest tests/ --tb=short -q` → expect 455 passed
5. Load: active skills SKILL.md files
6. Announce: phase, skills, next task, acceptance criteria
7. Execute: with Full Production Standard (NEVER MVP)

### GitHub Repo Awareness:
- **Repo:** https://github.com/AlotfyDev/Prism.git
- **Remote:** origin | **Branch:** master | **Auth:** gh CLI (AlotfyDev)
- **Workflow:** create-repo-index.yml auto-generates repo-index.json on every push
- **Before push:** `git pull --rebase origin master` → verify .gitignore → push
- **ICM memories:** 17+ memories stored, including GitHub repo details (Step 8 in WCP)
