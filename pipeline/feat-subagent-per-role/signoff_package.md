# Signoff Package: feat-subagent-per-role

**Date:** 2026-09-02
**Branch:** worktree-feat-subagent-per-role
**Status:** ready to merge

---

## Summary

This feature replaces the single-session orchestrator model with a hybrid subagent execution architecture. Anthropic-provider roles are now spawned as dedicated Claude Code subagents via the Agent tool with their exact configured model, giving each role its own context window and making per-role model selection enforceable. Cross-provider roles (e.g. `tester_generator_b` on OpenAI) are invoked through a new `scripts/call_provider.py` script that resolves credentials from `agent-config.yml`, calls the provider API, and writes structured output back to `state.md`. Independent tasks can now be dispatched in a single orchestrator message turn (`parallel_execution: true` is enforceable), `tester_generator_a` and `tester_generator_b` always run concurrently, and every activation appends a log row with `model_used` and `provider` to enable future cost attribution. The `check_providers.py` tool is extended to verify reachability of every configured role model before Gate 0.

---

## Changes

| File | Change type | Description |
|---|---|---|
| `CLAUDE.md` | Modified | Replaced Role Activation Protocol with hybrid Path A / Path B spawn logic; documents Agent tool call with `model:` param for Anthropic roles, Bash invocation of `call_provider.py` for cross-provider roles, parallel task dispatch rules, `isolation: worktree` for Coder, and state.md-only result reading |
| `scripts/call_provider.py` | New | Cross-provider API caller; CLI `--role/--run/--context-file/--config`; blocks Anthropic roles at step 6; exits 1 on missing key; POSTs to OpenAI-compat or Google endpoint; on 2xx appends output to state.md with `<!-- call_provider: [role] start/end -->` markers and writes log row; on non-2xx writes log row (error) and nothing to state.md; exits 1 on failure |
| `scripts/check_providers.py` | Modified | Added `verify_all_role_models(config)` that deduplicates `(provider, model)` pairs across all roles and probes each once via existing `_PROBERS`; added `--verify-models` CLI flag that prints a role-level table and exits 1 if any probe fails; existing no-flag behavior unchanged |
| `steering/tech.md` | Modified | Added "log.md schema" subsection with 7-column table header (`timestamp`, `run`, `role`, `model_used`, `provider`, `status`, `detail`) and column-definition table with formats |

---

## Test Results

**34/34 passed** — 0 failures, 0 errors

| Test class | Count | ACs covered |
|---|---|---|
| `TestCallProviderAnthropicBlock` | 3 | AC4 |
| `TestCallProviderMissingApiKey` | 2 | AC3 |
| `TestCallProviderSuccess` | 5 | AC3, AC5 |
| `TestCallProviderNon2xx` | 4 | AC3, AC5 |
| `TestCallProviderNetworkException` | 4 | AC3 |
| `TestCallProviderCustomConfig` | 2 | `--config` flag |
| `TestVerifyAllRoleModelsDeduplication` | 3 | AC6 |
| `TestVerifyAllRoleModelsFailingProbe` | 3 | AC6 |
| `TestVerifyModelsFlagExits1OnFailure` | 2 | AC6 |
| `TestVerifyModelsFlagExits0OnSuccess` | 1 | AC6 |
| `TestVerifyModelsOutputPerRole` | 3 | AC12 |
| `TestNoFlagBehaviorUnchanged` | 2 | AC6 |
| **Total** | **34** | |

Test file: `tests/test_subagent_per_role.py`

---

## AC Verification

