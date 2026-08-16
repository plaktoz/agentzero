# Resume Pipeline

Use this skill to resume an in-progress pipeline run — across sessions or across machines after a `git pull`.

Read `proj-protocol` for all shared rules.

---

## Step 1: Identify the Run

If a run name was passed as an argument (e.g. `/proj-resume feat-dark-mode`), use it directly.

If no argument was given:
1. List all subdirectories in `pipeline/`
2. For each, read the `Status:` field from `state.md`
3. Show the user a table:

```
Active pipeline runs:
  feat-dark-mode       — in_progress (last step: Gate 1 approved)
  fix-auth-bug         — in_progress (last step: Tester Phase 1 complete)

Which run do you want to resume?
```

Wait for the user to pick one.

---

## Step 2: Read State

Read `pipeline/[run-name]/state.md` in full.

Identify the last completed step by scanning the sections present:
- Gate 0 approved → execution plan exists, ready for Analyst
- Gate 1 approved → spec exists, ready for Designer (if activated) or Architect
- Gate 2 approved → design exists, ready for Architect
- Architect complete → task breakdown exists, ready for Tester Phase 1
- Tester Phase 1 complete → tests exist, ready for Coder
- Coder complete → code artifacts listed, ready for Tester Phase 2
- Gate 3 approved → ready for Deployer

---

## Step 3: Announce and Continue

Announce: "Resuming **[run-name]** from: [last completed step]"

Read `agent-config.yml` for role configs.

Continue the pipeline from the next step, following the same rules as the original skill (`proj-new-feature`, `proj-fix-bug`, or `proj-refactor` — infer from the run name prefix).

Log the resume event to `pipeline/[run-name]/log.md`:
```
| [timestamp] | Orchestrator | Resumed run [run-name] from [last step] | pipeline/[run-name]/state.md | complete |
```
