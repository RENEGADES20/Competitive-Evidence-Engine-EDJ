"""The prompt (v1) carries the citation rules and the standard wording (plans/0010)."""
import re

from cee.answer import prompt
from cee.answer.llm import SYSTEM_PROMPT, anthropic_request, openai_request

WORDING = [prompt.BOUNDARY_HANDOFF, prompt.MERRILL_GAP, prompt.GWIM_DIFFERS, prompt.ATTRITION_GAP,
           prompt.HEADCOUNT_DIFFERS, prompt.PAYOUT_GAP, prompt.COMPENSATION_DIFFERS,
           prompt.TRADE_PRESS_NOTE]


def test_prompt_is_versioned():
    assert prompt.PROMPT_VERSION == "v1"
    assert "Prompt version: v1" in prompt.SYSTEM_PROMPT


def test_llm_uses_prompt_module():
    assert SYSTEM_PROMPT is prompt.SYSTEM_PROMPT


def test_prompt_carries_standard_wording():
    for text in WORDING:
        assert text in prompt.SYSTEM_PROMPT


def test_prompt_names_every_behavior():
    for behavior in ("answer", "answer_with_boundary", "gap_with_adjacent", "refuse"):
        assert f'"{behavior}"' in prompt.SYSTEM_PROMPT


def test_prompt_states_citation_rules():
    text = prompt.SYSTEM_PROMPT
    assert "No citation, no claim." in text
    assert "verbatim" in text
    assert "differs_because" in text and "suggested_source" in text


def test_gwim_wording_names_both_parts():
    # Q30: GWIM is wider than Merrill.
    assert "Merrill" in prompt.GWIM_DIFFERS
    assert "Bank of America Private Bank" in prompt.GWIM_DIFFERS


def test_boundary_handoff_is_not_normative():
    # Q12, Q19: the hand-off returns the "should" without recommending anything.
    assert not re.search(r"\b(recommend|we suggest|ought to|consider)\b", prompt.BOUNDARY_HANDOFF, re.I)
    assert "strategy team" in prompt.BOUNDARY_HANDOFF


def test_both_providers_send_the_prompt():
    assert anthropic_request("q", [])["system"].startswith(prompt.SYSTEM_PROMPT)
    assert openai_request("q", [])["messages"][0]["content"].startswith(prompt.SYSTEM_PROMPT)
