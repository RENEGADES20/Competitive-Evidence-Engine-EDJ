"""The prompt (v4) carries the citation rules, the standard wording and the answer-shape rules
(plans/0010, plans/0167, plans/0204, plans/0215)."""
import re
from pathlib import Path

import yaml

from cee.answer import prompt
from cee.answer.llm import SYSTEM_PROMPT, anthropic_request, openai_request

WORDING = [prompt.BOUNDARY_HANDOFF, prompt.MERRILL_GAP, prompt.GWIM_DIFFERS, prompt.ATTRITION_GAP,
           prompt.HEADCOUNT_DIFFERS, prompt.PAYOUT_GAP, prompt.PAYOUT_RANGES_PUBLISHED,
           prompt.COMPENSATION_DIFFERS, prompt.TRADE_PRESS_NOTE]


def test_prompt_is_versioned():
    assert prompt.PROMPT_VERSION == "v4"
    assert "Prompt version: v4" in prompt.SYSTEM_PROMPT


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


def _hit(**kw):
    from cee.retrieve.fts import Hit
    base = dict(chunk_id="RJF-PR-web-advisor-select#0", doc_id="RJF-PR-web-advisor-select", entity_id="RJF",
                segment=None, doc_type="press", source_tier=3, published_at="2026-07-12", period_end=None,
                section="Document", page=None, rank=1.0, text="x")
    return Hit(**{**base, **kw})


def test_user_message_dates_undated_pages_by_content_as_of():
    # ADR-007 T-09 (#58): an undated page is not "published" on its download date
    from cee.answer.llm import build_user_message

    msg = build_user_message("q", [_hit(date_basis="retrieved")])
    assert 'source="RJF press, period n/a, page content as of 2026-07-12 (undated web page), Document"' in msg
    assert "published" not in msg


def test_user_message_source_dated_unchanged():
    from cee.answer.llm import build_user_message

    msg = build_user_message("q", [_hit(doc_type="10-K", period_end="2025-12-31", section="Item 1", page=4)])
    assert 'source="RJF 10-K, period 2025-12-31, published 2026-07-12, Item 1, p.4"' in msg


def test_advisor_pay_gap_is_decided_per_firm():
    # #167: RJF publishes headline payout ranges (recruiting pages, #151); the prompt must not tell
    # the model to say "payout grids are not public" for a firm whose evidence shows ranges.
    text = " ".join(prompt.SYSTEM_PROMPT.split())       # ignore line breaks in the prompt
    assert "firm by firm" in text
    assert f'Never write "{prompt.PAYOUT_GAP}" for a firm whose cited evidence shows payout ranges' in text
    assert "page content as of" in text.split("Advisor pay")[1]
    assert "<date>" in prompt.PAYOUT_RANGES_PUBLISHED and "full payout grid is not public" in prompt.PAYOUT_RANGES_PUBLISHED


# --- prompt v3 (#204): answer shape and behavior choice, with no question-specific text ---

def _flat() -> str:
    return " ".join(prompt.SYSTEM_PROMPT.split())


def test_comparison_grid_rule():
    text = _flat()
    assert "answer on one grid" in text
    assert "Use the same dimensions for every firm" in text
    # v4 (#215): dimensions from the question and its parts, not from the evidence
    assert "Fix the dimensions from the question and its parts before reading the evidence" in text
    assert "do not add one only because the evidence offers it" in text
    assert "from what the evidence covers for at least one of the firms" not in text
    assert "An empty cell is only a gap, never a claim: a claim always has chunk_ids." in text
    assert "Every firm gets an entry under every dimension, a claim or a gap" in text
    assert "a dimension never appears for one firm only" in text
    assert '"<Dimension> - <Firm>:"' in text
    assert '"<Firm> - <dimension>: not found in the evidence provided."' in text
    assert "Never fill a cell with an inference" in text


def test_positions_rule():
    text = _flat()
    assert "group the claims by position, not by firm or source" in text
    assert "saying whose statement each claim is" in text
    assert "report both and say that they disagree" in text
    assert "Offer no forecast or synthesis of your own" in text


def test_parts_rule():
    text = _flat()
    assert "Give every claim, adjacent item and gap the part_id of the part it answers" in text
    assert "Every part gets at least one cited claim, or a gap that names what is missing for that part" in text
    assert "a part with no passages under it is a gap" in text
    assert "what a question of its type needs" in text
    assert "the home firm's figures on the same dimension, from its own filings" in text


