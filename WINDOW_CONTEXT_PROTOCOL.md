# PRISM — Window Context Protocol (WCP)

> **PURPOSE:** This is the MANDATORY protocol for EVERY new context window/session.
> **STATUS:** NON-NEGOTIABLE — skip no step, rationalize no excuse.
> **STANDARD:** Full Production Functional — NEVER MVP, NEVER "good enough for now".

---

## 🚨 MANDATORY: Session Start Protocol (7 Steps — Execute IN ORDER)

### Step 1: Activate Orchestrator
```
Read: skills/prism-orchestrator/SKILL.md
```
- Determine current phase (DEFINE / PLAN / BUILD / VERIFY / REVIEW / SHIP)
- Identify active sub-skills for this phase
- Check phase exit criteria from previous phase

### Step 2: Recall ICM Memories
```bash
Portable_ICM\bin\icm.exe recall --topic prism --limit 30 --no-embeddings "all"
```
- Read ALL returned memories — they contain accumulated project knowledge
- Cross-reference with CLAUDE.md for consistency
- Note any discrepancies between ICM and file state

### Step 3: Read Context Files (IN ORDER)
1. `CLAUDE.md` → worktree context, task table, progress log
2. `PRISM_STATE.md` → complete architecture, schemas, decisions, directory tree
3. `HANDOFF.md` → step-by-step guide for next task
4. `00.00_Project_Management/06_TASKS.md` → 48 atomic tasks with acceptance criteria
5. `00.00_Project_Management/07_WORKTREE_ARCHITECTURE.md` → worktree layout, shared code strategy, dependency flow

### Step 4: Verify State
```bash
.venv\Scripts\python.exe -m pytest tests/ --tb=short -q
```
- Expected: ALL tests pass (current baseline: 258)
- If ANY test fails: STOP. Enter VERIFY phase immediately.
- Never proceed with broken tests.

### Step 5: Load Active Sub-Skills
Based on current phase, read the relevant SKILL.md files:

| Phase | Skills to Load |
|-------|---------------|
| DEFINE | `skills/agent-skills/idea-refine/SKILL.md` + `skills/superpowers/brainstorming/SKILL.md` |
| PLAN | `skills/agent-skills/spec-driven-development/SKILL.md` + `skills/agent-skills/planning-and-task-breakdown/SKILL.md` + `skills/superpowers/writing-plans/SKILL.md` |
| BUILD | `skills/superpowers/test-driven-development/SKILL.md` + `skills/agent-skills/incremental-implementation/SKILL.md` + `skills/superpowers/subagent-driven-development/SKILL.md` + `skills/agent-skills/source-driven-development/SKILL.md` |
| VERIFY | `skills/superpowers/systematic-debugging/SKILL.md` + `skills/superpowers/verification-before-completion/SKILL.md` |
| REVIEW | `skills/agent-skills/code-review-and-quality/SKILL.md` + `skills/agent-skills/security-and-hardening/SKILL.md` |
| SHIP | `skills/agent-skills/git-workflow-and-versioning/SKILL.md` + `skills/superpowers/finishing-a-development-branch/SKILL.md` |

### Step 6: Confirm Phase & Task
- Announce: Current phase, active skills, next task ID, acceptance criteria
- Verify: Previous task exit criteria met
- Proceed only if all checks pass

### Step 7: Execute with Full Production Standard
- **NO shortcuts** — every feature must handle edge cases, errors, unicode, empty inputs
- **NO "MVP mentality"** — "good enough for now" is banned
- **NO "fix it later"** — technical debt is introduced only with explicit justification
- **TDD mandatory** — RED → GREEN → REFACTOR, no exceptions

