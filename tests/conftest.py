"""Test-wide guard (CLAUDE.md "Paid API calls"): tests and CI make 0 real model calls.

A developer's .env may set LLM_PROVIDER=anthropic for planned real runs; every test runs with the
mock provider unless it passes a provider and a fake client itself (#214: the question planner
reads the configured provider in ask())."""
import pytest


@pytest.fixture(autouse=True)
def _mock_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
