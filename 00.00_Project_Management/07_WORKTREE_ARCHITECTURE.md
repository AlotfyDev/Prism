# PRISM — Worktree Architecture Design (Option A)

> **Decision Date:** 2026-05-01
> **Decision:** Separate worktree per stage with full isolation
> **Status:** ARCHITECTURAL DECISION — DO NOT CHANGE without team consensus

---

## 1. Architectural Decision

**Selected Option:** A — Separate worktree per stage
**Rationale:**
- True isolation between stages — changes in one stage cannot accidentally break another
- Parallel development — multiple developers/agents can work on different stages simultaneously
- Clear dependency boundaries — each stage explicitly imports from shared foundation
- Clean git history per stage — commits are scoped to specific stage work
- Independent testing — each stage has its own test suite and CI pipeline
- Stage-specific dependencies — each stage can have its own `pyproject.toml` if needed

**Trade-offs Accepted:**
- Shared code (core + schemas) must be committed to each stage branch
- Branch management overhead — merging shared code updates into all stage branches
- Slightly larger repo footprint — shared code duplicated across branches (not disk — git stores once)

---

## 2. Branch Strategy

```
master (shared foundation)
├── wt/foundation    (core + schemas + stage1)
├── wt/stage2        (core + schemas + stage1 → stage2)
├── wt/stage3        (core + schemas + stage1 → stage2 → stage3)
├── wt/stage4        (core + schemas + stage1 → stage4)
├── wt/orchestrator  (core + schemas + orchestrator)
└── wt/cli-e2e       (core + schemas + cli + e2e tests)
```

### Branch Contents

| Branch | Contains | Purpose |
|--------|----------|---------|
| `master` | Shared schemas + core + project docs | Source of truth for shared code |
| `wt/foundation` | master + Stage 1 complete | Active P1 development (DONE) |
| `wt/stage2` | master + Stage 1 (for imports) + Stage 2 | Physical Topology |
| `wt/stage3` | master + Stage 1 + Stage 2 (for imports) + Stage 3 | Semantic Topology |
| `wt/stage4` | master + Stage 1 + Stage 3 (for imports) + Stage 4 | Aggregation |
| `wt/orchestrator` | master + orchestrator | LangGraph state machine |
| `wt/cli-e2e` | master + CLI + E2E tests | User interface |

### Dependency Flow

```
master (schemas/core)
    ↓
wt/foundation (stage1) ───→ Stage1Output
    ↓
wt/stage2 ───→ Stage2Output
    ↓
wt/stage3 ───→ Stage3Output
    ↓
wt/stage4 ───→ Stage4Output

wt/orchestrator ← all stages (wires them together)
wt/cli-e2e ← orchestrator (user interface)
```

### Shared Code Sync Protocol

When shared code changes (schemas, core):
1. Commit to `master` first
2. Merge `master` into each affected stage branch
3. Run tests on each stage branch to verify no regressions
4. Update CLAUDE.md/PRISM_STATE.md in each worktree

---

## 3. Filesystem Structure

### 3.1 Top-Level Repo Structure

```
D:\MCPs\Prism\                          ← Main repository (master branch)
├── .git/                               ← Git internals
├── .gitignore                          ← Ignore patterns
├── AGENTS.md                           ← Agent instructions
├── pyproject.toml                      ← Shared project config
│
├── 00.00_Project_Management\           ← Planning documents
│   ├── 01_DEFINE.md
│   ├── 02_PLAN.md
│   ├── 03_STAGE_MATRIX.md
│   ├── 04_SCHEMA_PROTOCOL.md
│   ├── 05_LANGGRAPH_ARCHITECTURE.md
│   └── 06_TASKS.md
│
├── data\
│   └── models\                         ← Bundled ML models
│       ├── multilingual-e5-base\       ← 768d embedding model
│       └── multilingual-e5-small\      ← 384d embedding model
│
├── references\leankg\                  ← Rust reference project (read-only)
├── skills\                             ← Agent skill definitions
│   ├── prism-orchestrator\
│   ├── agent-skills\
│   └── superpowers\
│
└── worktrees\                          ← Git worktrees (7 total)
    ├── foundation\                     ← Branch: wt/foundation
    ├── stage1\                         ← Branch: wt/stage1
    ├── stage2\                         ← Branch: wt/stage2
    ├── stage3\                         ← Branch: wt/stage3
    ├── stage4\                         ← Branch: wt/stage4
    ├── orchestrator\                   ← Branch: wt/orchestrator
    └── cli-e2e\                        ← Branch: wt/cli-e2e
```