### Step 8: GitHub Repo Awareness (Step 8.5 — Check Before Any Push)
```
GitHub Repo: https://github.com/AlotfyDev/Prism.git
Remote: origin | Default branch: master
Auth: gh CLI (AlotfyDev account) | Credential: gh auth git-credential
Workflow: .github/workflows/create-repo-index.yml (auto-generates repo-index.json)
Size: ~2.4MB clean (no models, no refs, no skills, no AGENTS.md)
Before ANY push:
  1. git pull --rebase origin master (sync with remote)
  2. Verify no .gitignored files staged (models, skills, leankg, AGENTS.md, worktrees)
  3. git push origin master
  4. Check workflow: gh run list --repo AlotfyDev/Prism --limit 1
```

---

## 🔄 MANDATORY: Task Completion Protocol (6 Steps — Execute IN ORDER)

### Step 1: Run Full Regression
```bash
.venv\Scripts\python.exe -m pytest tests/ --tb=short -q
```
- ALL tests must pass
- New tests added for the feature
- No regressions from previous work

### Step 2: Update CLAUDE.md
- Update task table (status, test count)
- Update progress log (date, what changed)
- Update file listings if new files added

### Step 3: Update PRISM_STATE.md
- Update task status table
- Update directory structure if changed
- Update test count baseline

### Step 4: Update HANDOFF.md
- Write next task guide
- Include current state, what exists, what's next

### Step 5: Store ICM Memory
```bash
Portable_ICM\bin\icm.exe store --topic prism --content "detailed description" --no-embeddings
```
- Store: what was done, tests added, total count, next task
- Use descriptive content — this is the cross-session memory

### Step 6: Verify ICM Consistency
```bash
Portable_ICM\bin\icm.exe recall --topic prism --limit 5 --no-embeddings "latest"
```
- Verify the stored memory is retrievable
- Cross-check with file state for consistency

---

## 🏗️ Production Quality Standards (NON-NEGOTIABLE)

### Error Handling
- Every function handles: empty inputs, None values, type mismatches, missing files, unicode, BOM
- Every ProcessingUnit implements: validate_input(), validate_output() with meaningful messages
- No silent failures — raise descriptive exceptions

### Testing
- Minimum 80% branch coverage per module
- Test happy path + all error paths + edge cases
- Property-based tests for invariants (via Hypothesis)
- BDD scenarios for user-facing behavior

### Schema Design
- Every field has description
- Validators for invariants (not just type checks)
- model_validator for cross-field constraints
- No Optional fields without justification

### Code Structure
- Single responsibility per class/function
- Descriptive names (no abbreviations)
- Docstrings for every public API
- Type hints everywhere

### Documentation
- Every decision documented with rationale
- Every schema change logged
- Every interface contract specified

---

## 🚫 Anti-Patterns (BANNED)

| Anti-Pattern | Why Banned | Replacement |
|-------------|------------|-------------|
| "MVP first, fix later" | Creates tech debt that never gets paid | Full production from day 1 |
| "Tests can wait" | Later never comes | RED → GREEN → REFACTOR always |
| "I know what it does, no docs needed" | Future you will forget | Document everything |
| "Skip validation, it's internal" | Internal bugs are harder to find | Validate every boundary |
| "Hardcode it, make it configurable later" | Later never comes | Configurable from day 1 |
| "Ignore unicode/edge cases" | Users will hit them | Test all edge cases |
| "Copy-paste from tutorial" | Tutorials don't know your context | Source-driven development |

---

## 📊 Current State (as of 2026-05-01 — Stage 2 Worktree)

| Metric | Value |
|--------|-------|
| **Phase** | P2 — Physical Topology (P2.1-P2.4 COMPLETE) |
| **Tasks Complete** | P2.1 (Parser), P2.2a (CRUD), P2.2b-e (Orchestration), P2.3 (Topology), P2.4 (ValidationV2 + Property + Contract) |
| **Tests Passing** | 331 (194 existing + 60 orchestration + 30 V2 + 16 property + 31 contract) |
| **Next Task** | P2.5 (Behavioral/BDD tests) → P2.6 (Integration tests) |
| **Active Worktree** | `worktrees/stage2/` (branch: `wt/stage2`) |
| **Active Skills** | test-driven-development, incremental-implementation |
| **Architectural Decisions** | 5-phase orchestration pipeline, Pydantic intermediates (DetectedLayersReport → HierarchyTree → PhysicalComponents → Stage2Output), CRUD modularization, auto-registration, 6-check validation gate (V2.1-V2.6) |

