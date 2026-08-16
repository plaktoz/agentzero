# Deploy Skill

You are the Deployer agent. Follow these steps exactly.

## Step 1: Read Configuration

Read `agent-config.yml` and extract the `deploy` section:
- `container_runtime` — docker | podman | none
- `registry` — docker.io | ghcr.io | local | none
- `target_environment` — local | staging | production
- `build_tool` — dockerfile | compose | none
- `pre_deploy_checks` — list of checks to run before deploying

## Step 2: Run Pre-Deploy Checks

For each item in `pre_deploy_checks`:

**tests:**
Read `pipeline-state.md` — confirm Gate 3 status is `approved`. If not approved, STOP and tell the user Gate 3 must be approved before deploying.

**lint:**
Run the project's lint command. Find it by checking:
1. `package.json` scripts section for a `lint` key
2. `Makefile` for a `lint` target
3. `pyproject.toml` or `setup.cfg` for a linter config
If no lint command is found, log `lint: skipped (no lint command found)` and continue.

## Step 3: Build & Deploy

Branch on `container_runtime`:

### container_runtime: none

Run the project's standard build/start commands:
1. Check for `Makefile` → run `make build` then `make start` if targets exist
2. Check for `package.json` → run `npm run build` then `npm start`
3. Check for `pyproject.toml` → run `python -m build` or `pip install -e .`
4. If none found: tell the user no build command was detected and ask them to specify one.

### container_runtime: docker

1. Build: `docker build -t <project-name>:<git-short-sha> .`
   - `<project-name>` = basename of the project directory
   - `<git-short-sha>` = output of `git rev-parse --short HEAD`
2. If `registry` is not `none`: tag and push
   - `docker tag <project-name>:<git-short-sha> <registry>/<project-name>:<git-short-sha>`
   - `docker push <registry>/<project-name>:<git-short-sha>`
3. If `build_tool: compose`: run `docker compose up -d --build` instead of steps 1-2
4. If `build_tool` is NOT `compose`: run the container
   `docker run -d --name <project-name> <project-name>:<git-short-sha>`
   If `build_tool: compose`: skip this step — `compose up` already started containers.

### container_runtime: podman

Same steps as docker, replacing `docker` with `podman` in every command.
`docker compose` becomes `podman compose`.
Step 4 conditional applies identically: only run `podman run` when `build_tool` is NOT `compose`.

## Step 4: Write to pipeline/[run-name]/state.md

The run name is passed by the Orchestrator. Append to the `## Deployment` section of `pipeline/[run-name]/state.md`:

```markdown
**Status:** complete

**Deploy Log:**
```
[paste actual shell output from deploy commands]
```
```

Also update the top-level `**Status:**` field in `state.md` to `complete`.

## Step 5: Write to pipeline/[run-name]/log.md

Append one row:
```
| [timestamp] | Deployer | Deployed [container_runtime] to [target_environment] | pipeline/[run-name]/state.md#deployment | complete |
```

## On Any Error

If any command fails:
1. Paste the full error output
2. Write `**Status:** failed` to `pipeline/[run-name]/state.md#deployment`
3. Do NOT attempt to retry automatically — report the error to the user and wait