def test_disclosure_question_behavior_rule():
    text = _flat()
    part = text.split("Partial or missing disclosure:")[1].split("Standard gap wording")[0]
    assert "A question about what firms disclose on a topic is answered by the disclosures" in part
    assert 'choose "gap_with_adjacent", with the disclosures as claims' in part


def test_recency_example_reworded():
    # v3's example shared a 6-word run with a bank question's text (#215 review).
    assert "since the start of the year" not in _flat()
    assert "Questions about recent change (what is new, what changed since a given date): newest first." in _flat()


def test_behavior_choice_rule():
    text = _flat()
    part = text.split("Partial or missing disclosure:")[1].split("Standard gap wording")[0]
    assert 'not disclosed for most of the firms asked about, choose "gap_with_adjacent"' in part
    assert "Report what is disclosed as claims" in part
    assert 'covers part of the asked population, cohort or period' in part and 'choose "answer"' in part
    assert "source, sample and date" in part
    assert "is not partial evidence: it stays adjacent" in part   # a wider unit (GWIM) is not partial


def test_published_ranges_gap_names_the_firm():
    assert 'name the firm first, e.g. "Raymond James: Headline payout ranges' in _flat()


def test_ground_rules_held_in_v3():
    text = prompt.SYSTEM_PROMPT
    assert f'"{prompt.BOUNDARY_HANDOFF}"' in text
    assert "Never recommend, suggest or evaluate an action for any firm." in text
    assert "Never cite a chunk_id that is not in the evidence." in text


def test_anthropic_output_cap_fits_grid_answers():
    assert anthropic_request("q", [])["max_tokens"] == 8000


# Leak check: the prompt must not carry the question bank or its scoring rubric.
_TOKENS = re.compile(r"[a-z0-9']+")
_BANK = Path(__file__).resolve().parents[1] / "evals" / "questions.yaml"


def _grams(s: str, n: int = 6) -> set[tuple[str, ...]]:
    t = _TOKENS.findall(s.lower())
    return {tuple(t[i:i + n]) for i in range(len(t) - n + 1)}


def _passes_if() -> dict[str, str]:
    data = yaml.safe_load(_BANK.read_text(encoding="utf-8"))
    qs = data["questions"] if isinstance(data, dict) else data
    return {q["id"]: str(q.get("passes_if") or "") for q in qs}


def _leaks(text: str) -> dict[str, set]:
    mine = _grams(text)
    return {qid: hit for qid, p in _passes_if().items() if (hit := mine & _grams(p))}


def _question_texts() -> dict[str, str]:
    data = yaml.safe_load(_BANK.read_text(encoding="utf-8"))
    qs = data["questions"] if isinstance(data, dict) else data
    return {q["id"]: str(q.get("text") or "") for q in qs}


def test_prompt_shares_no_run_with_question_text():
    """The whole prompt, no exception (#215; the planner prompt has the same check, #224)."""
    mine = _grams(prompt.SYSTEM_PROMPT)
    hits = {qid: h for qid, t in _question_texts().items() if (h := mine & _grams(t))}
    assert hits == {}


def test_prompt_names_no_question_id():
    assert not re.search(r"Q\d{1,2}", prompt.SYSTEM_PROMPT)


def test_prompt_has_no_passes_if_text():
    # The standard wording (specs/answer-citations.md) is quoted by Q28 and Q30 on purpose: the
    # bank asks for those exact sentences. Everything else in the prompt must not match a rubric.
    text = prompt.SYSTEM_PROMPT
    for sentence in WORDING:
        text = text.replace(sentence, " ")
    assert _leaks(text) == {}
    assert set(_leaks(prompt.SYSTEM_PROMPT)) <= {"Q28", "Q30"}


def test_leak_check_catches_a_copied_rubric():
    # The rule-3 wording of the first #204 plan draft (6976a04) restated Q3's rubric; the check
    # (lower case, punctuation stripped) must catch it.
    old = ("a strategy question also covers how the firm frames the business, its stated priorities "
           "and the competitive pressure management acknowledges, including where it concedes ground")
    assert "Q3" in _leaks(old)
