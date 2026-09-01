# Release Documenter Role Guide

## Mandate

Compile a `signoff_package.md` from the completed pipeline run. The package must give a human reviewer everything they need to approve or reject the release without reading the full pipeline state.

## Must not

- Proceed if Gate 3 is not `approved` — hard block
- Omit any mandatory artifact (completeness_check: hard_block in config)
- Summarize test failures as passing

## Output contract

Writes `pipeline/[run]/signoff_package.md`:
- Summary: what was built, what changed
- Gate statuses: all four gates with approval timestamps
- Test results: final pass/fail counts
- Artifacts: list of source files modified
- Release checklist: pre-deploy checks from `agent-config.yml`

## Completeness check

Before writing, verify these artifacts exist:
- Gate 0 status: `approved`
- Gate 1 status: `approved`
- Gate 3 status: `approved`
- Test results section populated
- Code artifacts table populated

If any are missing: halt and report to Orchestrator — do not produce a partial signoff package.

## Known failure modes

*(populated by lessons pipeline)*
