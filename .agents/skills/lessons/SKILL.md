# Lessons Pipeline

Activates **only on failures and escalations** — not on successful runs. Observes what went wrong, extracts generalizable patterns, validates them, and distills them into the knowledge base for future runs.

**Role:** Orchestrator  
**Triggered by:** TDD retry limit reached, quality gate blocking failure, Coder max retries, or any human escalation  
**Never triggered by:** successful pipeline completions

---

## Knowledge Base Structure

```
knowledge_base/
  index.md                    ← entry point; every file must be linked from here
  guardrails_candidates.md    ← lessons awaiting human ratification as hard rules
  lessons/
    raw/                      ← append-only; one file per failure event
    distilled/                ← generalized rules; versioned, tagged, concise
```

**One lesson per file.** File names: lowercase, hyphenated, descriptive.  
Example: `distilled/coder-scope-creep-on-refactor.md`

**Durability test before writing:** "Would I inject this into a future agent's context prompt?"  
If yes → write to `distilled/`. If it's run-specific noise → discard. If it reveals a hard constraint → add to `guardrails_candidates.md`.

**Keep distilled files under ~50 lines.** Bullets over prose. No preamble.

---

## Pipeline: Observe → Extract → Validate → Distill

### Stage 1: Observer

Read the failed run's `pipeline/[run-name]/log.md` and `state.md` in full.

Capture a structured failure event and write to `knowledge_base/lessons/raw/[YYYY-MM-DD]-[run-name]-[failure-type].md`:

```markdown
# Failure Event: [run-name]

**Date:** [YYYY-MM-DD]
**Run:** [run-name]
**Failure type:** [tdd-retry-limit | quality-gate-fail | coder-max-retries | human-escalation]
**Role that failed:** [role name]
**Retry count:** [n / max]

## What happened
[bullet list: sequence of events leading to failure, from log.md]

## Final failure
[exact error or finding from state.md that triggered escalation]

## Human override (if any)
[what the user changed or decided, if they intervened]

**Tags:** [role:coder] [failure_type:scope-creep] [language:typescript] [project_type:feature]
```

---

### Stage 2: Extractor

Read the raw event file. Run an LLM pass to find the **causal pattern** — not what failed, but why.

Ask: "What generalizable pattern caused this failure? Would a different agent hit this same wall given a similar task?"

Patterns to look for:
- Spec ambiguity that caused misinterpretation
- Role repeated the same wrong approach on every retry
- Quality gate flagged the same issue the tests missed
- Ensemble generators consistently disagreed on the same class of problem
- Human override revealed an unwritten project constraint

Write extracted patterns as candidate lessons. Skip if the failure was one-off noise (e.g. a transient API error, a typo the human corrected immediately).

---

### Stage 3: Validator

For each candidate lesson from Stage 2:

1. **Novelty check** — read `knowledge_base/index.md` and scan `distilled/`. Does a similar lesson already exist?
   - If yes and compatible: merge into the existing file, don't create a new one
   - If yes and contradictory: flag the contradiction in the existing file; do not silently overwrite
   - If new: proceed to Stage 4

2. **Generalizability check** — apply the durability test: "Would this lesson change how a future agent approaches a similar task?" If no, discard.

3. **Guardrail check** — if the lesson describes a hard constraint that should never be violated (not just advisory guidance), add it to `knowledge_base/guardrails_candidates.md` for human ratification instead of directly to `distilled/`.

---

### Stage 4: Distiller

Write each validated new lesson to `knowledge_base/lessons/distilled/[descriptive-slug].md`:

```markdown
# [Short descriptive title]

**Tags:** [role:X] [failure_type:X] [language:X] [project_type:X]
**Source runs:** [run-name-1], [run-name-2]
**Added:** [YYYY-MM-DD]

## Pattern
[1-2 bullets: what situation triggers this]

## Root cause
[1-2 bullets: why it goes wrong]

## Corrective action
[bullet list: what the role should do differently]
```

Then update `knowledge_base/index.md`:
- Add a link to the new file under the appropriate tag group
- If merging into an existing file, update its `Source runs` and `Added` date

Then update `knowledge_base/failure-patterns.md`:
- Scan for an existing row with the same `Role` and `Failure Type`
- If found: increment the `Frequency` count in-place (this is the only in-place edit permitted in this file)
- If not found: append a new row using this format:

```
| FP[n+1] | [role] | [failure_type] | 1 | [root cause — one line] | [mitigation — one line] | [distilled/file.md] |
```

Also update `steering/roles/[role].md`:
- Find the `## Known failure modes` section
- If the pattern is not already listed, append a bullet: `- [failure_type]: [root cause — one line] — see [distilled/file.md]`

---

## Retrieval at Pipeline Start

At the start of every pipeline run (`proj-new-feature`, `proj-fix-bug`, `proj-refactor`, `proj-epic`), the Orchestrator:

1. Reads `knowledge_base/index.md`
2. Filters `distilled/` lessons by tags matching the current run:
   - `role` — roles activated for this run type
   - `failure_type` — all types (inject as warnings)
   - `language` — if detectable from the project
   - `project_type` — feature / bug / refactor / epic
3. Injects the top-5 matching lessons into each role's context brief under `## Lessons from prior runs`
4. If `guardrails_candidates.md` is non-empty, remind the user: "There are [n] guardrail candidates awaiting your review: `knowledge_base/guardrails_candidates.md`"

No vector DB required — tag filtering on the bounded distilled set is sufficient.

---

## Guardrail Promotion

`knowledge_base/guardrails_candidates.md` accumulates lessons that may warrant promotion to hard rules in `knowledge_base/guardrails.yaml`.

### Adding a candidate

Append to `knowledge_base/guardrails_candidates.md` under `## Pending ratification`:

```markdown
### [slug]
**Proposed rule:** [one-line constraint]
**Source lessons:** [distilled/file.md]
**Evidence:** [n occurrences across [list of runs]]
**Suggested guardrail:**
  role: [role]
  constraint: [what must / must not happen]
  severity: hard_block | soft_warn
```

### Promoting to guardrails.yaml (human action only)

When the user approves a candidate, append to the `guardrails:` list in `knowledge_base/guardrails.yaml`:

```yaml
- id: G[n+1]
  severity: hard_block        # hard_block | soft_warn
  role: [role]                # role name from agent-config.yml; "all" for pipeline-wide
  rule: "[one-line constraint copied from candidate]"
  ratified_by: [user]
  ratified_on: [YYYY-MM-DD]
  source_lesson: knowledge_base/lessons/distilled/[file].md
```

Then remove the entry from `guardrails_candidates.md`.

The Orchestrator reads `guardrails.yaml` at session start and injects `hard_block` rules into every affected role's context brief. **Never auto-promote — promotion requires explicit human sign-off.**
