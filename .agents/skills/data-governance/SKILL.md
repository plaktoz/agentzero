# Data Governance — Pre-flight Scanner

Pre-flight check that runs before any role reads source files or sends content to an external LLM API. Prevents secrets and PII from leaving the network unintentionally.

**Role:** Orchestrator  
**When:** Before activating Analyst, Architect, Coder, or any role that reads project source files  
**Autonomous:** yes — never asks the user unless secrets are found

---

## Step 1: Identify Files in Scope

Collect all files the next role will read:
- Source files listed in the task description or `state.md#code-artifacts`
- Any file the role's context brief references by path

Exclude:
- `pipeline/` — pipeline state files only, no source code
- `knowledge_base/` — internal KB, not sent to LLMs
- `.env`, `.env.*` — never read by any role under any circumstance
- `node_modules/`, `.venv/`, `dist/`, `build/` — generated output

---

## Step 2: Scan for Secrets

Run pattern matching against all in-scope files:

| Pattern | Description |
|---|---|
| `sk-[a-zA-Z0-9]{20,}` | API keys (Anthropic, OpenAI style) |
| `ghp_[a-zA-Z0-9]{36}` | GitHub personal access tokens |
| `AKIA[0-9A-Z]{16}` | AWS access key IDs |
| `[0-9a-f]{40}` in a credentials context | Generic secrets/tokens |
| `password\s*=\s*\S+` | Hardcoded passwords |
| `-----BEGIN (RSA\|EC\|OPENSSH) PRIVATE KEY-----` | Private keys |
| `[a-zA-Z0-9+/]{40,}={0,2}` near `secret\|token\|key\|pass` | Base64-encoded secrets |

---

## Step 3: Scan for PII

| Pattern | Description |
|---|---|
| `\b\d{3}-\d{2}-\d{4}\b` | US Social Security Numbers |
| `\b4[0-9]{12}(?:[0-9]{3})?\b` | Visa card numbers |
| `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z\|a-z]{2,}\b` in bulk | Email addresses (flag if >5 in one file) |
| Real names + addresses co-located | PII combination |

---

## Step 4: Act on Findings

**No findings:** proceed silently — do not log a pass message, just continue.

**Secrets found:**
1. **STOP** — do not activate the role
2. Report to the user:
   ```
   ⚠ Pre-flight scan found potential secrets in [file:line]:
   - [pattern matched] in [file]

   Options:
   a) Redact the values before proceeding (replace with placeholder)
   b) Mark as false positive — proceed anyway
   c) Abort this pipeline run
   ```
3. Wait for user choice before continuing

**PII found:**
1. Report to the user (non-blocking unless bulk PII):
   ```
   ⚠ Pre-flight scan found potential PII in [file:line]:
   - [pattern matched] in [file]

   Proceeding — confirm this data is handled appropriately.
   ```
2. Log the finding to `pipeline/[run-name]/log.md` with status `escalated`
3. Continue if user does not object

---

## Step 5: Local Model Override (sensitive codebases)

If `data_governance.require_local_model: true` is set in `agent-config.yml`, the Orchestrator must override the role's model with the local/self-hosted model specified in `data_governance.local_model` before activation.

Add to `agent-config.yml` when needed:
```yaml
data_governance:
  require_local_model: false     # set true for sensitive codebases
  local_model: ollama/llama3     # model to use when require_local_model: true
  pii_scan: true                 # enable PII scanning (default: true)
  secrets_scan: true             # enable secrets scanning (default: true)
```
