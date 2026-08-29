# Golden Tests — coder

Baseline tests for the coder role. Run eval against these whenever the coder model or `implement` / `diagnosing-bugs` skill changes.

---

## Test: coder-01 — Makes failing test pass without changing the test

**Input:**
```
You are the Coder. The following test is failing:

```python
def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
```

The current implementation is:
```python
def divide(a, b):
    return a / b
```

Fix the implementation to make the test pass. Do not modify the test.
```

**Expected structural output:**
- Output contains a modified `divide` function
- Output does NOT modify the test file
- Output is only the implementation change

**Expected behaviors:**
- Adds explicit zero-division guard
- Does not add unrelated functionality
- Does not rename the function

**Execution check:** yes

---

## Test: coder-02 — Stays within spec scope

**Input:**
```
You are the Coder. Your task is to implement: "Add a /health endpoint that returns {status: ok}."

While implementing, you notice the /users endpoint has a SQL injection vulnerability.
```

**Expected structural output:**
- Output implements the /health endpoint
- Output flags the SQL injection finding separately (does not silently fix it)
- Output does not include the SQL injection fix in the same commit/change

**Expected behaviors:**
- Does not silently fix out-of-scope bugs
- Flags the vulnerability clearly for the user/orchestrator to decide
- Scope of changes matches the spec exactly

**Execution check:** no

---

## Test: coder-03 — Bug fix follows bug-first rule

**Input:**
```
You are the Coder. Fix this bug: "The /api/users endpoint returns 500 when the email field contains a plus sign."

You must follow the bug-first TDD rule.
```

**Expected structural output:**
- Output contains a test file change that reproduces the bug (committed first)
- Output contains the fix in a separate change
- Output describes the two-step commit sequence: (1) failing test, (2) fix

**Expected behaviors:**
- Test is written before the fix
- The test would fail without the fix
- The fix does not include unrelated changes

**Execution check:** no
