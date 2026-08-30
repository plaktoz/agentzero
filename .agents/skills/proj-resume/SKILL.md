# Resume Pipeline

Use this skill to resume an in-progress pipeline run — after a session ends, context is exhausted, or a run is paused by a limit hit or blocking finding.

Read `proj-protocol` for all shared rules.

---

## Step 1: Identify the Run

If a run name was passed as an argument (e.g. `/proj-resume feat-dark-mode`), use it directly.

If no argument was given:
1. List all subdirectories in `pipeline/`
2. For each, read the `**Status:**` and `**Last checkpoint:**` fields from `state.md`
3. Show the user a table, grouping epics above their child feature runs:

```
Active pipeline runs:
  epic-user-auth        — in_progress  checkpoint: Gate 1 approved
    feat-login          — in_progress  checkpoint: Tester Ensemble Phase 1 complete
    feat-signup         — pending
  feat-dark-mode        — in_progress  checkpoint: Gate 1 approved
  fix-auth-bug          — in_progress  checkpoint: Tester Ensemble Phase 1 complete

Which run do you want to resume?
```

Wait for the user to pick one. If they pick an epic, resume the epic. If they pick a feature run inside an epic, resume that feature run directly.

---

## Step 2: Read State and Restore Counters

Read `pipeline/[run-name]/state.md` in full.

### Identify last completed step

Read the `**Last checkpoint:**` field if present — this is the authoritative resume point written by the Orchestrator after each role completes.

If no `**Last checkpoint:**` exists, infer the last completed step from the sections present in `state.md` using the table below.

**For epic runs (`epic-`):**

| Last completed step | Next step |
|---|---|
| Gate 0 approved, no Gate 1 | Architect → feature breakdown |
| Gate 1 approved, no feature runs | Create feature run folders |
| Feature runs created, all pending | Start first unblocked feature |
| Some features complete | Resume next unblocked feature |
| All features complete, no epic-signoff.md | Release Documenter → epic-signoff.md |

**For feature/bug/refactor runs (`feat-`, `fix-`, `refactor-`):**

| Last completed step | Next step |
|---|---|
| Gate 0 approved, no `#gate-1` | Analyst → spec |
| `#gate-1` present, no `#gate-2` or Architect | Designer (if activated) or Architect |
| `#gate-2` present, no task breakdown | Architect → task breakdown |
| Task breakdown present, no `#tests` | Tester Ensemble Phase 1 |
| `#tests` present, no `#code-artifacts` | Coder |
| `#code-artifacts` present, no `#test-results` | Tester Ensemble Phase 2 |
| `#test-results` present, no `#quality-gate` | Quality Gate |
| `#quality-gate` PASS, no Gate 3 approval | Gate 3 (present test results) |
| Gate 3 approved, no signoff_package.md | Release Documenter |
| signoff_package.md present, no deployment | Deployer |

### Restore retry counters

Read `log.md` and count rows by role to restore the retry state. The Orchestrator must carry these forward — caps must not reset on resume.

```
tester_retries_used  = count of rows where Role is Coder or tester_ensemble AND Status is failed
spec_revisions_used  = count of rows where Role is analyst AND Status is failed (Gate 1 rejection)
design_revisions_used = count of rows where Role is designer AND Status is failed (Gate 2 rejection)
review_cycles_used   = count of rows where Role is tester_arbiter AND Action contains "code-review" AND Status is failed
```

Compare each against its cap in `agent-config.yml`. If any counter is already at its cap, immediately report to the user — do not silently proceed past a cap that was already reached.

### Check accumulated cost

Sum the `Cost (USD)` column in `log.md`. Compare against `cost_governance.max_cost_per_run`.

Report in the resume announcement:
```
Accumulated cost so far: $[sum] of $[cap] cap ([pct]% used)
```

If accumulated cost is within one role's estimated cost of the cap, warn:
```
⚠ Budget nearly exhausted — $[remaining] remaining. Next role: [role] (~$[est]).
```

---

## Step 3: Announce and Continue

Announce:
```
Resuming [run-name]
Last checkpoint: [last completed step]
Next step: [next step]

Retry counters:
  TDD/quality:   [tester_retries_used]/[max_tester_retries]
  Spec revision: [spec_revisions_used]/[max_spec_revisions]
  Design revision: [design_revisions_used]/[max_design_revisions]
  Code review:   [review_cycles_used]/[max_review_cycles]

Accumulated cost: $[sum] of $[cap] ([pct]% used)
```

If `knowledge_base/guardrails_candidates.md` is non-empty, surface:
```
⚠ [n] guardrail candidates are awaiting your review: knowledge_base/guardrails_candidates.md
```

Read `agent-config.yml` for role configs.

Continue the pipeline from the next step, following the same rules as the original skill. Infer skill from run name prefix:
- `epic-` → `proj-epic`
- `feat-` → `proj-new-feature`
- `fix-` → `proj-fix-bug`
- `refactor-` → `proj-refactor`

---

## Step 4: Log the Resume Event

Append one row to `pipeline/[run-name]/log.md` using the full 12-field format:

```
| [timestamp] | Orchestrator | claude-opus-4-8 | anthropic | — | [next role] | Resumed run from [last checkpoint] | pipeline/[run-name]/state.md | 0 | 0 | 0.00 | complete |
```
