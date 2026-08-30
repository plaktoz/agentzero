# Project Config

Configure or reconfigure this project's deployment settings. Can be run at any time — not just on first setup.

Announce: "Starting project config wizard. I'll ask you up to 5 questions and update `agent-config.yml`."

---

## Question 1: Container Runtime

Ask: "What container runtime will you use for this project?"

Options:
- `none` — run the app directly without containers (default for new projects)
- `docker` — use Docker to build and run
- `podman` — use Podman (rootless Docker alternative)

Recommendation: `none` for local development unless the app has external service dependencies.

Save as `container_runtime`.

---

## Question 2: Container Registry

Only ask if `container_runtime` is `docker` or `podman`.

Ask: "Where will you push container images?"

Options:
- `none` — build locally, don't push
- `docker.io` — Docker Hub
- `ghcr.io` — GitHub Container Registry
- `local` — local registry at localhost:5000

Recommendation: `none` for local-only development.

Save as `registry`. If `container_runtime` is `none`, set `registry: none` automatically.

---

## Question 3: Build Tool

Only ask if `container_runtime` is `docker` or `podman`.

Ask: "How will you define the container build?"

Options:
- `dockerfile` — single Dockerfile
- `compose` — docker-compose.yml / compose.yaml

Recommendation: `dockerfile` for single-service apps, `compose` for multiple services.

Save as `build_tool`. If `container_runtime` is `none`, set `build_tool: none` automatically.

---

## Question 4: Target Environment

Ask: "What is the target environment?"

Options:
- `local` — running on your machine only
- `staging` — a shared test environment
- `production` — live environment

Recommendation: `local` to start.

Save as `target_environment`.

---

## Question 5: Pre-Deploy Checks

Ask: "Which checks should run before every deploy? (pick any combination)"

Options:
- `tests` — confirm Gate 3 approved before deploying
- `lint` — run the project's lint command

Recommendation: both.

Save as `pre_deploy_checks` (a YAML list).

---

## Write to agent-config.yml

After all answers, update the `deploy` section:

1. Read the current `agent-config.yml`
2. Replace the `deploy` section:

```yaml
deploy:
  container_runtime: <answer 1>
  registry: <answer 2>
  target_environment: <answer 4>
  build_tool: <answer 3>
  pre_deploy_checks:
    - <answer 5 items>
```

3. Write the updated file
4. Run `python scripts/validate_config.py` to confirm the result is valid
5. Report: "Project config complete. Here is your deploy configuration: [show deploy section]"
