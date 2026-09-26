# Proposal: Template Improvements

*Based on: poteto/noodle and mattpocock/skills research (`poteto-vs-matt.md`), current project audit*
*Context: This is a copy-into-any-project template. Every gap here ships to every downstream project.*

---

## The Core Problem

This template ships without a `.claude/settings.json`. Every project that copies the template starts with only 3 allowed patterns (`git ls-remote`, `gh repo`, `gh issue`). The first pipeline run immediately hits 40–60 permission prompts — before a single line of business code is written.

This is a first-run experience failure. The template's success criterion is: "copies into a project, runs `/proj-start`, gives a task, produces reviewed, tested, deployable code with no out-of-band coordination required." The current permission setup breaks that contract on the first tool call.

---

## Change 1 — Ship `.claude/settings.json` in the Template

**The gap**: `.claude/settings.json` does not exist. Only `.local.json` exists (3 entries). `settings.json` is the project-level file that gets committed to git and copied with the template. `settings.local.json` is for personal overrides and should stay thin.

**Why this matters for a template**: Every project that copies this template inherits the same 3-entry allowlist. They will all hit the same permission wall on day one.

**What to add to `settings.json`**:

| Pattern | Used by | Risk |
|---|---|---|
| `Bash(git status)` | All roles | None |
| `Bash(git log *)` | All roles | None |
| `Bash(git diff *)` | All roles | None |
| `Bash(git add pipeline/*)` | Orchestrator | Scoped — pipeline dir only |
| `Bash(git commit -m *)` | Orchestrator | Low — pipeline state commits |
| `Bash(git checkout -b *)` | Coder, Orchestrator | Low |
| `Bash(git worktree *)` | Coder | Low — worktrees are scoped |
| `Bash(python scripts/validate_config.py)` | Orchestrator | None — read-only |
| `Bash(python scripts/check_providers.py)` | Orchestrator | None — connectivity check |
| `Read(pipeline/*)` | All roles | None |
| `Read(steering/*)` | All roles | None |
| `Read(knowledge_base/*)` | All roles | None |
| `Read(agent-config.yml)` | All roles | None |
| `Write(pipeline/*)` | All roles | Scoped — pipeline output only |

**Impact**:
- Permission prompts per run: ~40–60 → ~3–5
- Every downstream project copy gets this for free — fix once, fix everywhere
- Prompts users still see: production deploys, force-pushes, anything outside the above patterns

**How to apply**: Create `.claude/settings.json` in the template with the allowlist above. Run `/update-config` and describe the table above — it will write the file.

---

## Change 2 — Extend `/proj-start` to Cover First-Run Setup

**The gap**: `/proj-start` only runs a deployment config wizard (5 questions, writes to `agent-config.yml`). It does not handle the other first-time setup tasks a new project needs. After `/proj-start`, a user is left with unconfigured vocabulary, empty guardrails, and no verification that required skills are installed.

**What `/proj-start` should do**:

| Step | Current | Proposed |
|---|---|---|
| Check deploy config | Yes | Yes (keep) |
| Scaffold `CONTEXT.md` | No | Yes — prompt user for 5–10 key project terms; pre-fill pipeline vocabulary |
| Verify skill dependencies | No | Yes — check that every skill listed in `agent-config.yml` exists in `.claude/skills/` |
| Confirm API keys present | No | Yes — run `python scripts/check_providers.py` and surface any missing keys before the first run |
| Show what's next | Yes (3 commands) | Yes (keep, expand) |

**Why this matters for a template**: A user copying this template has never run it before. `/proj-start` is their single entry point. If it only configures deployment and stops, they discover the other gaps mid-run — after a role has already stalled.

**Impact**:
- Reduces first-run failures from silent mid-pipeline stalls to upfront "here's what's missing"
- Skill dependency check alone catches the `to-tickets` gap (Change 5) on every new project copy before the first pipeline run

**How to apply**: Edit `.claude/skills/proj-start/SKILL.md` to add the three new steps. Each step is a conditional check — skip if already done.

