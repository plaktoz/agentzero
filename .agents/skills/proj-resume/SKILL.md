# Resume Pipeline

Use this skill to resume an in-progress pipeline run — across sessions or across machines after a `git pull`.

Read `proj-protocol` for all shared rules.

---

## Step 1: Identify the Run

If a run name was passed as an argument (e.g. `/proj-resume feat-dark-mode`), use it directly.

If no argument was given:
1. List all subdirectories in `pipeline/`
2. For each, read the `Status:` field from `state.md`
3. Show the user a table, grouping epics above their child feature runs:

```
Active pipeline runs:
  epic-user-auth       — in_progress (last step: Gate 1 approved)
    feat-login         — in_progress (last step: Tester Ensemble Phase 1 complete)
    feat-signup        — pending
  feat-dark-mode       — in_progress (last step: Gate 1 approved)
  fix-auth-bug         — in_progress (last step: Tester Ensemble Phase 1 complete)

Which run do you want to resume?
```

Wait for the user to pick one. If they pick an epic, resume the epic. If they pick a feature run that belongs to an epic, resume that feature run directly.

---

## Step 2: Read State

Read `pipeline/[run-name]/state.md` in full.

Identify the run type from the prefix (`epic-`, `feat-`, `fix-`, `refactor-`) and scan accordingly.

**For epic runs (`epic-`):**
- Gate 0 approved → epic spec exists, ready for Architect
- Gate 1 approved → feature breakdown exists, ready to create feature runs
- Feature runs created → ready to execute next pending feature
- All features complete → ready for Release Documenter
- Release Documenter complete → epic-signoff.md exists, ready to close

**For feature/bug/refactor runs (`feat-`, `fix-`, `refactor-`):**
- Gate 0 approved → execution plan exists, ready for Analyst
- Gate 1 approved → spec exists, ready for Designer (if activated) or Architect
- Gate 2 approved → design exists, ready for Architect
- Architect complete → task breakdown exists, ready for Tester Ensemble Phase 1
- Tester Ensemble Phase 1 complete → tests exist, ready for Coder
- Coder complete → code artifacts listed, ready for Tester Ensemble Phase 2
- Tester Ensemble Phase 2 complete → test results exist, ready for Quality Gate
- Quality Gate passed → verdict in state.md#quality-gate, ready for Gate 3
- Gate 3 approved → ready for Release Documenter
- Release Documenter complete → signoff_package.md exists, ready for Deployer

---

## Step 3: Announce and Continue

Announce: "Resuming **[run-name]** from: [last completed step]"

Read `agent-config.yml` for role configs.

Continue the pipeline from the next step, following the same rules as the original skill — infer from the run name prefix:
- `epic-` → `proj-epic`
- `feat-` → `proj-new-feature`
- `fix-` → `proj-fix-bug`
- `refactor-` → `proj-refactor`

Log the resume event to `pipeline/[run-name]/log.md`:
```
| [timestamp] | Orchestrator | Resumed run [run-name] from [last step] | pipeline/[run-name]/state.md | complete |
```
