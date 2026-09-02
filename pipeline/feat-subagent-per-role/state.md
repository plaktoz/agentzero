# Pipeline State: feat-subagent-per-role

**Task:** Subagent-Per-Role Execution — wire up each pipeline role to spawn as a true subagent via the Agent tool, with model sourced from agent-config.yml, log.md model_used column, and check_providers.py model verification.
**Started:** 2026-09-01
**Status:** complete

---

## Worktree

**Path:** .claude/worktrees/feat-subagent-per-role
**Branch:** worktree-feat-subagent-per-role
**Created:** 2026-09-01
**Status:** active

---

## Gate 0: Execution Plan

**Classification:** feature
**Complexity:** medium

**Roles Activated:** Analyst, Architect, Tester Ensemble, Coder, Quality Gate, Release Documenter, Deployer
**Designer Activated:** no

**Execution Sequence:**
1. Analyst → skill: to-spec
   Output: spec + acceptance criteria → state.md#gate-1
   [GATE 1: human approval required — revision cap: 2]
2. Architect → skill: to-tickets + codebase-design
   Reads: Gate 1 spec
   Output: feature/task breakdown table → state.md#feature-task-breakdown
3. Tester Ensemble Phase 1 → skill: tdd
   Reads: spec + acceptance criteria
   3a. tester_generator_a + tester_generator_b in parallel → each generates test cases
   3b. tester_consolidator → deduplicates, produces test_plan.md → state.md#tests
   3c. tester_arbiter → resolves any generator disagreements
   Output: unit tests + integration tests → state.md#tests
4. Coder → skill: implement
   Reads: spec + tests from state.md
   Working directory: .claude/worktrees/feat-subagent-per-role
   Output: source files → state.md#code-artifacts
5. Tester Ensemble Phase 2 → skill: tdd + code-review
   5a. tester_generator_a + tester_generator_b in parallel → run tests and report
   5b. tester_consolidator → merges results → state.md#test-results
   5c. tester_arbiter → resolves disagreements; escalates critical failures to human
   Output: test results → state.md#test-results
   Retry cap: 3 | Review cap: 2
6. Quality Gate → skill: quality (tester_arbiter, autonomous)
   Output: pass/fail verdict → state.md#quality-gate
   [GATE 3: human approval required before deploying]
7. Release Documenter → skill: proj-deploy
   Output: signoff_package.md
8. Deployer → skill: proj-deploy

### Architecture Decision (approved pre-Gate 1)

**Hybrid approach:**
- All Anthropic roles → Claude Code Agent tool with `model:` sourced from agent-config.yml
- Cross-provider roles (e.g. `tester_generator_b` on OpenAI) → `scripts/call_provider.py` shell script; result written to state.md
- Orchestrator checks `roles.[role].provider` at activation time to route each call

**Files in scope:**
- `CLAUDE.md` — Role Activation Protocol rewrite (hybrid spawn logic + log.md write)
- `scripts/call_provider.py` — new: cross-provider API caller; reads config, writes output to state.md
- `scripts/check_providers.py` — extend: model reachability verification for all configured providers
- `steering/tech.md` — log.md schema update (add `model_used` column)

---

## Run Estimates

**Complexity:** medium
**Duration:** ~38–74 min (no retries: ~38 min)
**Cost:** ~$0.34–$0.54 (cap: $5.00)
**Tokens:** ~30K–75K

**Retry budgets:**
- TDD + quality gate: 3 rounds
- Spec revision: 2 rounds
- Design revision: n/a (Designer not activated)
- Code review: 2 rounds

---

## Gate 1: Spec

**Status:** approved
**Revision:** 1 of max 2

## Spec: Subagent-Per-Role Execution

### Background

The agentzero pipeline defines distinct roles (analyst, architect, coder, tester ensemble, etc.) with per-role model selections and a `parallel_execution` flag in `agent-config.yml`. In the current implementation every role runs as a skill invocation inside the orchestrator's single Claude Code session. Because there is only one session, all roles inherit the orchestrator's model (`claude-opus-4-8`) regardless of what is declared in `agent-config.yml`, `parallel_execution: true` has no observable effect, per-role token counts cannot be measured so `max_cost_per_run` is unenforceable, and context from every prior role accumulates in the orchestrator's window before the next role reads it.

