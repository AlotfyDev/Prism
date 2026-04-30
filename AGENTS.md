# Prism — AI Coding Agent Instructions

## Master Orchestrator

**Always activate `prism-orchestrator` at session start and at every phase transition.**

- **Skill:** `skills/prism-orchestrator/SKILL.md`
- **Trigger:** Read this file at the start of every session.

## How It Works

The orchestrator determines which sub-skills to activate based on the current project phase:

| Phase | What it means | Active skills |
|-------|--------------|---------------|
| DEFINE | Clarifying what to build | `idea-refine`, `brainstorming` |
| PLAN | Breaking it into tasks | `spec-driven-development`, `writing-plans` |
| BUILD | Writing code | `test-driven-development`, `incremental-implementation` |
| VERIFY | Proving it works | `systematic-debugging`, `verification-before-completion` |
| REVIEW | Quality gate | `code-review-and-quality`, `security-and-hardening` |
| SHIP | Deploying | `git-workflow-and-versioning`, `ci-cd-and-automation` |

## Available Skills

### Agent Skills (Planning & Design)
Located in `skills/agent-skills/` — 21 skills covering the full development lifecycle.

### Superpowers (Execution & Coding)
Located in `skills/superpowers/` — 14 skills for disciplined implementation.

### Prism Orchestrator
Located in `skills/prism-orchestrator/` — The master coordinator.

## Engineering Reference

LeanKG reference materials at `references/leankg/` — use as engineering patterns for:
- MCP Server implementation (Rust)
- CLI architecture
- Rust project structure

## Rules

1. **Never skip phases.** DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP.
2. **TDD is mandatory.** Tests before code. RED → GREEN → REFACTOR.
3. **Reference sources.** Every technical decision must be backed by official documentation or papers (`source-driven-development`).
4. **Review before merge.** No code merges without review.
5. **Use the orchestrator.** Let it decide which skill to activate — don't guess.
