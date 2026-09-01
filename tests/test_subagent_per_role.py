"""
tests/test_subagent_per_role.py

TDD test suite for:
  - scripts/call_provider.py       (new file — does not exist yet → all tests red)
  - scripts/check_providers.py     (new verify_all_role_models() + --verify-models flag)

All tests are written FROM THE SPEC and FAIL before the code is written (red phase of TDD).
HTTP calls are mocked via unittest.mock — no real API calls are made.

AC reference:
  AC3  — provider credential resolution + exit codes
  AC4  — anthropic roles blocked immediately
  AC5  — state.md / log.md write contract
  AC6  — verify_all_role_models deduplication + --verify-models flag
  AC12 — --verify-models output is per role, not per unique (provider, model) pair
"""
import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# ---------------------------------------------------------------------------
# Path bootstrap — scripts/ must be importable
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# ---------------------------------------------------------------------------
# Shared fixture config
# ---------------------------------------------------------------------------
# 11 roles, 4 unique (provider, model) pairs:
#   (anthropic, claude-opus-4-8)   orchestrator, architect
#   (anthropic, claude-sonnet-5)   analyst, designer, coder, tester_arbiter, release_documenter
#   (anthropic, claude-haiku-4-5)  tester_generator_a, tester_consolidator, deployer
#   (openai, gpt-5.4)              tester_generator_b
MINIMAL_CONFIG = {
    "default_provider": "anthropic",
    "providers": {
        "anthropic": {
            "api_key": "${ANTHROPIC_API_KEY}",
            "api_url": "${ANTHROPIC_BASE_URL}",
        },
        "openai": {
            "api_key": "${OPENAI_API_KEY}",
            "api_url": "${OPENAI_BASE_URL}",
        },
    },
    "roles": {
        "orchestrator":        {"provider": "anthropic", "model": "claude-opus-4-8"},
        "analyst":             {"provider": "anthropic", "model": "claude-sonnet-5"},
        "designer":            {"provider": "anthropic", "model": "claude-sonnet-5"},
        "architect":           {"provider": "anthropic", "model": "claude-opus-4-8"},
        "coder":               {"provider": "anthropic", "model": "claude-sonnet-5"},
        "tester_generator_a":  {"provider": "anthropic", "model": "claude-haiku-4-5"},
        "tester_generator_b":  {"provider": "openai",    "model": "gpt-5.4"},
        "tester_arbiter":      {"provider": "anthropic", "model": "claude-sonnet-5"},
        "tester_consolidator": {"provider": "anthropic", "model": "claude-haiku-4-5"},
        "release_documenter":  {"provider": "anthropic", "model": "claude-sonnet-5"},
        "deployer":            {"provider": "anthropic", "model": "claude-haiku-4-5"},
    },
}

