"""Tests cannot reach a paid API (#224, CLAUDE.md "Paid API calls" rule 4).

tests/conftest.py stubs the two real-client builders and clears the credential environment. These
tests prove it with a request counter on the SDKs' transport: anthropic 1.9.0 and openai 3.22.1
send through httpx2 (their client wrappers subclass httpx2.Client / httpx2.AsyncClient and define
no send of their own; httpx2.Client is not an httpx.Client). The counter records every request and
raises a connection error, so nothing leaves the machine even in the control test.

anthropic, openai and httpx2 are core requirements (requirements.txt), so they are imported
unconditionally. Plain httpx is not: it only arrives with optional tools (edgartools,
huggingface_hub), and CI installs requirements.txt only. Its counter is extra cover, patched when
httpx is installed; without httpx nothing can send through it.
"""
import json
import os
import time

import anthropic
import httpx2
import openai
import pytest

try:
    import httpx
except ImportError:  # not a core requirement; see the docstring
    httpx = None

from cee.answer import llm
from cee.retrieve import fts, planner
from tests.conftest import CLOSED_PORT_URL, PaidCallBlocked


@pytest.fixture
def sent(monkeypatch):
    """Requests that reached the SDK transport (each one raised a ConnectError)."""
    seen: list = []

    def record(self, request, *args, **kwargs):
        seen.append({"url": str(request.url), "auth": kwargs.get("auth")})
        raise httpx2.ConnectError("blocked by test", request=request)

    async def arecord(self, request, *args, **kwargs):
        return record(self, request, *args, **kwargs)

    def record_httpx(self, request, *args, **kwargs):
        seen.append({"url": str(request.url), "auth": kwargs.get("auth")})
        raise httpx.ConnectError("blocked by test", request=request)

    async def arecord_httpx(self, request, *args, **kwargs):
        return record_httpx(self, request, *args, **kwargs)

    monkeypatch.setattr(httpx2.Client, "send", record)
    monkeypatch.setattr(httpx2.AsyncClient, "send", arecord)
    if httpx is not None:
        monkeypatch.setattr(httpx.Client, "send", record_httpx)
        monkeypatch.setattr(httpx.AsyncClient, "send", arecord_httpx)
    return seen


def _fake_profile(folder) -> None:
    """A valid on-disk Anthropic profile (SDK 1.9.0 format) with a dummy token whose base URL is a
    closed local port (the SDK allows plain http only for localhost / 127.0.0.1 / [::1])."""
    (folder / "configs").mkdir()
    (folder / "credentials").mkdir()
    (folder / "configs" / "default.json").write_text(json.dumps(
        {"authentication": {"type": "user_oauth"}, "base_url": CLOSED_PORT_URL}), encoding="utf-8")
    (folder / "credentials" / "default.json").write_text(json.dumps(
        {"type": "oauth_token", "access_token": "dummy-token", "expires_at": int(time.time()) + 86400}),
        encoding="utf-8")


def _budget_question() -> fts.Query:
    """A question the planner would really be called for: token-budget mode, searchable, 2 firms."""
    q = fts.resolve("How do Morgan Stanley and Raymond James approach advisor recruiting?")
    assert fts.budget_tokens(q) is not None and fts.searchable(q) and len(q.entities) == 2
    return q


def test_environment_is_cleared(sent):
    assert os.environ["LLM_PROVIDER"] == "mock"
    left = {n for n in os.environ if n.startswith(("ANTHROPIC_", "OPENAI_"))}
    assert left == {"ANTHROPIC_CONFIG_DIR", "ANTHROPIC_BASE_URL", "OPENAI_BASE_URL"}
    assert os.listdir(os.environ["ANTHROPIC_CONFIG_DIR"]) == []
    assert os.environ["ANTHROPIC_BASE_URL"] == os.environ["OPENAI_BASE_URL"] == CLOSED_PORT_URL
    with pytest.raises(anthropic.AnthropicError):   # CredentialsError: no profile in the empty dir
        anthropic.Anthropic()
    with pytest.raises(openai.OpenAIError):         # no key
        openai.OpenAI()
    assert sent == []


def test_client_builders_are_blocked(sent):
    with pytest.raises(PaidCallBlocked, match="blocked"):
        llm.anthropic_client()
    with pytest.raises(PaidCallBlocked, match="blocked"):
        llm.openai_client()
    assert sent == []


def test_profile_on_disk_cannot_reach_the_api(sent, monkeypatch, tmp_path):
    _fake_profile(tmp_path)
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("PLANNER", "on")

    # Control: an SDK client built directly picks up the profile, and its request reaches the
    # counter (so the counter sees SDK traffic) with the profile's token auth.
    client = anthropic.Anthropic(max_retries=0)
    with pytest.raises(anthropic.APIConnectionError):
        client.messages.create(model="x", max_tokens=1, messages=[{"role": "user", "content": "hi"}])
    assert len(sent) == 1
    assert sent[0]["url"] == f"{CLOSED_PORT_URL}/v1/messages"
    assert type(sent[0]["auth"]).__name__ == "AccessTokenAuth"

    # Guard: the project's code paths, same profile, no fake client: blocked, 0 requests.
    sent.clear()
    plan = planner.plan_question(_budget_question(), "anthropic")
    assert plan.source == "fallback" and "blocked" in plan.error and plan.calls == 1
    with pytest.raises(PaidCallBlocked, match="blocked"):
        llm.generate("question", [], provider="anthropic")
    with pytest.raises(PaidCallBlocked, match="blocked"):
        llm.generate("question", [], provider="openai")
    assert sent == []