---

## Change 3 — Ship a Two-Part `CONTEXT.md` in the Template

*From: mattpocock/skills domain-modeling*

**The gap**: No `CONTEXT.md` exists. Every role activation re-infers what terms like `run`, `state.md`, `output-contract`, and `Gate 0` mean from surrounding context. This wastes tokens and produces inconsistent results when inferences differ.

**Why this is a template concern**: The pipeline itself has a fixed vocabulary that every project using the template shares. That vocabulary should ship pre-filled. The project-specific vocabulary is added by the user at setup time.

**Two-part structure**:

*Part 1 — Pipeline vocabulary (ships pre-filled in the template):*
> **run** — one pipeline execution. Lives in `pipeline/[run-name]/`. Named `[type]-[slug]`. Contains `state.md` and `log.md`.
>
> **output-contract** — the specific section of `state.md` a role must write before it is considered complete. The Orchestrator reads only this section to determine success or failure.
>
> **Gate** — a human approval checkpoint between pipeline phases. Gate 0 = plan approval. Gate 1 = spec approval. Gate 2 = design approval. Gate 3 = final QA sign-off.
>
> **activation** — one subagent invocation for one role on one run. Logged as one row in `log.md`.
>
> **tester ensemble** — four roles that run together: generator_a, generator_b (independent test generation), arbiter (resolves disagreements), consolidator (deduplicates findings).

*Part 2 — Project vocabulary (scaffolded by `/proj-start`, filled in by user):*
> <!-- Add 10–20 project-specific terms here. Example: -->
> **[domain entity]** — [what it is in one sentence].

**Impact**:
- Estimated 10–15% reduction in per-role token consumption (agents stop re-inferring pipeline vocabulary on every run)
- Consistency improvement: roles write to the correct `state.md` sections because sections are defined, not inferred
- Every downstream project copy gets Part 1 for free; `/proj-start` prompts them for Part 2

**How to apply**: Create `CONTEXT.md` in the template root with Part 1 pre-filled and Part 2 as a commented scaffold. Update `CLAUDE.md` to include `Read(CONTEXT.md)` in every role's context brief construction.

---

## Change 4 — Ship Starter Guardrails in the Template

**The gap**: `knowledge_base/guardrails.yaml` has the full machinery (hard_block, soft_warn, per-role, pipeline-wide) but ships empty (`guardrails: []`). Every new project starts with zero safety nets.

**Why this matters for a template**: The most common pipeline failure modes are predictable from the design. They don't require runs to accumulate — they're known from reading the pipeline spec. Shipping them as defaults means every project copy starts protected.

**What to ship in the template**:

```yaml
guardrails:
  - id: no-coder-before-spec
    severity: hard_block
    role: coder
    rule: "Do not begin implementation if state.md does not contain a spec section with status: approved."
    rationale: Prevents code written to an unreviewed spec — the primary cause of rework and retry loops.

  - id: no-deploy-without-gate
    severity: hard_block
    role: deployer
    rule: "Do not proceed if quality_gate status in state.md is not 'pass'."
    rationale: Prevents deploying code that failed review or testing.

  - id: state-append-only
    severity: hard_block
    role: all
    rule: "Never overwrite a completed section of state.md. Only append new sections or update status fields in-place."
    rationale: Preserves the audit trail. Overwriting causes silent data loss with no way to recover.

  - id: no-scope-creep-in-coder
    severity: soft_warn
    role: coder
    rule: "Flag and halt if implementation requires touching files not listed in the Architect's task breakdown."
    rationale: Scope creep in the Coder is the most common cause of quality gate failures and retry caps being hit.
```

**Impact**:
- Every new project starts with 3 hard blocks and 1 soft warning active from run 1
- Prevents `max_tester_retries: 3` and `max_review_cycles: 2` caps from being hit by avoidable ordering errors
- Hard blocks surface as explicit messages, not silent wrong behavior

