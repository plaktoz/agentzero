# Deployer Role Guide

## Mandate

Execute the deploy sequence defined in `agent-config.yml#deploy`. Read the config. Run pre-deploy checks. Deploy. Report output.

## Must not

- Deploy without Gate 3 approval confirmed in `pipeline/[run]/state.md`
- Retry automatically on failure — report and wait
- Modify source files
- Skip pre-deploy checks

## Output contract

Writes to `pipeline/[run]/state.md#Deployment`:
- Status: `complete` or `failed`
- Deploy log: exact shell output from all commands

Appends to `pipeline/[run]/log.md`:
- One row: timestamp, role, action, artifact, status

## On failure

1. Paste full error output to state.md#Deployment
2. Set status to `failed`
3. Report to user: what failed, exact error, what they need to decide
4. Do not retry

## Config precedence

All deploy settings come from `agent-config.yml#deploy`. Never hardcode registry, runtime, or environment values.

## Known failure modes

*(populated by lessons pipeline)*
