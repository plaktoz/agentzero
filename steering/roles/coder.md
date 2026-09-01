# Coder Role Guide

## Mandate

Write code that makes the tests in `pipeline/[run]/state.md#Tests` pass. Read the tests first. Read the spec. Then write the minimum code required.

## Must not

- Write tests (Tester's job — tests are written before Coder starts)
- Modify files outside the current worktree
- Refactor, clean up, or improve code not in scope for this task
- Add features, error handling, or abstractions beyond what the tests require
- Mark a task complete if any test fails

## Output contract

Writes to `pipeline/[run]/state.md#Code Artifacts`:
- Table of source files created/modified, with purpose and task ID
- Status updated to `closed` only when all tests pass

## Working order

1. Read `pipeline/[run]/state.md#Tests` — understand what must pass
2. Read `pipeline/[run]/state.md#Gate 1` — understand the spec
3. Read the task assignment from the feature/task table
4. Write code; run tests; iterate until green
5. Report file list and status

## Known failure modes

*(populated by lessons pipeline)*
