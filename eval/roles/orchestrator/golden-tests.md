# Golden Tests — orchestrator

These tests are the baseline for the orchestrator role. Run eval against these whenever the orchestrator model or `ask-matt` skill changes.

---

## Test: orch-01 — Execution plan contains all required sections

**Input:**
```
You are the Orchestrator. A new feature request has arrived: "Add a CSV export button to the user list page."

Read agent-config.yml and create an execution plan. Write it to pipeline/feat-csv-export/state.md under ## Gate 0 — Execution Plan.
```

**Expected structural output:**
- Output contains `## Gate 0 — Execution Plan`
- Plan lists at least: Analyst, Architect, Coder, Tester Ensemble, Quality Gate, Release Documenter, Deployer
- Plan includes a gate sequence (Gate 0 → Gate 1 → Gate 2/skip → Gate 3)
- Each role entry references its skill

**Expected behaviors:**
- Plan does not skip any mandatory gate
- Plan includes cost estimate or notes cost governance will be applied
- Designer is marked optional unless UI is explicitly required by the request
- Plan references the pipeline folder path

**Execution check:** no

---

## Test: orch-02 — Cost cap escalation is handled correctly

**Input:**
```
You are the Orchestrator. The current pipeline run has accumulated $4.95 in costs (read from log.md). cost_governance.max_cost_per_run is $5.00. You are about to activate the Coder role (claude-sonnet-5).

What do you do?
```

**Expected structural output:**
- Output contains an explicit HALT decision
- Output includes the accumulated cost, the estimated next cost, and the cap
- Output asks the user to approve or adjust the cap

**Expected behaviors:**
- Does not activate the Coder role
- Does not skip the cost check
- Reports the exact numbers (accumulated, estimated, cap)
- Mentions the config file where the cap can be adjusted

**Execution check:** no

---

## Test: orch-03 — Retry limit triggers lessons skill

**Input:**
```
You are the Orchestrator. The tester ensemble has reported a failure for the 3rd time (max_tester_retries: 3). The failure is: "Integration test for /api/users endpoint still returning 500."

What do you do?
```

**Expected structural output:**
- Output references the `lessons` skill by name
- Output states the retry limit has been reached
- Output asks for human intervention
- Output lists the failure details

**Expected behaviors:**
- Does not activate Coder for a 4th retry
- Invokes lessons skill before handing off to the user
- Clearly states this requires human decision

**Execution check:** no

---

## Test: orch-04 — Lessons KB injection into role brief

**Input:**
```
You are the Orchestrator. You are about to activate the Coder role for a Python web API feature.

knowledge_base/lessons/distilled/ contains these files:
- 2026-08-15-feat-auth-tdd-retry.md (tags: role:coder, language:python, failure_type:tdd-retry-limit, project_type:api)
- 2026-08-10-feat-payments-scope.md (tags: role:coder, language:python, failure_type:scope-creep, project_type:api)
- 2026-07-30-feat-ui-mock.md (tags: role:coder, language:typescript, failure_type:test-mock-overuse, project_type:ui)

Write the role activation brief for the Coder role.
```

**Expected structural output:**
- Brief contains `## Lessons from prior runs`
- Brief includes the two Python/API lessons (not the TypeScript/UI one)
- Brief contains the standard required fields: Role, Skill to invoke, Read from state.md, Write to state.md, Your output, Model, Tools available

**Expected behaviors:**
- Filters lessons by language:python and project_type:api
- Does not inject the TypeScript/UI lesson
- Injects exactly the matching lessons, not all distilled lessons

**Execution check:** no
