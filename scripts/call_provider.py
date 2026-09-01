#!/usr/bin/env python3
"""
Cross-provider API caller for pipeline roles configured outside Anthropic.

Usage:
    python3 scripts/call_provider.py --role ROLE --run RUN --context-file PATH [--config PATH]

Exit codes:
    0 — API call succeeded; output appended to state.md and log row written.
    1 — Configuration error (anthropic role, missing key, bad config) or API failure.
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Default config path — repo root (same parent as the scripts/ directory)
# ---------------------------------------------------------------------------
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "agent-config.yml"


def _resolve_env(value: str) -> str | None:
    """Replace ${ENV_VAR} with the actual env var value, or return the value as-is."""
    m = re.fullmatch(r"\$\{([^}]+)\}", value.strip())
    return os.environ.get(m.group(1)) if m else value


def main() -> int:
    # ------------------------------------------------------------------
    # Step 1: Parse arguments
    # ------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Cross-provider API caller for pipeline roles.",
    )
    parser.add_argument("--role", required=True, help="Role name as in agent-config.yml")
    parser.add_argument("--run", required=True, help="Pipeline run directory name under pipeline/")
    parser.add_argument("--context-file", required=True, help="Path to context brief file")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to agent-config.yml (default: repo root)",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Step 2: Load .env from repo root
    # ------------------------------------------------------------------
    load_dotenv(Path(__file__).parent.parent / ".env")

    # ------------------------------------------------------------------
    # Step 3: Load and parse agent-config.yml
    # ------------------------------------------------------------------
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG_PATH
    try:
        config = yaml.safe_load(config_path.read_text())
    except Exception as exc:
        print(f"error: could not load config from {config_path}: {exc}", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------
    # Step 4: Resolve role config
    # ------------------------------------------------------------------
    roles = config.get("roles", {})
    if args.role not in roles:
        print(f"error: role '{args.role}' not found in config", file=sys.stderr)
        return 1

    role_cfg = roles[args.role]
    default_provider = config.get("default_provider", "anthropic")
    provider_name = role_cfg.get("provider", default_provider)
    model = role_cfg.get("model", "")

    # ------------------------------------------------------------------
    # Step 5: Resolve provider API key and URL
    # ------------------------------------------------------------------
    providers = config.get("providers", {})
    if provider_name not in providers:
        print(
            f"error: provider '{provider_name}' for role '{args.role}' not found in config",
            file=sys.stderr,
        )
        return 1

    provider_cfg = providers[provider_name]
    raw_key = provider_cfg.get("api_key", "")
    raw_url = provider_cfg.get("api_url", "")

    # ------------------------------------------------------------------
    # Step 6: Block Anthropic roles immediately — no API call
    # ------------------------------------------------------------------
    if provider_name == "anthropic":
        print(
            f"error: role '{args.role}' uses provider 'anthropic' — "
            "invoke via the Agent tool instead of call_provider.py for Anthropic roles.",
            file=sys.stderr,
        )
        return 1

    # ------------------------------------------------------------------
    # Step 7: Validate API key
    # ------------------------------------------------------------------
    api_key = _resolve_env(raw_key)
    api_url = _resolve_env(raw_url) or raw_url

    if not api_key:
        m = re.search(r"\$\{([^}]+)\}", raw_key)
        var_name = m.group(1) if m else "API_KEY"
        print(
            f"error: API key env var ${var_name} for provider '{provider_name}' is not set or empty.",
            file=sys.stderr,
        )
        return 1

    # ------------------------------------------------------------------
    # Step 8: Read context brief
    # ------------------------------------------------------------------
    context_path = Path(args.context_file)
    try:
        context = context_path.read_text()
    except Exception as exc:
        print(f"error: could not read context file {context_path}: {exc}", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------
    # Determine pipeline directory and run paths
    # ------------------------------------------------------------------
    pipeline_dir_env = os.environ.get("PIPELINE_DIR")
    if pipeline_dir_env:
        pipeline_dir = Path(pipeline_dir_env)
    else:
        pipeline_dir = config_path.parent / "pipeline"

    run_dir = pipeline_dir / args.run
    state_path = run_dir / "state.md"
    log_path = run_dir / "log.md"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ------------------------------------------------------------------
    # API call
    # ------------------------------------------------------------------
    try:
        if provider_name == "google":
            endpoint = f"{api_url.rstrip('/')}/models/{model}:generateContent"
            response = requests.post(
                endpoint,
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": context}]}]},
                timeout=120,
            )
        else:
            # OpenAI-compatible (openai, mistral)
            endpoint = f"{api_url.rstrip('/')}/chat/completions"
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "messages": [{"role": "user", "content": context}]},
                timeout=120,
            )

        response.raise_for_status()

        # ------------------------------------------------------------------
        # Success path (HTTP 2xx)
        # ------------------------------------------------------------------
        if provider_name == "google":
            output_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            output_text = response.json()["choices"][0]["message"]["content"]

        # Append model output to state.md with start/end markers
        with open(state_path, "a") as f:
            f.write(
                f"\n<!-- call_provider: {args.role} start -->\n"
                f"{output_text}\n"
                f"<!-- call_provider: {args.role} end -->\n"
            )

        # Append ok log row
        with open(log_path, "a") as f:
            f.write(
                f"| {timestamp} | {args.run} | {args.role} | {model}"
                f" | {provider_name} | ok | cross-provider call |\n"
            )

        return 0

    except requests.RequestException as exc:
        error_msg = str(exc)
        print(
            f"error: API call failed for provider '{provider_name}', model '{model}': {error_msg}",
            file=sys.stderr,
        )

        # Append error log row — do NOT write to state.md
        detail = error_msg[:200]
        try:
            with open(log_path, "a") as f:
                f.write(
                    f"| {timestamp} | {args.run} | {args.role} | {model}"
                    f" | {provider_name} | error | {detail} |\n"
                )
        except Exception:
            pass  # Do not mask the original API error

        return 1


if __name__ == "__main__":
    sys.exit(main())