### 3.2 Worktree: foundation/ (ACTIVE — P1 Complete)

```
worktrees/foundation/                   ← Branch: wt/foundation
├── .git                                ← Worktree reference file
├── .gitignore
├── pyproject.toml                      ← Project dependencies + test config
├── CLAUDE.md                           ← Worktree context memory
├── PRISM_STATE.md                      ← Complete project state
├── HANDOFF.md                          ← Next task handoff guide
├── WINDOW_CONTEXT_PROTOCOL.md          ← Mandatory session protocol
│
├── prism/
│   ├── __init__.py                     ← v0.1.0
│   │
│   ├── core/                           ← SHARED (from master)
│   │   ├── __init__.py
│   │   ├── processing_unit.py          ← ProcessingUnit[InputT, OutputT, ConfigT] ABC
│   │   └── validation_unit.py          ← ValidationUnit ABC + ValidationReport
│   │
│   ├── schemas/                        ← SHARED (from master)
│   │   ├── __init__.py
│   │   ├── enums.py                    ← 14 enums (LayerType, EntityType, etc.)
│   │   ├── token.py                    ← Token, TokenMetadata, Stage1Input/Output
│   │   ├── physical.py                 ← PhysicalComponent, Stage2Input/Output
│   │   ├── semantic.py                 ← MiniPG, Stage3Input/Output
│   │   └── global_pg.py                ← GlobalPG, Stage4Input/Output
│   │
│   ├── stage1/                         ← STAGE 1: Tokenization (COMPLETE)
│   │   ├── __init__.py
│   │   ├── converter.py                ← RawMarkdown wrapper
│   │   ├── loader.py                   ← MarkdownLoader ProcessingUnit
│   │   ├── tokenizer.py                ← SpacyTokenStreamBuilder (3-phase pipeline)
│   │   ├── gap_filler.py               ← _StructuralGapFiller (Unicode-aware)
│   │   ├── metadata.py                 ← MetadataIndexer (wraps tokenizer + validation)
│   │   └── validation_v1.py            ← ValidationV1 (5 checks: V1.1-V1.5)
│   │
│   ├── stage2/                         ← STAGE 2: Empty placeholder
│   │   └── __init__.py
│   ├── stage3/                         ← STAGE 3: Empty placeholder
│   │   └── __init__.py
│   ├── stage4/                         ← STAGE 4: Empty placeholder
│   │   └── __init__.py
│   │
│   ├── orchestrator/                   ← Orchestrator: Empty placeholder
│   ├── cli/                            ← CLI: Empty placeholder
│   ├── config/                         ← Config: Empty placeholder
│   ├── embedding/                      ← Embedding: Empty placeholder
│   ├── llm/                            ← LLM: Empty placeholder
│   ├── observability/                  ← Observability: Empty placeholder
│   └── validation/                     ← Validation: Empty placeholder
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     ← Shared fixtures
│   │
│   ├── test_schemas_tokens.py          ← 24 tests
│   ├── test_schemas_physical.py        ← 24 tests
│   ├── test_schemas_semantic.py        ← 51 tests
│   ├── test_schemas_global.py          ← 43 tests
│   ├── test_processing_unit.py         ← 15 tests
│   ├── test_validation_unit.py         ← 23 tests
│   ├── test_stage1_loader.py           ← 21 tests
│   ├── test_stage1_tokenizer.py        ← 37 tests
│   ├── test_stage1_metadata.py         ← 48 tests
│   ├── test_validation_v1.py           ← 31 tests
│   ├── test_gap_filler.py              ← 62 tests
│   │
│   ├── features/                       ← BDD tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── stage1_tokenization.feature
│   │   └── test_stage1_bdd.py          ← 9 scenarios
│   │
│   ├── property/                       ← Property tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_token_properties.py    ← 15 Hypothesis tests
│   │
│   ├── contract/                       ← Contract tests
│   │   ├── __init__.py
│   │   └── conftest.py
│   │
│   ├── fixtures/
│   │   └── sample_simple.md
│   └── benchmarks/expected/
│
├── .venv/                              ← Virtual environment (gitignored)
├── Portable_ICM/                       ← ICM local copy
├── data/models/                        ← Local copy of embedding models
├── .pytest_cache/                      ← Test cache (gitignored)
└── .hypothesis/                        ← Hypothesis cache (gitignored)
```

**Status:** 455 tests passing. P1 COMPLETE.

### 3.3 Worktree: stage2/ (Future — P2: Physical Topology)

