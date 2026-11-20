"""Test-wide guard (CLAUDE.md "Paid API calls" rule 4): tests and CI make 0 real model calls.

A developer's .env may set LLM_PROVIDER=anthropic and real credentials for planned real runs
(`cee.config` loads it at import). Every test therefore runs with:

1. LLM_PROVIDER=mock, unless the test passes a provider and a fake client itself (#214: the
   question planner reads the configured provider in ask()).
2. The three real-client builders, `cee.answer.llm.anthropic_client`, `openai_client` and
   `deepseek_client` (#242), replaced by
   a function that raises (#224). They are the only place `src/` builds an SDK client, and the
   planner and the answer path look them up at call time, so a test without a fake client fails
   before any SDK client exists, wherever the SDK would have found credentials.
3. Defence in depth for code that builds an SDK client directly: every ANTHROPIC_* / OPENAI_* /
   DEEPSEEK_* variable removed (API keys, auth token, profile name, workload-identity settings,
   admin key), the three base URLs pointed at a closed local port, and ANTHROPIC_CONFIG_DIR set to an empty folder.
   It is set, not unset, on purpose: a set config dir is an explicit profile choice, so a directly
   built anthropic.Anthropic() fails at construction (config file not found) instead of falling
   back to the user's on-disk default profile (Anthropic SDK 1.9.0 credential chain).
"""
import os

import pytest

CLOSED_PORT_URL = "http://127.0.0.1:9"


class PaidCallBlocked(RuntimeError):
    pass


def _blocked(*args, **kwargs):
    raise PaidCallBlocked("paid API call blocked in tests: pass a fake client")


@pytest.fixture(autouse=True)
def _no_paid_calls(monkeypatch, tmp_path_factory):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    from cee.answer import llm

    monkeypatch.setattr(llm, "anthropic_client", _blocked)
    monkeypatch.setattr(llm, "openai_client", _blocked)
    monkeypatch.setattr(llm, "deepseek_client", _blocked)
    for name in [n for n in os.environ if n.startswith(("ANTHROPIC_", "OPENAI_", "DEEPSEEK_"))]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", str(tmp_path_factory.mktemp("anthropic-config")))
    monkeypatch.setenv("ANTHROPIC_BASE_URL", CLOSED_PORT_URL)
    monkeypatch.setenv("OPENAI_BASE_URL", CLOSED_PORT_URL)
    monkeypatch.setenv("DEEPSEEK_BASE_URL", CLOSED_PORT_URL)