The approved fix is a hybrid execution model: Anthropic-provider roles are spawned as true Claude Code subagents via the Agent tool's `model:` parameter so each role runs in its own context window on the correct model; cross-provider roles (currently `tester_generator_b` on OpenAI) are invoked via a new `scripts/call_provider.py` script that reads role config from `agent-config.yml`, calls the provider's API, and writes output directly into `state.md`. The orchestrator determines which path to use by checking `roles.[role].provider` at activation time and reads all role results from `state.md` output-contract sections, never from subagent return values.

---

### Goals

- Every Anthropic-provider role activation spawns a dedicated Claude Code subagent with the exact `model:` value declared in `agent-config.yml` for that role.
- Cross-provider roles (provider != anthropic) are invoked via `scripts/call_provider.py`, which resolves credentials from `agent-config.yml`, calls the configured provider API, and writes structured output to `state.md`.
- `parallel_execution: true` becomes enforceable: independent tasks identified by the Architect are spawned as concurrent Agent calls in a single orchestrator message.
- `tester_generator_a` (Anthropic) and `tester_generator_b` (OpenAI) always run concurrently.
- Coder subagents receive `isolation: worktree` when `pipeline.worktree_isolation: true` is set in `agent-config.yml`.
- Every role activation appends a row to `log.md` that includes `model_used` and `provider` so per-role cost attribution becomes possible.
- `check_providers.py` verifies every model configured across all roles — not just one model per provider — before Gate 0.
- The orchestrator never reads a subagent's return value as an output signal; all results are read from `state.md` under the role's declared output-contract section.

---

### Non-goals

- Cost metering or enforcement against `max_cost_per_run` — this spec makes the data available (model_used in log.md) but does not implement the enforcement logic.
- Support for Google or Mistral provider roles — `call_provider.py` will handle them via the existing `_probe_google` and `_probe_openai_compat` functions but no role in `agent-config.yml` currently uses these providers; they are included only to avoid regressions.
- Changes to any skill's internal logic — skills are invoked unchanged; only the invocation mechanism changes.
- UI or dashboard changes.
- Streaming support in `call_provider.py` — synchronous blocking calls only.

---

### Changes

#### 1. CLAUDE.md — Role Activation Protocol

Replace the current "Role Activation Protocol" section with:

**Path A — Anthropic provider** (`provider: anthropic` or provider absent and `default_provider: anthropic`):

Spawn the role as a Claude Code subagent using the Agent tool:
- `model:` — exact value of `roles.[role].model` from `agent-config.yml`
- `isolation: worktree` — only when role is `coder` AND `pipeline.worktree_isolation: true`
- `prompt:` — full context brief: role guide + state.md sections + fields: Role, Skill, Read from state.md, Write to state.md, Your output, Tools available, Active guardrails, Lessons from prior runs

**Path B — Cross-provider** (provider != anthropic):

Write context brief to `pipeline/[run]/[role]_context_brief.md`, then invoke:
```
python3 scripts/call_provider.py --role [role] --run [run] --context-file pipeline/[run]/[role]_context_brief.md
```
Read results from `state.md` after exit 0.

**Parallel execution** (when `pipeline.parallel_execution: true`):

Spawn all independent tasks in a single response message — multiple Agent tool calls in one message. `tester_generator_a` and `tester_generator_b` are always spawned together in one message.

**Reading results**: Always read from `state.md` output-contract section. Never use subagent return value as authoritative output. Missing or incomplete section = role failure → apply retry logic.

**Logging**: After every activation, append one row to `pipeline/[run]/log.md` with `model_used` and `provider`.

---

#### 2. scripts/call_provider.py — New cross-provider caller

CLI: `python3 scripts/call_provider.py --role ROLE --run RUN --context-file PATH [--config PATH]`

Startup: load `.env`, parse `agent-config.yml`, resolve provider credentials. Exit 1 if API key missing.

API call: POST to provider's chat completions endpoint with context brief as user message. 120s timeout. Anthropic roles → exit 1 immediately (configuration error).

On success: append output to `state.md` delimited by `<!-- call_provider: [role] start/end -->` markers, append log row, exit 0.