```
worktrees/stage2/                       ← Branch: wt/stage2
├── .git                                ← Worktree reference file
├── pyproject.toml                      ← Shared deps + stage2-specific deps
├── CLAUDE.md
├── PRISM_STATE.md
├── HANDOFF.md
│
├── prism/
│   ├── core/                           ← SHARED (from master)
│   ├── schemas/                        ← SHARED (from master)
│   │
│   └── stage2/                         ← STAGE 2: Physical Topology (FUTURE)
│       ├── __init__.py
│       ├── parser.py                   ← MarkdownParser (markdown-it-py)
│       ├── classifier.py               ← LayerClassifier
│       ├── mapper.py                   ← TokenToLayerMapper
│       └── validation_v2.py            ← ValidationV2
│
├── tests/
│   ├── test_stage2_parser.py
│   ├── test_stage2_classifier.py
│   ├── test_stage2_mapper.py
│   ├── test_validation_v2.py
│   ├── features/stage2_topology.feature
│   └── property/test_topology_properties.py
│
└── .venv/
```

### 3.4 Worktree: stage3/ (Future — P3: Semantic Topology)

```
worktrees/stage3/                       ← Branch: wt/stage3
├── .git                                ← Worktree reference file
├── pyproject.toml
├── CLAUDE.md
├── PRISM_STATE.md
├── HANDOFF.md
│
├── prism/
│   ├── core/                           ← SHARED
│   ├── schemas/                        ← SHARED
│   ├── stage1/                         ← Stage1 (for imports, read-only)
│   ├── stage2/                         ← Stage2 (for imports, read-only)
│   │
│   └── stage3/                         ← STAGE 3: Semantic Topology (FUTURE)
│       ├── __init__.py
│       ├── topic_extractor.py          ← KeyBERT topic extraction
│       ├── srl_processor.py            ← Stanza semantic role labeling
│       ├── ner_pipeline.py             ← spaCy NER + GLiNER
│       ├── coref_resolver.py           ← Coreference resolution
│       ├── relationship_analyzer.py    ← LLM-based relation extraction
│       └── validation_v3.py            ← ValidationV3
│
├── tests/
│   └── (stage3 test files)
│
└── .venv/
```

### 3.5 Worktree: stage4/ (Future — P4: Aggregation)

```
worktrees/stage4/                       ← Branch: wt/stage4
├── .git                                ← Worktree reference file
├── pyproject.toml
├── CLAUDE.md
├── PRISM_STATE.md
├── HANDOFF.md
│
├── prism/
│   ├── core/                           ← SHARED
│   ├── schemas/                        ← SHARED
│   ├── stage3/                         ← Stage3 (for imports, read-only)
│   │
│   └── stage4/                         ← STAGE 4: Aggregation (FUTURE)
│       ├── __init__.py
│       ├── entity_resolver.py          ← Cross-layer entity resolution
│       ├── entity_merger.py            ← Entity merging + conflict resolution
│       ├── topic_clusterer.py          ← Topic clustering via embeddings
│       └── validation_v4.py            ← ValidationV4
│
├── tests/
│   └── (stage4 test files)
│
└── .venv/
```

### 3.6 Worktree: orchestrator/ (Future — P5: LangGraph)

```
worktrees/orchestrator/                 ← Branch: wt/orchestrator
├── .git                                ← Worktree reference file
├── pyproject.toml
├── CLAUDE.md
├── PRISM_STATE.md
├── HANDOFF.md
│
├── prism/
│   ├── core/                           ← SHARED
│   ├── schemas/                        ← SHARED
│   │
│   └── orchestrator/                   ← ORCHESTRATOR (FUTURE)
│       ├── __init__.py
│       ├── pipeline_graph.py           ← Main LangGraph StateGraph
│       ├── stage1_node.py              ← Stage 1 node definition
│       ├── stage2_node.py              ← Stage 2 node definition
│       ├── stage3_node.py              ← Stage 3 node definition
│       ├── stage4_node.py              ← Stage 4 node definition
│       ├── error_handler.py            ← Error recovery and retry
│       └── checkpoint.py               ← SQLite checkpointing
│
├── tests/
│   └── (orchestrator test files)
│
└── .venv/
```

### 3.7 Worktree: cli-e2e/ (Future — P6: CLI + E2E)

