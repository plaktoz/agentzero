#!/usr/bin/env python3
"""
Connectivity check for all providers in agent-config.yml.
Makes a minimal (max_tokens=1) live API call per provider and prints pass/fail.

Usage:
    python3 scripts/check_providers.py
    python3 scripts/check_providers.py path/to/agent-config.yml
"""
import os
import re
import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent / "agent-config.yml"

# Cheapest probe model per provider (used only if none is configured in roles)
_PROBE_FALLBACKS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai":    "gpt-4o-mini",
    "google":    "gemini-1.5-flash",
    "mistral":   "mistral-small-latest",
}


def _resolve_env(value: str) -> str | None:
    """Replace ${ENV_VAR} with the actual env var value, or return the value as-is."""
    m = re.fullmatch(r"\$\{([^}]+)\}", value.strip())
    return os.environ.get(m.group(1)) if m else value


def _pick_model(config: dict, provider_name: str) -> str:
    """Pick the cheapest configured model for a provider, falling back to a known probe model."""
    default = config.get("default_provider")
    candidates = [
        cfg["model"]
        for cfg in config.get("roles", {}).values()
        if cfg.get("provider", default) == provider_name and "model" in cfg
    ]
    for keyword in ("haiku", "flash", "small", "mini"):
        for m in candidates:
            if keyword in m.lower():
                return m
    return candidates[0] if candidates else _PROBE_FALLBACKS.get(provider_name, "")


def _probe_anthropic(key: str, url: str, model: str) -> tuple[bool, str]:
    try:
        import anthropic
    except ImportError:
        return False, "anthropic SDK not installed — run: pip install anthropic"
    try:
        client = anthropic.Anthropic(api_key=key, base_url=url)
        resp = client.messages.create(
            model=model,
            max_tokens=1,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True, f"model={resp.model}"
    except Exception as exc:
        return False, str(exc)


def _probe_openai_compat(key: str, url: str, model: str) -> tuple[bool, str]:
    """Works for any OpenAI-compatible API (OpenAI, Mistral, etc.)."""
    try:
        import requests
    except ImportError:
        return False, "requests not installed — run: pip install requests"
    try:
        r = requests.post(
            f"{url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
            timeout=15,
        )
        r.raise_for_status()
        return True, f"model={r.json().get('model', '?')}"
    except Exception as exc:
        return False, str(exc)


def _probe_google(key: str, url: str, model: str) -> tuple[bool, str]:
    try:
        import requests
    except ImportError:
        return False, "requests not installed — run: pip install requests"
    try:
        endpoint = f"{url.rstrip('/')}/models/{model}:generateContent"
        r = requests.post(
            endpoint,
            params={"key": key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": "ping"}]}],
                "generationConfig": {"maxOutputTokens": 1},
            },
            timeout=15,
        )
        r.raise_for_status()
        return True, f"HTTP {r.status_code}"
    except Exception as exc:
        return False, str(exc)


_PROBERS = {
    "anthropic": _probe_anthropic,
    "openai":    _probe_openai_compat,
    "google":    _probe_google,
    "mistral":   _probe_openai_compat,  # Mistral uses an OpenAI-compatible endpoint
}


def main() -> int:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else CONFIG_PATH
    config = yaml.safe_load(config_path.read_text())
    providers = config.get("providers", {})

    if not providers:
        print("No providers found in agent-config.yml")
        return 1

    print(f"Probing {len(providers)} provider(s) (max_tokens=1)…\n")
    failures = 0

    for name, cfg in providers.items():
        raw_key = cfg.get("api_key", "")
        url     = cfg.get("api_url", "")
        key     = _resolve_env(raw_key)
        model   = _pick_model(config, name)

        if not key:
            m = re.search(r"\$\{([^}]+)\}", raw_key)
            var = m.group(1) if m else "API_KEY"
            print(f"  SKIP  {name:<14}  env var ${var} not set")
            failures += 1
            continue

        if not model:
            print(f"  SKIP  {name:<14}  no model configured for this provider")
            continue

        prober = _PROBERS.get(name)
        if not prober:
            print(f"  SKIP  {name:<14}  no prober implemented for this provider")
            continue

        print(f"  …     {name:<14}  {model}", end="  ", flush=True)
        ok, detail = prober(key, url, model)
        marker = "✓ OK  " if ok else "✗ FAIL"
        print(f"\r  {marker}  {name:<14}  {model}  —  {detail}")
        if not ok:
            failures += 1

    print()
    if failures:
        print(f"{failures} provider(s) failed or were skipped.")
        return 1
    print("All providers connected successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