---

## 🏗️ Worktree Architecture (Option A — Decided 2026-05-01)

### Decision: Separate Worktree Per Stage
Each stage has its own git worktree + branch for true isolation and parallel development.

### Worktree Layout

| Worktree | Branch | Status | Contents |
|----------|--------|--------|----------|
| `foundation/` | `wt/foundation` | ✅ Active | Core + Schemas + Stage 1 (COMPLETE, 455 tests) |
| `stage1/` | `wt/stage1` | ❌ Empty | To be populated with Stage 1 code |
| `stage2/` | `wt/stage2` | 🔧 Active | Physical Topology: Parser + CRUD (10 types) + 10 Detectors + Orchestration (Classifier/Hierarchy/Mapper/TokenSpan/Topology) + ValidationV2 + Property/Contract tests (331 tests) |
| `stage3/` | `wt/stage3` | ❌ Empty | Future: Semantic Topology (P3) |
| `stage4/` | `wt/stage4` | ❌ Empty | Future: Aggregation (P4) |
| `orchestrator/` | `wt/orchestrator` | ❌ Empty | Future: LangGraph orchestration (P5) |
| `cli-e2e/` | `wt/cli-e2e` | ❌ Empty | Future: CLI + E2E tests (P6) |

### Shared Code Strategy
- `master` branch: Core + Schemas + Project docs (source of truth)
- Each stage branch: Contains shared code (merged from master) + its own stage code
- Stage dependencies: stage2 imports from stage1, stage3 from stage2, etc.
- No circular imports between stages
- Full architecture: `00.00_Project_Management/07_WORKTREE_ARCHITECTURE.md`

### Dependency Flow
```
master (core + schemas)
    ↓
foundation (stage1) → Stage1Output
    ↓
stage2 → Stage2Output
    ↓
stage3 → Stage3Output
    ↓
stage4 → Stage4Output

orchestrator ← all stages (wires together)
cli-e2e ← orchestrator (user interface)
```

### 🔄 MANDATORY: Worktree Code Update Protocols (NON-NEGOTIABLE)

#### Protocol A: Shared Code Changes (schemas, core, pyproject.toml)
When modifying ANY shared code that affects multiple stages:
```
1. Commit to `master` branch first
2. Merge `master` into each affected stage worktree:
   cd worktrees/<stage> && git merge master
3. Run tests in each affected worktree:
   .venv/Scripts/python.exe -m pytest tests/ --tb=short -q
4. Update context files (CLAUDE.md, PRISM_STATE.md, HANDOFF.md) in each affected worktree
```

#### Protocol B: Stage-Specific Code Changes
When modifying code that belongs to ONE stage only:
```
1. Commit to the stage's own branch (wt/<stage_name>)
2. DO NOT merge into master
3. DO NOT affect other worktrees
4. Run tests ONLY in the current worktree
```

#### Decision Tree
```
Is this code shared across stages? (core, schemas, config)
  ├─ YES → Protocol A: commit to master → merge → test all
  └─ NO  → Protocol B: commit to stage branch → test current only
```

### Worktree Awareness
- ALWAYS know which worktree you're in: `worktrees/<name>/`
- ALWAYS know which branch you're on: `wt/<name>`
- Never commit stage-specific code to `master`
- Never skip merging shared code updates into affected stages
- See `07_WORKTREE_ARCHITECTURE.md` for full layout and dependency flow

## 📋 Task Completion Quick-Reference

```
1. Run: pytest tests/ --tb=short -q → expect ALL passed
2. Update: CLAUDE.md (task table + progress log)
3. Update: PRISM_STATE.md (task status + directory + test count)
4. Update: HANDOFF.md (next task guide)
5. Store: icm.exe store --topic prism --content "details" --no-embeddings
6. Verify: icm.exe recall --topic prism --limit 5 → confirm stored
```