**How to apply**: Replace `guardrails: []` in `knowledge_base/guardrails.yaml` with the rules above. These are ratified defaults for the template — each project can add project-specific rules via `guardrails_candidates.md` after their first run.

---

## Change 5 — Fix the Broken `to-tickets` Skill Reference

**The gap**: `agent-config.yml` lists `to-tickets` under `roles.architect.skills` but the skill file does not exist in `.claude/skills/`. The Architect will fail when it attempts to invoke `/to-tickets`.

**Why this matters for a template**: Every project copied from this template inherits the broken reference. When the Architect activates, it either errors or silently skips the skill — both outcomes stall the run without a clear cause.

**How to verify**:
```bash
ls .claude/skills/to-tickets
# returns: No such file or directory
```

**How to apply**: Remove `to-tickets` from `roles.architect.skills` in `agent-config.yml` until the skill is implemented. If the Architect needs ticket-breakdown capability, the `proj-epic` or `proj-protocol` skills can cover it in the interim.

---

## Change 6 — Three-Level Context Loading in `CLAUDE.md`

*From: poteto/noodle architecture*

**The gap**: `CLAUDE.md` instructs the Orchestrator to read all three steering files (`product.md`, `tech.md`, `structure.md`) plus `agent-config.yml` at the start of every session, before any role is activated. Every session message pays the full upfront cost regardless of what role runs.

**What to change**: Each subagent's context brief includes only the steering sections it needs:

| Role | Needs |
|---|---|
| Analyst | `tech.md` (model IDs), `structure.md` (naming rules) |
| Architect | `tech.md`, `structure.md` |
| Coder | `tech.md`, `structure.md` |
| Deployer | `tech.md`, deploy section of `agent-config.yml` |
| All | `CONTEXT.md`, their own `steering/roles/[role].md` |

The Orchestrator only needs `agent-config.yml` for routing decisions. It loads full steering files only when constructing context briefs.

**Why this belongs in the template**: This is a CLAUDE.md protocol change. Every project that copies the template inherits the protocol. Fixing it here fixes it everywhere.

**Impact**:
- Orchestrator upfront context per session: ~3,000 tokens → ~800 tokens
- Per-role subagent context: ~40% reduction — each role carries only what it needs
- Estimated token savings per full pipeline run (10 roles): 8,000–12,000 tokens
- At Sonnet 5 pricing, this is ~$0.04–$0.06 per run — small individually, but meaningful across a project's lifetime of hundreds of runs

**How to apply**: Update the Session Start Protocol section of `CLAUDE.md`. Add a `Role → Required Steering Sections` lookup table used during context brief construction. Defer steering file reads to the context brief step.

---

## Priority Order

| # | Change | Effort | Impact | Who benefits |
|---|---|---|---|---|
| 1 | Ship `.claude/settings.json` | 15 min | ~90% fewer permission prompts per run | Every project copy, immediately |
| 2 | Fix `to-tickets` reference | 5 min | Prevents silent Architect failure | Every project copy, first Architect activation |
| 3 | Ship starter guardrails | 20 min | Prevents top failure modes from run 1 | Every project copy, first pipeline run |
| 4 | Extend `/proj-start` | 1 hr | Catches setup gaps before first run | Every new project user |
| 5 | Ship pre-filled `CONTEXT.md` | 45 min | Reduces token waste, improves output consistency | Every project copy, every run |
| 6 | Three-level context loading | 1–2 hr | Reduces context overhead per run | Every project copy, every run |

Changes 1–3 are mechanical. Do them first — they require no design decisions and fix issues every downstream copy inherits right now. Changes 4–6 require content work or CLAUDE.md refactoring.

---

## What This Does Not Propose

- Replacing the current architecture with noodle's binary — the current approach is hackable and has no binary dependency, which is a feature for a template
- Adding autonomous unattended mode — the product spec explicitly excludes this
- Adopting noodle's `orders.json` schema — the `state.md` blackboard is simpler, already git-tracked, and human-readable; the structured schema adds complexity without enough benefit at this scale