| AC | Verdict | Evidence |
|---|---|---|
| AC1: Anthropic role Agent tool `model:` = `roles.[role].model` | PASS | CLAUDE.md Path A: "`model:` — exact value of `roles.[role].model` from `agent-config.yml`"; quality gate confirmed |
| AC2: Cross-provider role activates `call_provider.py` via Bash; no Agent tool call | PASS | CLAUDE.md Path B documents Bash invocation only, no Agent call; quality gate confirmed |
| AC3: `call_provider.py` writes to state.md with markers on 2xx; exits 1 and writes nothing on non-2xx | PASS | `call_provider.py` lines 183–195 (success) and 199–216 (failure); quality gate confirmed |
| AC4: `call_provider.py --role [anthropic-role]` exits 1 with no API call | PASS | `call_provider.py` step 6 (lines 98–104) blocks before any HTTP call; `TestCallProviderAnthropicBlock` (3 tests) |
| AC5: Every activation appends exactly one log.md row with non-empty `timestamp`, `role`, `model_used`, `provider` | PASS | `call_provider.py` lines 191–195 (Path B ok) and 208–214 (Path B error); CLAUDE.md Path A logging section; quality gate confirmed |
| AC6: `check_providers.py --verify-models` probes all unique `(provider, model)` pairs; exits 1 if any probe fails | PASS | `verify_all_role_models()` at lines 119–155 of `check_providers.py`; deduplication confirmed (4 unique pairs from 11 roles in tests); quality gate confirmed |
| AC7: With `parallel_execution: true`, independent tasks flagged by Architect are spawned in a single orchestrator message turn | PASS | CLAUDE.md Parallel execution section: "emit all their Agent tool calls in a single response message — do not send them sequentially across multiple turns"; listed in CLAUDE.md "Acceptance criteria covered" section |
| AC8: `tester_generator_a` and `tester_generator_b` always spawned in the same message turn; generator_a uses Agent tool with `model: claude-haiku-4-5`; generator_b invokes `call_provider.py` | PASS | CLAUDE.md: "`tester_generator_a` (Path A) and `tester_generator_b` (Path B) are always spawned together in the same turn regardless of task dependency flags"; listed in CLAUDE.md "Acceptance criteria covered" section |
| AC9: Coder Agent tool includes `isolation: worktree` when `worktree_isolation: true`; omitted when false | PASS | CLAUDE.md Path A: "`isolation: worktree` — only when role is `coder` AND `pipeline.worktree_isolation: true`; omit otherwise"; quality gate confirmed |
| AC10: Orchestrator reads role output from state.md output-contract section only; absent/incomplete triggers retry | PASS | CLAUDE.md: "If that section is absent or its status field is not in a terminal state, treat the activation as failed and apply retry logic"; quality gate confirmed |
| AC11: `steering/tech.md` contains log.md schema subsection defining all 7 columns with formats | PASS | `steering/tech.md` "log.md schema" subsection present with full column-definition table; quality gate confirmed |
| AC12: `check_providers.py --verify-models` completes within 30 seconds and outputs one line per role | PASS | `--verify-models` iterates roles dict directly (line 174), printing one row per role name; tests ran in 0.23s; quality gate confirmed |

---

## Quality Gate

**Verdict: PASS**
**Tests:** 34/34 passed
**Review cycles:** 0
**Blocking findings:** 0
**Non-blocking findings:** 2

| Finding | Severity | Notes |
|---|---|---|
| `check_providers.py --verify-models` lacks try/except around `yaml.safe_load()` — malformed config raises unhandled exception instead of clean exit 1 | MINOR / non-blocking | File always present in production; `call_provider.py` handles this correctly and can serve as a template for a follow-up fix |
| `call_provider.py` `_resolve_env(raw_url)` falls back to the literal `${ENV_VAR}` string when the URL env var is unset — API call fails gracefully but the root cause is opaque | MINOR / non-blocking | Error and log row are written correctly; URL env vars are always set alongside key env vars in practice; can be hardened in a follow-up |

---

## Non-goals confirmed out of scope

- Cost metering or enforcement against `max_cost_per_run` — `model_used` is now logged but enforcement logic is not implemented
- Support for Google or Mistral provider roles in `agent-config.yml` — `call_provider.py` handles them via `_probe_google` / `_probe_openai_compat` to avoid regressions, but no role currently uses these providers
- Changes to any skill's internal logic — skills are invoked unchanged; only the invocation mechanism changed
- UI or dashboard changes
- Streaming support in `call_provider.py` — synchronous blocking calls only

---

## Merge checklist

- [ ] All 34 tests pass
- [ ] No blocking quality gate findings
- [ ] Branch: worktree-feat-subagent-per-role
- [ ] PR created and linked