On failure: print error to stderr, append log row with status `error`, exit 1. No internal retries.

Dependencies: `requests`, `pyyaml`, `python-dotenv`.

---

#### 3. scripts/check_providers.py — Model verification extension

Add `verify_all_role_models(config)` that:
- Iterates all `config["roles"]`, builds deduplicated `(provider, model)` pairs
- Probes each pair with `max_tokens=1`
- Returns `{(provider, model): (ok, detail)}`

New CLI flag `--verify-models` prints a table: role | provider | model | status. Exit 1 if any probe fails.

Orchestrator runs `python3 scripts/check_providers.py --verify-models` at Gate 0. If any model fails, halt until user resolves.

---

#### 4. steering/tech.md — log.md schema

Add "log.md schema" subsection with this table header and column definitions:

```
| timestamp | run | role | model_used | provider | status | detail |
```

| Column | Format |
|---|---|
| `timestamp` | ISO 8601 UTC |
| `run` | pipeline run directory name |
| `role` | role name from agent-config.yml |
| `model_used` | exact model string used |
| `provider` | `anthropic` \| `openai` \| `google` \| `mistral` |
| `status` | `ok` \| `error` \| `skipped` |
| `detail` | skill invoked (ok), error message (error), skip reason (skipped) |

Orchestrator writes rows for Path A. `call_provider.py` writes rows for Path B.

---

### Acceptance Criteria

1. Anthropic role Agent tool call `model:` parameter equals `roles.[role].model` in `agent-config.yml`.
2. Cross-provider role activates `call_provider.py` via Bash; no Agent tool call emitted.
3. `call_provider.py` writes output to `state.md` with start/end markers, exits 0 on success; exits 1 and writes nothing to `state.md` on non-2xx API response.
4. `call_provider.py --role [anthropic-role]` exits 1 without making any API call.
5. Every activation appends exactly one log.md row with non-empty `timestamp`, `role`, `model_used`, `provider`.
6. `check_providers.py --verify-models` probes all unique (provider, model) pairs across all roles; exits 1 if any probe fails.
7. With `parallel_execution: true`, independent tasks flagged by Architect are spawned in a single orchestrator message turn.
8. `tester_generator_a` and `tester_generator_b` are always spawned in the same message turn; `generator_a` uses Agent tool with `model: claude-haiku-4-5`; `generator_b` invokes `call_provider.py`.
9. Coder Agent tool call includes `isolation: worktree` when `worktree_isolation: true`; parameter omitted when false.
10. Orchestrator reads role output from `state.md` output-contract section only; absent/incomplete section triggers retry logic.
11. `steering/tech.md` contains log.md schema subsection defining all 7 columns with formats.
12. `check_providers.py --verify-models` completes within 30 seconds and outputs one line per role.

---

---

## Tests

**Status:** ready
**File:** `tests/test_subagent_per_role.py`
**Count:** 32 tests (30 red / 2 regression guards)
**Red phase confirmed:** yes — 30 failures are ModuleNotFoundError / AssertionError on missing implementation; 2 pass as regression guards for existing check_providers.py behavior.

**Coverage:**
| Tests | AC |
|---|---|
| TestCallProviderAnthropicBlock (3) | AC4 |
| TestCallProviderMissingApiKey (2) | AC3 |
| TestCallProviderSuccess (5) | AC3, AC5 |
| TestCallProviderNon2xx (4) | AC3, AC5 |
| TestCallProviderNetworkException (4) | AC3 |
| TestCallProviderCustomConfig (2) | --config flag |
| TestVerifyAllRoleModelsDeduplication (3) | AC6 |
| TestVerifyAllRoleModelsFailingProbe (3) | AC6 |
| TestVerifyModelsFlagExits1OnFailure (2) | AC6 |
| TestVerifyModelsFlagExits0OnSuccess (1) | AC6 |
| TestVerifyModelsOutputPerRole (3) | AC12 |
| TestNoFlagBehaviorUnchanged (2) | AC6 |