FAKE_ENV = {
    "ANTHROPIC_API_KEY":  "sk-ant-fake",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
    "OPENAI_API_KEY":     "sk-openai-fake",
    "OPENAI_BASE_URL":    "https://api.openai.com/v1",
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config_file(tmp_path):
    """Write MINIMAL_CONFIG to a temp YAML file.

    call_provider.py is expected to derive the pipeline root from this file's
    parent directory, so pipeline/test-run/ sits alongside it.
    """
    p = tmp_path / "agent-config.yml"
    p.write_text(yaml.dump(MINIMAL_CONFIG))
    return p


@pytest.fixture()
def pipeline_run(tmp_path):
    """Create pipeline/test-run/{state,log}.md under tmp_path; return the run dir."""
    run_dir = tmp_path / "pipeline" / "test-run"
    run_dir.mkdir(parents=True)
    (run_dir / "state.md").write_text("# State\n")
    (run_dir / "log.md").write_text("# Log\n")
    return run_dir


@pytest.fixture()
def context_file(tmp_path):
    """A minimal context brief file."""
    p = tmp_path / "context.txt"
    p.write_text("Summarise the pipeline state in one sentence.")
    return p


# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------


def _import_call_provider():
    """Import scripts/call_provider.py; reload if already cached.

    Will raise ModuleNotFoundError until the file is created → red phase.
    """
    name = "call_provider"
    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    return importlib.import_module(name)


def _import_check_providers():
    """Import scripts/check_providers.py; reload if already cached."""
    name = "check_providers"
    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    return importlib.import_module(name)


def _run_main(mod, argv, env_overrides=None):
    """Call mod.main() with patched sys.argv and optional env overrides.

    Returns the integer exit code returned by main().
    """
    env = {**os.environ, **(env_overrides or {})}
    with patch.dict(os.environ, env, clear=False):
        with patch.object(sys, "argv", argv):
            return mod.main()


def _call_provider_argv(config_file, pipeline_run, context_file, role="tester_generator_b"):
    """Build a standard sys.argv list for call_provider.py tests."""
    return [
        "call_provider.py",
        "--role", role,
        "--run", "test-run",
        "--context-file", str(context_file),
        "--config", str(config_file),
    ]


def _openai_env(pipeline_run):
    """Env overrides that supply a valid-looking OpenAI key and pipeline dir."""
    return {
        **FAKE_ENV,
        "PIPELINE_DIR": str(pipeline_run.parent),
    }


def _mock_200():
    """Build a mock requests.Response for a 200 chat-completions reply."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"choices": [{"message": {"content": "model output here"}}]}
    return resp


def _mock_http_error(status_code: int):
    """Build a mock requests.Response that raises HTTPError on raise_for_status()."""
    import requests as _req
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status.side_effect = _req.HTTPError(f"{status_code} Error")
    return resp


# ===========================================================================
# Test 1 + Test 2 — Anthropic role → exit 1, no API call (AC4)
# ===========================================================================


class TestCallProviderAnthropicBlock:
    """AC4: any role whose provider is anthropic must be rejected at entry, exit 1."""

    def test_orchestrator_exits_1(self, config_file, pipeline_run, context_file):
        # AC4: orchestrator uses anthropic → must exit 1, must not call requests.post.
        cp = _import_call_provider()
        with patch("requests.post") as mock_post:
            rc = _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file, role="orchestrator"),
                _openai_env(pipeline_run),
            )
        assert rc == 1
        mock_post.assert_not_called()

    def test_anthropic_role_does_not_write_state(self, config_file, pipeline_run, context_file):
        # AC4 + AC5: state.md must be untouched when the role's provider is anthropic.
        cp = _import_call_provider()
        original = (pipeline_run / "state.md").read_text()
        with patch("requests.post"):
            _run_main(
                cp,
                # tester_generator_a is also anthropic
                _call_provider_argv(config_file, pipeline_run, context_file, role="tester_generator_a"),
                _openai_env(pipeline_run),
            )
        assert (pipeline_run / "state.md").read_text() == original

    def test_anthropic_block_does_not_write_ok_to_log(self, config_file, pipeline_run, context_file):
        # AC4: log.md must not contain an ok row for an anthropic-blocked role.
        cp = _import_call_provider()
        with patch("requests.post"):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file, role="analyst"),
                _openai_env(pipeline_run),
            )
        log = (pipeline_run / "log.md").read_text()
        # An "ok" log row must not appear — the call never happened.
        assert "ok" not in log.lower()


# ===========================================================================
# Test 2 — Missing API key → exit 1 (AC3)
# ===========================================================================


class TestCallProviderMissingApiKey:
    """AC3: when the provider's env var is absent, exit 1 with descriptive error."""

    def test_missing_openai_key_exits_1(self, config_file, pipeline_run, context_file):
        # AC3: OPENAI_API_KEY absent → exit 1 before any HTTP call.
        cp = _import_call_provider()
        env_without_openai = {
            k: v for k, v in os.environ.items()
            if not k.startswith("OPENAI")
        }
        env_without_openai["PIPELINE_DIR"] = str(pipeline_run.parent)
        with patch("requests.post") as mock_post:
            with patch.dict(os.environ, env_without_openai, clear=True):
                with patch.object(sys, "argv",
                                  _call_provider_argv(config_file, pipeline_run, context_file)):
                    rc = cp.main()
        assert rc == 1
        mock_post.assert_not_called()

    def test_missing_key_leaves_state_unchanged(self, config_file, pipeline_run, context_file):
        # AC3 + AC5: state.md must not be modified on a missing-key failure.
        cp = _import_call_provider()
        original = (pipeline_run / "state.md").read_text()
        env_without_openai = {
            k: v for k, v in os.environ.items()
            if not k.startswith("OPENAI")
        }
        env_without_openai["PIPELINE_DIR"] = str(pipeline_run.parent)
        with patch.dict(os.environ, env_without_openai, clear=True):
            with patch.object(sys, "argv",
                              _call_provider_argv(config_file, pipeline_run, context_file)):
                cp.main()
        assert (pipeline_run / "state.md").read_text() == original


# ===========================================================================
# Test 3 — Successful 2xx response (AC3, AC5)
# ===========================================================================


class TestCallProviderSuccess:
    """AC3 + AC5: HTTP 2xx → start/end markers in state.md, ok row in log.md, exit 0."""

    def test_success_exits_0(self, config_file, pipeline_run, context_file):
        # AC3: exit 0 on HTTP 200.
        cp = _import_call_provider()
        with patch("requests.post", return_value=_mock_200()):
            rc = _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        assert rc == 0

    def test_success_state_has_start_marker(self, config_file, pipeline_run, context_file):
        # AC5: state.md must contain <!-- call_provider: tester_generator_b start -->.
        cp = _import_call_provider()
        with patch("requests.post", return_value=_mock_200()):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        state = (pipeline_run / "state.md").read_text()
        assert "<!-- call_provider: tester_generator_b start -->" in state

    def test_success_state_has_end_marker(self, config_file, pipeline_run, context_file):
        # AC5: state.md must contain <!-- call_provider: tester_generator_b end -->.
        cp = _import_call_provider()
        with patch("requests.post", return_value=_mock_200()):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        state = (pipeline_run / "state.md").read_text()
        assert "<!-- call_provider: tester_generator_b end -->" in state

    def test_success_log_has_ok_row(self, config_file, pipeline_run, context_file):
        # AC5: log.md must contain a row with status=ok.
        cp = _import_call_provider()
        with patch("requests.post", return_value=_mock_200()):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        log = (pipeline_run / "log.md").read_text()
        assert "ok" in log.lower(), f"Expected 'ok' in log.md, got:\n{log}"

    def test_success_model_output_between_markers(self, config_file, pipeline_run, context_file):
        # AC5: the model's reply text must appear between the start and end markers.
        cp = _import_call_provider()
        with patch("requests.post", return_value=_mock_200()):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        state = (pipeline_run / "state.md").read_text()
        start_idx = state.find("<!-- call_provider: tester_generator_b start -->")
        end_idx   = state.find("<!-- call_provider: tester_generator_b end -->")
        assert start_idx != -1 and end_idx != -1 and start_idx < end_idx
        between = state[start_idx:end_idx]
        assert "model output here" in between


# ===========================================================================
# Test 4 — Non-2xx response (AC3, AC5)
# ===========================================================================


class TestCallProviderNon2xx:
    """AC3 + AC5: HTTP non-2xx → state.md unchanged, error row in log.md, exit 1."""

    def test_non2xx_exits_1(self, config_file, pipeline_run, context_file):
        # AC3: HTTP 429 → exit 1. No internal retries.
        cp = _import_call_provider()
        with patch("requests.post", return_value=_mock_http_error(429)):
            rc = _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        assert rc == 1

    def test_non2xx_state_unchanged(self, config_file, pipeline_run, context_file):
        # AC5: state.md must not be written on non-2xx.
        cp = _import_call_provider()
        original = (pipeline_run / "state.md").read_text()
        with patch("requests.post", return_value=_mock_http_error(500)):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        assert (pipeline_run / "state.md").read_text() == original

    def test_non2xx_log_has_error_row(self, config_file, pipeline_run, context_file):
        # AC5: log.md must contain a row with status=error.
        cp = _import_call_provider()
        with patch("requests.post", return_value=_mock_http_error(503)):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        log = (pipeline_run / "log.md").read_text()
        assert "error" in log.lower(), f"Expected 'error' in log.md, got:\n{log}"

    def test_non2xx_no_start_marker_in_state(self, config_file, pipeline_run, context_file):
        # AC5: start marker must not appear in state.md on failure.
        cp = _import_call_provider()
        with patch("requests.post", return_value=_mock_http_error(422)):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        state = (pipeline_run / "state.md").read_text()
        assert "call_provider:" not in state


# ===========================================================================
# Test 5 — Network exception (AC3)
# ===========================================================================


class TestCallProviderNetworkException:
    """AC3: requests.RequestException → same outcome as non-2xx (exit 1, state unchanged)."""

    def test_connection_error_exits_1(self, config_file, pipeline_run, context_file):
        # AC3: ConnectionError → exit 1.
        # Import call_provider first (will raise ModuleNotFoundError until implemented),
        # then import requests (needed only for exception class after the module exists).
        cp = _import_call_provider()
        import requests as _req  # noqa: PLC0415 — deferred until call_provider exists
        with patch("requests.post", side_effect=_req.ConnectionError("network unreachable")):
            rc = _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        assert rc == 1

    def test_timeout_leaves_state_unchanged(self, config_file, pipeline_run, context_file):
        # AC3: Timeout → state.md not written.
        cp = _import_call_provider()
        import requests as _req  # noqa: PLC0415
        original = (pipeline_run / "state.md").read_text()
        with patch("requests.post", side_effect=_req.Timeout("120s timeout")):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        assert (pipeline_run / "state.md").read_text() == original

    def test_request_exception_log_has_error_row(self, config_file, pipeline_run, context_file):
        # AC3: any RequestException → log.md row with status=error.
        cp = _import_call_provider()
        import requests as _req  # noqa: PLC0415
        with patch("requests.post", side_effect=_req.RequestException("generic failure")):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        log = (pipeline_run / "log.md").read_text()
        assert "error" in log.lower()

    def test_no_markers_written_on_exception(self, config_file, pipeline_run, context_file):
        # AC5: no call_provider markers must appear in state.md after a network exception.
        cp = _import_call_provider()
        import requests as _req  # noqa: PLC0415
        with patch("requests.post", side_effect=_req.ConnectionError("refused")):
            _run_main(
                cp,
                _call_provider_argv(config_file, pipeline_run, context_file),
                _openai_env(pipeline_run),
            )
        state = (pipeline_run / "state.md").read_text()
        assert "call_provider:" not in state


# ===========================================================================
# Test 6 — --config flag points to a custom config file path
# ===========================================================================


class TestCallProviderCustomConfig:
    """Spec: --config PATH must make the script load that file instead of the default."""

    def test_custom_config_path_used_on_success(self, tmp_path, pipeline_run, context_file):
        # The script must load the custom config; a successful call still exits 0.
        custom = tmp_path / "my-custom-config.yml"
        custom.write_text(yaml.dump(MINIMAL_CONFIG))

        cp = _import_call_provider()
        with patch("requests.post", return_value=_mock_200()):
            rc = _run_main(
                cp,
                [
                    "call_provider.py",
                    "--role", "tester_generator_b",
                    "--run", "test-run",
                    "--context-file", str(context_file),
                    "--config", str(custom),          # non-default location
                ],
                {**FAKE_ENV, "PIPELINE_DIR": str(pipeline_run.parent)},
            )
        assert rc == 0

    def test_nonexistent_config_path_exits_nonzero(self, pipeline_run, context_file):
        # --config pointing at a missing file must produce a non-zero exit.
        cp = _import_call_provider()
        rc = _run_main(
            cp,
            [
                "call_provider.py",
                "--role", "tester_generator_b",
                "--run", "test-run",
                "--context-file", str(context_file),
                "--config", "/nonexistent/path/agent-config.yml",
            ],
            {"PIPELINE_DIR": str(pipeline_run.parent)},
        )
        assert rc != 0


# ===========================================================================
# Test 7 — verify_all_role_models deduplicates (provider, model) pairs (AC6)
# ===========================================================================


class TestVerifyAllRoleModelsDeduplication:
    """AC6: 11 roles with 4 unique (provider, model) pairs must trigger 4 probes, not 11."""

    def test_11_roles_produce_4_prober_calls(self):
        # AC6: one probe per unique (provider, model) pair; MINIMAL_CONFIG → 4 calls.
        cp = _import_check_providers()
        assert hasattr(cp, "verify_all_role_models"), (
            "verify_all_role_models not found in check_providers — implementation not written yet"
        )

        calls: list[tuple] = []

        def recording_prober(key, url, model):
            calls.append((url, model))
            return True, f"model={model}"

        patched = {p: recording_prober for p in ("anthropic", "openai", "mistral", "google")}

        with patch.dict(os.environ, FAKE_ENV):
            with patch.object(cp, "_PROBERS", patched):
                cp.verify_all_role_models(MINIMAL_CONFIG)

        assert len(calls) == 4, (
            f"Expected exactly 4 probe calls (one per unique pair), "
            f"got {len(calls)}: {calls}"
        )

    def test_return_keys_are_provider_model_tuples(self):
        # AC6: return dict keys must be (provider, model) tuples, not role names.
        cp = _import_check_providers()
        assert hasattr(cp, "verify_all_role_models")

        def ok_prober(key, url, model):
            return True, f"model={model}"

        with patch.dict(os.environ, FAKE_ENV):
            with patch.object(cp, "_PROBERS", {"anthropic": ok_prober, "openai": ok_prober}):
                result = cp.verify_all_role_models(MINIMAL_CONFIG)

        assert isinstance(result, dict)
        for key in result:
            assert isinstance(key, tuple) and len(key) == 2, (
                f"Expected (provider, model) tuple key, got {key!r}"
            )

    def test_exactly_4_unique_pairs_in_result(self):
        # AC6: result must contain exactly 4 keys for MINIMAL_CONFIG.
        cp = _import_check_providers()
        assert hasattr(cp, "verify_all_role_models")

        def ok_prober(key, url, model):
            return True, f"model={model}"

        with patch.dict(os.environ, FAKE_ENV):
            with patch.object(cp, "_PROBERS", {"anthropic": ok_prober, "openai": ok_prober}):
                result = cp.verify_all_role_models(MINIMAL_CONFIG)

        assert len(result) == 4, (
            f"Expected 4 unique (provider, model) pairs in result, got {len(result)}: "
            f"{list(result.keys())}"
        )


# ===========================================================================
# Test 8 — verify_all_role_models returns False for a failing probe (AC6)
# ===========================================================================


class TestVerifyAllRoleModelsFailingProbe:
    """AC6: a prober returning (False, ...) must be reflected as ok=False in the result."""

    def test_failing_openai_probe_reflected_as_false(self):
        # AC6: openai prober fails → result[("openai", "gpt-5.4")] == (False, ...).
        cp = _import_check_providers()
        assert hasattr(cp, "verify_all_role_models")

        def ok_prober(key, url, model):
            return True, f"model={model}"

        def failing_prober(key, url, model):
            return False, "401 Unauthorized"

        patched = {"anthropic": ok_prober, "openai": failing_prober}

        with patch.dict(os.environ, FAKE_ENV):
            with patch.object(cp, "_PROBERS", patched):
                result = cp.verify_all_role_models(MINIMAL_CONFIG)

        entry = result.get(("openai", "gpt-5.4"))
        assert entry is not None, "Expected ('openai', 'gpt-5.4') key in result"
        ok, detail = entry
        assert ok is False, f"Expected ok=False for failing openai probe, got {ok}"

    def test_passing_probes_have_ok_true(self):
        # AC6: successful probers must yield ok=True for each pair.
        cp = _import_check_providers()
        assert hasattr(cp, "verify_all_role_models")

        def ok_prober(key, url, model):
            return True, f"model={model}"

        with patch.dict(os.environ, FAKE_ENV):
            with patch.object(cp, "_PROBERS", {"anthropic": ok_prober, "openai": ok_prober}):
                result = cp.verify_all_role_models(MINIMAL_CONFIG)

        for pair, (ok, _) in result.items():
            assert ok is True, f"Expected ok=True for {pair}"

    def test_partial_failure_does_not_affect_other_pairs(self):
        # AC6: one failing pair must not corrupt the status of other pairs.
        cp = _import_check_providers()
        assert hasattr(cp, "verify_all_role_models")

        def ok_prober(key, url, model):
            return True, "ok"

        def failing_prober(key, url, model):
            return False, "timeout"

        patched = {"anthropic": ok_prober, "openai": failing_prober}

        with patch.dict(os.environ, FAKE_ENV):
            with patch.object(cp, "_PROBERS", patched):
                result = cp.verify_all_role_models(MINIMAL_CONFIG)

        # All anthropic pairs must still be True
        for pair, (ok, _) in result.items():
            provider, _ = pair
            if provider == "anthropic":
                assert ok is True, f"anthropic pair {pair} unexpectedly failed"


# ===========================================================================
# Test 9 — --verify-models exits 1 when any probe fails (AC6)
# ===========================================================================


class TestVerifyModelsFlagExits1OnFailure:
    """AC6: --verify-models must exit 1 when verify_all_role_models contains any False."""

    def test_exits_1_on_partial_failure(self, config_file):
        # AC6: one failing pair → exit 1.
        cp = _import_check_providers()

        failing_result = {
            ("anthropic", "claude-haiku-4-5"): (False, "connection refused"),
            ("anthropic", "claude-sonnet-5"):  (True,  "ok"),
            ("anthropic", "claude-opus-4-8"):  (True,  "ok"),
            ("openai",    "gpt-5.4"):          (True,  "ok"),
        }

        with patch.object(cp, "verify_all_role_models", return_value=failing_result):
            with patch.dict(os.environ, FAKE_ENV):
                rc = _run_main(
                    cp,
                    ["check_providers.py", str(config_file), "--verify-models"],
                )

        assert rc == 1, f"Expected exit 1 when a probe fails, got {rc}"

    def test_exits_1_on_all_failures(self, config_file):
        # AC6: all failing → exit 1.
        cp = _import_check_providers()

        all_fail = {
            ("anthropic", "claude-haiku-4-5"): (False, "refused"),
            ("anthropic", "claude-sonnet-5"):  (False, "refused"),
            ("anthropic", "claude-opus-4-8"):  (False, "refused"),
            ("openai",    "gpt-5.4"):          (False, "refused"),
        }

        with patch.object(cp, "verify_all_role_models", return_value=all_fail):
            with patch.dict(os.environ, FAKE_ENV):
                rc = _run_main(
                    cp,
                    ["check_providers.py", str(config_file), "--verify-models"],
                )

        assert rc == 1


# ===========================================================================
# Test 10 — --verify-models exits 0 when all probes succeed (AC6)
# ===========================================================================


class TestVerifyModelsFlagExits0OnSuccess:
    """AC6: --verify-models must exit 0 when all probes return True."""

    def test_exits_0_when_all_pass(self, config_file):
        # AC6: all (provider, model) pairs probed successfully → exit 0.
        cp = _import_check_providers()

        all_pass = {
            ("anthropic", "claude-opus-4-8"):  (True, "ok"),
            ("anthropic", "claude-sonnet-5"):  (True, "ok"),
            ("anthropic", "claude-haiku-4-5"): (True, "ok"),
            ("openai",    "gpt-5.4"):          (True, "ok"),
        }

        with patch.object(cp, "verify_all_role_models", return_value=all_pass):
            with patch.dict(os.environ, FAKE_ENV):
                rc = _run_main(
                    cp,
                    ["check_providers.py", str(config_file), "--verify-models"],
                )

        assert rc == 0, f"Expected exit 0 when all probes succeed, got {rc}"


# ===========================================================================
# Test 11 — --verify-models output has one line per role, not per unique pair (AC12)
# ===========================================================================


class TestVerifyModelsOutputPerRole:
    """AC12: the output table must contain one row per role (11), not one per unique pair (4)."""

    def _run_and_capture(self, cp, config_file, capsys, probe_results):
        with patch.object(cp, "verify_all_role_models", return_value=probe_results):
            with patch.dict(os.environ, FAKE_ENV):
                with patch.object(sys, "argv",
                                  ["check_providers.py", str(config_file), "--verify-models"]):
                    cp.main()
        return capsys.readouterr()

    def test_output_has_at_least_one_line_per_role(self, config_file, capsys):
        # AC12: 11 roles → ≥11 lines that mention a role name.
        cp = _import_check_providers()

        probe_results = {
            ("anthropic", "claude-opus-4-8"):  (True, "ok"),
            ("anthropic", "claude-sonnet-5"):  (True, "ok"),
            ("anthropic", "claude-haiku-4-5"): (True, "ok"),
            ("openai",    "gpt-5.4"):          (True, "ok"),
        }

        captured = self._run_and_capture(cp, config_file, capsys, probe_results)
        role_names = set(MINIMAL_CONFIG["roles"].keys())
        role_lines = [
            line for line in captured.out.splitlines()
            if any(role in line for role in role_names)
        ]
        expected = len(role_names)  # 11
        assert len(role_lines) >= expected, (
            f"Expected ≥{expected} role-name lines in output, got {len(role_lines)}.\n"
            f"Output:\n{captured.out}"
        )

    def test_output_not_collapsed_to_unique_pairs(self, config_file, capsys):
        # AC12 (guard): if the impl incorrectly prints one line per unique pair it emits only 4.
        # This test ensures the count exceeds 4.
        cp = _import_check_providers()

        probe_results = {
            ("anthropic", "claude-opus-4-8"):  (True, "ok"),
            ("anthropic", "claude-sonnet-5"):  (True, "ok"),
            ("anthropic", "claude-haiku-4-5"): (True, "ok"),
            ("openai",    "gpt-5.4"):          (True, "ok"),
        }

        captured = self._run_and_capture(cp, config_file, capsys, probe_results)
        role_names = set(MINIMAL_CONFIG["roles"].keys())
        role_lines = [
            line for line in captured.out.splitlines()
            if any(role in line for role in role_names)
        ]
        unique_pairs = 4
        assert len(role_lines) > unique_pairs, (
            f"Output contains only {len(role_lines)} role lines (≤ {unique_pairs} unique pairs). "
            "Implementation is likely printing per unique pair instead of per role."
        )

    def test_every_role_name_appears_in_output(self, config_file, capsys):
        # AC12: each of the 11 role names must appear somewhere in the output.
        cp = _import_check_providers()

        probe_results = {
            ("anthropic", "claude-opus-4-8"):  (True, "ok"),
            ("anthropic", "claude-sonnet-5"):  (True, "ok"),
            ("anthropic", "claude-haiku-4-5"): (True, "ok"),
            ("openai",    "gpt-5.4"):          (True, "ok"),
        }

        captured = self._run_and_capture(cp, config_file, capsys, probe_results)
        missing = [
            role for role in MINIMAL_CONFIG["roles"]
            if role not in captured.out
        ]
        assert not missing, (
            f"These role names were absent from --verify-models output: {missing}\n"
            f"Output:\n{captured.out}"
        )


# ===========================================================================
# Test 12 — no-flag behavior unchanged: runs connectivity check, not verify_all_role_models (AC6)
# ===========================================================================


class TestNoFlagBehaviorUnchanged:
    """AC6: without --verify-models the original per-provider connectivity check must run."""

    def test_no_flag_does_not_call_verify_all_role_models(self, config_file):
        # AC6: verify_all_role_models must NOT be invoked when the flag is absent.
        cp = _import_check_providers()

        called: list[bool] = []

        def spy_verify(config):
            called.append(True)
            return {}

        def ok_prober(key, url, model):
            return True, f"model={model}"

        patched_probers = {"anthropic": ok_prober, "openai": ok_prober}

        with patch.dict(os.environ, FAKE_ENV):
            with patch.object(cp, "_PROBERS", patched_probers):
                if hasattr(cp, "verify_all_role_models"):
                    with patch.object(cp, "verify_all_role_models", side_effect=spy_verify):
                        _run_main(cp, ["check_providers.py", str(config_file)])
                else:
                    # Function not yet implemented → original main() can still be tested
                    _run_main(cp, ["check_providers.py", str(config_file)])

        assert not called, (
            "verify_all_role_models was called even though --verify-models flag was absent"
        )

    def test_no_flag_calls_existing_probers(self, config_file):
        # AC6: original flow must still invoke _PROBERS (the per-provider connectivity check).
        cp = _import_check_providers()

        prober_calls: list[str] = []

        def recording_prober(key, url, model):
            prober_calls.append(url)
            return True, f"model={model}"

        patched_probers = {"anthropic": recording_prober, "openai": recording_prober}

        with patch.dict(os.environ, FAKE_ENV):
            with patch.object(cp, "_PROBERS", patched_probers):
                _run_main(cp, ["check_providers.py", str(config_file)])

        # MINIMAL_CONFIG has 2 providers → existing main() should call a prober at least once
        assert len(prober_calls) >= 1, (
            "Expected the existing connectivity check to invoke at least one prober, "
            f"but got {len(prober_calls)} calls. No-flag path may be broken."
        )