```
worktrees/cli-e2e/                      ← Branch: wt/cli-e2e
├── .git                                ← Worktree reference file
├── pyproject.toml
├── CLAUDE.md
├── PRISM_STATE.md
├── HANDOFF.md
│
├── prism/
│   ├── core/                           ← SHARED
│   ├── schemas/                        ← SHARED
│   ├── orchestrator/                   ← Orchestrator (for imports)
│   │
│   └── cli/                            ← CLI (FUTURE)
│       ├── __init__.py
│       ├── main.py                     ← CLI entry point (click/typer)
│       ├── commands/
│       │   ├── process.py              ← prism process command
│       │   ├── validate.py             ← prism validate command
│       │   └── export.py               ← prism export command
│       └── formatters/
│           ├── json_formatter.py
│           ├── table_formatter.py
│           └── graph_formatter.py
│
├── tests/
│   ├── e2e/
│   │   ├── test_full_pipeline.py       ← End-to-end pipeline tests
│   │   ├── test_cli_commands.py        ← CLI command tests
│   │   └── test_export_formats.py      ← Export format tests
│   └── benchmarks/
│       ├── test_speed.py
│       └── test_accuracy.py
│
└── .venv/
```

---

## 4. Git Workflow

### 4.1 Creating a New Stage Worktree

```bash
# From main repo
git worktree add worktrees/stage2 wt/stage2
cd worktrees/stage2

# Pull in shared code from master
git merge master

# Create stage2-specific directories
mkdir -p prism/stage2 tests/features tests/property tests/contract
```

### 4.2 Updating Shared Code

```bash
# 1. Update master
cd D:\MCPs\Prism
git checkout master
# Edit shared files (core/, schemas/)
git add prism/core prism/schemas
git commit -m "feat: update shared schemas"
git push

# 2. Merge into each stage branch
cd worktrees/foundation && git merge master && pytest tests/ -q
cd ../stage2 && git merge master && pytest tests/ -q
cd ../stage3 && git merge master && pytest tests/ -q
cd ../stage4 && git merge master && pytest tests/ -q
cd ../orchestrator && git merge master && pytest tests/ -q
cd ../cli-e2e && git merge master && pytest tests/ -q
```

### 4.3 Stage Development Flow

```bash
# Working on stage2
cd worktrees/stage2

# 1. Define (TDD)
# Write tests first in tests/test_stage2_*.py

# 2. Implement
# Write code in prism/stage2/*.py

# 3. Verify
pytest tests/ -q

# 4. Commit
git add prism/stage2 tests/
git commit -m "feat(P2.1): MarkdownParser with layer detection"

# 5. Update context files
# CLAUDE.md, PRISM_STATE.md, HANDOFF.md
```

---

## 5. Shared Code Ownership

| Module | Owner Branch | Consumers |
|--------|-------------|-----------|
| `prism/core/` | `master` | All stage branches |
| `prism/schemas/` | `master` | All stage branches |
| `prism/schemas/enums.py` | `master` | All stage branches |
| `prism/stage1/` | `wt/foundation` | stage2, stage3, stage4, orchestrator |
| `prism/stage2/` | `wt/stage2` | stage3, orchestrator |
| `prism/stage3/` | `wt/stage3` | stage4, orchestrator |
| `prism/stage4/` | `wt/stage4` | orchestrator, cli-e2e |
| `prism/orchestrator/` | `wt/orchestrator` | cli-e2e |

### Import Rules

- Stages MAY import from earlier stages (stage3 → stage2 → stage1)
- Stages MUST NOT import from later stages (stage2 → stage3)
- All stages import shared code from `prism.core` and `prism.schemas`
- No circular imports between stages

---

## 6. .gitignore (Top-Level)

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# Virtual environments
.venv/
venv/
env/

# Test caches
.pytest_cache/
.hypothesis/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# ICM local (managed separately)
Portable_ICM/

# Local model copies
data/models/
```

---

## 7. Current State & Next Steps

### What Exists Now
- `master` branch: Initial commit with planning docs only
- `wt/foundation` branch: Complete P0 + P1 (455 tests), uncommitted work
- All other worktrees: Empty (only `.git` reference file)

### Immediate Actions Required
1. **Add `.gitignore`** to prevent committing artifacts
2. **Commit foundation work** to `wt/foundation` branch
3. **Commit shared code to `master`** (core + schemas + planning docs)
4. **Populate `wt/stage2`** worktree with shared code + P2.1 starting point
5. **Update all CLAUDE.md** files in each worktree with this architecture

### Long-Term Workflow
- Develop each stage in its own worktree
- Merge `master` into stage branches when shared code changes
- Stage branches are independent — can be developed in parallel
- Final integration happens in `wt/orchestrator` which wires all stages together