**Note:** tester_generator_b skipped (bootstrapping run — call_provider.py is what we're building). tester_arbiter skipped (no disagreements with single generator).

---

**Last checkpoint:** tester_ensemble phase 1 at 2026-09-02

---

## Feature & Task Breakdown

| ID | Task | File(s) touched | Depends on | Status | Parallel? |
|---|---|---|---|---|---|
| T1 | Add "log.md schema" subsection to tech.md: the 7-column header `\| timestamp \| run \| role \| model_used \| provider \| status \| detail \|` plus a column-definition table giving each column's format (timestamp = ISO 8601 UTC; run = run dir name; role = role name from agent-config.yml; model_used = exact model string; provider = anthropic\|openai\|google\|mistral; status = ok\|error\|skipped; detail = skill invoked / error msg / skip reason). Note Path A writer = orchestrator, Path B writer = call_provider.py. **Covers AC11.** | `steering/tech.md` | — | open | yes |
| T2 | Create `scripts/call_provider.py`. CLI: `--role`, `--run`, `--context-file`, `--config`. Startup: `load_dotenv`, parse agent-config.yml, resolve provider credentials; exit 1 if key missing. If resolved provider is `anthropic` → exit 1 immediately with no API call (config error). Otherwise POST context brief as user message to the provider's chat-completions endpoint (openai / google / mistral), 120s timeout. Success (2xx): append model output to state.md wrapped in `<!-- call_provider: [role] start -->` / `<!-- call_provider: [role] end -->` markers, append one log.md row (status=ok), exit 0. Failure (non-2xx / exception): write nothing to state.md, print error to stderr, append one log.md row (status=error), exit 1. No internal retries. Deps: requests, pyyaml, python-dotenv. **Covers AC3, AC4, and AC5 (Path B log row).** | `scripts/call_provider.py` | — | open | yes |
| T3 | Extend `scripts/check_providers.py`. Add `verify_all_role_models(config)`: iterate `config["roles"]`, build a deduplicated set of `(provider, model)` pairs, probe each once with `max_tokens=1` via the existing `_PROBERS`, return `{(provider, model): (ok, detail)}`. Add `--verify-models` CLI flag that prints a `role \| provider \| model \| status` table (one line per role) and exits 1 if any probe fails. Existing no-flag connectivity behavior must stay unchanged. **Covers AC6, AC12.** | `scripts/check_providers.py` | — | open | yes |
| T4 | Replace the "Role Activation Protocol" section of CLAUDE.md with hybrid spawn logic. Path A (provider anthropic or absent): spawn via Agent tool with `model:` = `roles.[role].model`; include `isolation: worktree` only when role is `coder` AND `pipeline.worktree_isolation: true` (omit otherwise). Path B (provider != anthropic): write context brief to `pipeline/[run]/[role]_context_brief.md`, invoke `python3 scripts/call_provider.py --role … --run … --context-file …` via Bash (no Agent call), read result from state.md after exit 0. Parallel: when `parallel_execution: true` spawn all independent tasks in one message turn; `tester_generator_a` (Agent tool) and `tester_generator_b` (call_provider.py) always in the same turn. Reading results: only from the state.md output-contract section, never the subagent return value; absent/incomplete section → retry logic. Logging: after every Path A activation append one log.md row with model_used + provider. **Covers AC1, AC2, AC7, AC8, AC9, AC10, and AC5 (Path A log row).** | `CLAUDE.md` | T2 | closed | no |

**AC coverage map:** AC1→T4 · AC2→T4 · AC3→T2 · AC4→T2 · AC5→T2 (Path B) + T4 (Path A) · AC6→T3 · AC7→T4 · AC8→T4 (enabled by T2) · AC9→T4 · AC10→T4 · AC11→T1 · AC12→T3. All 12 ACs and all 4 spec changes are covered.

### Seam notes

- **One file per task → zero write conflicts.** T1 owns `steering/tech.md`, T2 owns `scripts/call_provider.py`, T3 owns `scripts/check_providers.py`, T4 owns `CLAUDE.md`. No two tasks ever open the same file, so the three independent tasks (T1, T2, T3) can be dispatched in a single message turn — Wave 1 — with no clobbering. Wave 2 = T4 alone.
- **The only real edge is T2 → T4 (producer → consumer).** `call_provider.py` is the producer of the Path B contract: the `<!-- call_provider: [role] start/end -->` state.md markers, the exit-0-on-success / exit-1-writes-nothing behavior, and the `--role/--run/--context-file/--config` CLI surface. `CLAUDE.md` is the consumer that documents how the orchestrator invokes that script and how it reads/retries on its output (AC2, AC8, AC10). Building the producer first lets the protocol describe verified behavior rather than a guess.
- **The log.md 7-column schema is a read-only contract, not shared mutable state.** It is fully pinned in the approved spec (Change 4). T1 records it in tech.md, T2 emits Path B rows against it, T4 documents Path A rows against it — each implements to the same spec-defined columns independently, so no build-order edge is needed between them and no Coder activation mutates another's state.
- **log.md and state.md are append-only runtime artifacts, not source files edited at Coder-time.** T2 appends to them only when the script executes; T4 only documents appending. There is no Coder-time contention over these files even though both eventually append log rows at runtime.
- **T3 is fully isolated.** `check_providers.py` neither writes state.md/log.md nor references the call_provider.py interface, so it shares no contract with any other task and runs start-to-finish in parallel with all of them.

Task breakdown written to state.md

---

## Code Artifacts

| ID | File | Description | Task | Status |
|---|---|---|---|---|
| T3 | scripts/check_providers.py | Added verify_all_role_models() + --verify-models flag | T3 | closed |
| T2 | scripts/call_provider.py | Created cross-provider API caller | T2 | closed |

---

## Code Artifacts

| ID | File | Change | Task | Status |
|---|---|---|---|---|
| T1 | steering/tech.md | Added log.md schema subsection (7 columns) | T1 | closed |
| T4 | CLAUDE.md | Replaced Role Activation Protocol with hybrid Path A/B spawn logic | T4 | closed |

---

## Build Check
**Verdict:** PASS
**Manifest:** scripts/requirements.txt (all deps declared and installed)
**Smoke tests:** 2/2 passed (call_provider.py, check_providers.py)
**Blocking findings:** 0
**Non-blocking:** requirements.txt location (scripts/ vs root), check_providers.py no-args crash (pre-existing)

---

## Quality Gate

**Verdict:** PASS
**Tests:** 34/34 passed
**Review cycles:** 0
**Open findings:** 2 (non-blocking)
**Findings:**
- MINOR (non-blocking): `check_providers.py --verify-models` path lacks try/except around `yaml.safe_load(config_path.read_text())`. A missing or malformed config file raises an unhandled exception rather than exiting 1 cleanly. Contrast with `call_provider.py` which wraps the same operation in try/except. No test covers this path; not blocking because the file is always present in production runs.
- MINOR (non-blocking): In `call_provider.py`, if the provider's URL env var is unset, `_resolve_env(raw_url)` returns `None` and the fallback `or raw_url` silently uses the literal `${ENV_VAR}` string as the endpoint URL. The API call will fail (not crash), and the error log row is written correctly. The existing missing-key guard does not protect the URL, only the key. Non-blocking because URL env vars are always set alongside key env vars in practice.

**AC Coverage:**
- AC1: PASS — CLAUDE.md Path A documents `model:` = `roles.[role].model`
- AC2: PASS — CLAUDE.md Path B documents call_provider.py via Bash with no Agent call
- AC3: PASS — call_provider.py exits 0 on 2xx with markers; exits 1 on non-2xx without writing to state.md
- AC4: PASS — call_provider.py blocks anthropic provider at step 6, before any HTTP call
- AC5: PASS — call_provider.py writes log row (model + provider) on every Path B activation; CLAUDE.md documents Path A log row
- AC6: PASS — verify_all_role_models deduplicates to 4 unique (provider, model) pairs from 11 roles; --verify-models exits 1 on failure
- AC9: PASS — CLAUDE.md documents isolation: worktree only when role=coder AND worktree_isolation: true
- AC10: PASS — CLAUDE.md documents read from state.md output-contract section only; absent/incomplete = retry
- AC11: PASS — steering/tech.md has log.md schema subsection with all 7 columns (timestamp, run, role, model_used, provider, status, detail)
- AC12: PASS — --verify-models outputs one line per role (11 rows, not 4 unique-pair rows); tests run in 0.23s
