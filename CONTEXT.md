# CONTEXT.md

Shared vocabulary for this project. Every agent reads this file at activation time.
Two sections: pipeline terms (fixed — part of the template) and project terms (filled in at setup).

---

## Pipeline Vocabulary

**run** — one pipeline execution. Lives in `pipeline/[run-name]/`. Named `[type]-[slug]` (e.g., `feat-dark-mode`, `fix-auth-bug`). Contains `state.md` and `log.md`.

**state.md** — the shared blackboard for a run. Roles read their inputs from it and write their outputs to it. Append-only except for status fields updated in-place. Never overwrite a completed section.

**log.md** — execution log for a run. One row per role activation. Append-only, never edited after writing.

**output-contract** — the specific section of `state.md` a role must write before it is considered complete. The Orchestrator reads only this section to determine success or failure — never the subagent's return value.

**activation** — one subagent invocation for one role on one run. Produces one log row and writes one output-contract section.

**Gate** — a human approval checkpoint between pipeline phases:
- Gate 0: plan approval (Orchestrator presents scope + ETA; user approves before any role runs)
- Gate 1: spec approval (user reviews Analyst output before Architect runs)
- Gate 2: design approval (user reviews Designer output before Coder runs; skipped if no UI)
- Gate 3: final QA sign-off (user reviews test results and quality gate before deploy)

**tester ensemble** — four roles that always run together: `tester_generator_a` and `tester_generator_b` generate tests independently (different providers for perspective diversity), `tester_arbiter` resolves disagreements and runs the quality gate, `tester_consolidator` deduplicates findings and produces `test_plan.md`.

**worktree isolation** — when `pipeline.worktree_isolation: true`, each Coder activation runs in its own git worktree under `.worktrees/[run-name]/`. Parallel features cannot conflict. Pipeline state (`state.md`, `log.md`) always stays in the main checkout.

**escalation** — when a retry cap is reached (`max_tester_retries`, `max_review_cycles`, etc.), the Orchestrator halts and surfaces the issue to the user. The run does not abort — the user decides next steps.

**context brief** — the prompt the Orchestrator constructs for a subagent. Contains: the role guide from `steering/roles/[role].md`, relevant sections from `state.md`, task fields (role, skill, read/write sections, output, model, tools, guardrails, lessons).

**hard_block** — a guardrail severity level. The Orchestrator includes it as a hard constraint in the role's context brief. The role must halt if the condition is violated.

**soft_warn** — a guardrail severity level. The Orchestrator surfaces it as a caution but does not block the role from proceeding.

---

## Project Vocabulary

<!-- Fill in 10–20 project-specific terms when you run /proj-start. -->
<!-- Format: **term** — one sentence definition. -->
<!-- Example: **user** — a person with an account who can log in and manage their own data. -->
