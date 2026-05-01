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

## 📊 Current State (as of 2026-05-01)

| Metric | Value |
|--------|-------|
| **Phase** | P1 COMPLETE — Moving to P2 (Physical Topology) |
| **Tasks Complete** | 14/48 (P0.1–P0.8, P1.1–P1.5) |
| **Tests Passing** | 455/455 |
| **Next Task** | P2.1 — MarkdownParser (Physical Topology) |
| **Active Worktree** | `worktrees/foundation/` (branch: `wt/foundation`) |
| **Active Skills** | test-driven-development, incremental-implementation |
| **Architectural Gaps Fixed** | TokenType, Full Coverage, Round-trip, BOM, Version, _StructuralGapFiller |

---

## 🏗️ Worktree Architecture (Option A — Decided 2026-05-01)

### Decision: Separate Worktree Per Stage
Each stage has its own git worktree + branch for true isolation and parallel development.

### Worktree Layout

| Worktree | Branch | Status | Contents |
|----------|--------|--------|----------|
| `foundation/` | `wt/foundation` | ✅ Active | Core + Schemas + Stage 1 (COMPLETE, 455 tests) |
| `stage1/` | `wt/stage1` | ❌ Empty | To be populated with Stage 1 code |
| `stage2/` | `wt/stage2` | ❌ Empty | Future: Physical Topology (P2) |
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

### Shared Code Update Protocol
When shared code (core/schemas) changes:
1. Commit to `master` first
2. Merge `master` into each affected stage branch
3. Run tests on each stage branch to verify no regressions
4. Update context files (CLAUDE.md, PRISM_STATE.md, HANDOFF.md)

---

## ⚡ Skill Conflict Resolution Priority

| Area | Primary | Fallback |
|------|---------|----------|
| TDD | `superpowers/test-driven-development` | `agent-skills/test-driven-development` |
| Debugging | `superpowers/systematic-debugging` | `agent-skills/debugging-and-error-recovery` |
| Planning | `agent-skills/spec-driven-development` | `superpowers/writing-plans` |
| Review | `agent-skills/code-review-and-quality` | `superpowers/requesting-code-review` |
| Git | `agent-skills/git-workflow-and-versioning` | `superpowers/using-git-worktrees` |

---

## 📋 Session Start Quick-Reference

```
1. Read: prism-orchestrator/SKILL.md → determine phase + active skills
2. Run: icm.exe recall --topic prism --limit 30 --no-embeddings "all"
3. Read: CLAUDE.md → PRISM_STATE.md → HANDOFF.md → 06_TASKS.md → 07_WORKTREE_ARCHITECTURE.md
4. Run: pytest tests/ --tb=short -q → expect 455 passed
5. Load: active skills SKILL.md files
6. Announce: phase, skills, next task, acceptance criteria, active worktree
7. Execute: with Full Production Standard
```

### Worktree Awareness
- ALWAYS know which worktree you're in: `worktrees/<name>/`
- ALWAYS know which branch you're on: `wt/<name>`
- Shared code changes → commit to `master` first, then merge into stage branches
- Stage-specific code → commit to the stage's own branch
- Never commit stage-specific code to `master`
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
