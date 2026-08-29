# Golden Tests — analyst

Baseline tests for the analyst role. Run eval against these whenever the analyst model or `to-spec` skill changes.

---

## Test: analyst-01 — Spec contains all mandatory sections

**Input:**
```
You are the Analyst. Convert this requirement into a spec using the to-spec skill:

"Add a password reset flow. Users should be able to click 'Forgot password?' on the login page, enter their email, receive a reset link, and set a new password."
```

**Expected structural output:**
- Output contains: `## Overview`, `## Acceptance Criteria`, `## Out of Scope`, `## Open Questions`
- Acceptance criteria are numbered
- Each criterion is testable (has a clear pass/fail condition)
- Out of scope section exists and is non-empty

**Expected behaviors:**
- Does not include implementation details (no "use bcrypt", no database schema)
- Acceptance criteria use "user can" / "system must" language
- No code or SQL in the spec
- Open questions flag at least one ambiguity (e.g. token expiry time, rate limiting)

**Execution check:** no

---

## Test: analyst-02 — Out-of-scope items are correctly identified

**Input:**
```
You are the Analyst. A developer asked: "Can you add social login (Google/GitHub OAuth) to the spec while you're at it?"

You are currently writing the spec for: "Add a password reset flow."

What do you do?
```

**Expected structural output:**
- Output explicitly rejects the scope addition
- Output adds social login to the `## Out of Scope` section
- Output explains why it is out of scope (separate feature, requires separate spec)

**Expected behaviors:**
- Does not add social login to acceptance criteria
- Suggests social login as a separate feature request
- Does not ignore the request — acknowledges and redirects

**Execution check:** no
