"""#275: the reduce's streamed claims: incremental parse of the tool JSON (StreamItems), the per-claim checks
before display (check_item, TL condition 2), adjacent items held (TL condition 1), early claims vs the final
answer, the Ask page events, the eval record and the prompt version. Fake clients only: 0 real calls."""
import json

import pytest

from cee import ask as pipeline
from cee.answer import llm
from cee.answer import prompt as P
from cee.answer import reduce as R
from cee.retrieve.fts import Query
from tests.test_deepseek_stages import USAGE, chunk, tc
from tests.test_reduce import H, _one_population, cell, item, matrix, plan_of, q24_shaped  # noqa: F401
from tests.test_stream_idle import Client

ITEMS = {"answerable": True, "behavior": "answer",
         "claims": [{"text": 'Edward Jones: "assets" of $2,647 billion {braces} \\u00e9.', "chunk_ids": ["EDJ-10Q#59"],
                     "part_id": "a2.EDJ"},
                    {"text": "Edward Jones had 20,514 advisors.", "chunk_ids": ["EDJ-10Q#60"], "part_id": "a3.EDJ"}],
         "adjacent": [{"text": "Schwab: 16,000 RIA client firms.", "chunk_ids": ["SCHW-TR#10"], "part_id": "a3.SCHW",
                       "differs_because": "RIA firms, not advisors"}],
         "gaps": [{"what": "x [y] {z}", "suggested_source": "", "part_id": "a1.MS"}]}


def feed_all(text, step):
    p, out = R.StreamItems(), []
    for k in range(0, len(text), step):
        out += p.feed(text[k:k + step])
    return out


@pytest.mark.parametrize("step", [1, 2, 3, 7, 50, 10_000])
def test_deltas_split_anywhere_give_the_whole_items(step):
    text = json.dumps(ITEMS)
    got = feed_all(text, step)
    want = [("claims", c) for c in ITEMS["claims"]] + [("adjacent", a) for a in ITEMS["adjacent"]]
    assert got == want   # gaps are not streamed; escapes, quotes, braces and \u inside text survive


def test_key_order_does_not_matter():
    reordered = {"gaps": ITEMS["gaps"], "adjacent": ITEMS["adjacent"], "behavior": "answer",
                 "claims": ITEMS["claims"], "answerable": True}
    got = feed_all(json.dumps(reordered, indent=2), 5)
    assert [k for k, _ in got] == ["adjacent", "claims", "claims"]


def test_a_cut_stream_returns_only_complete_items():
    text = json.dumps(ITEMS)
    cut = text[:text.index("20,514") + 3]
    got = feed_all(cut, 4)
    assert got == [("claims", ITEMS["claims"][0])]


# --- check_item (TL condition 2) ---------------------------------------------------------------------

def _claim(text, ids, part):
    return {"text": text, "chunk_ids": ids, "part_id": part}


MS_TEXT = "Morgan Stanley: advisor counts are not comparable across firms."
MS = {"text": MS_TEXT, "chunk_ids": ["MS-10K#5"], "part_id": "a4.MS"}   # a clean fact claim (a2 / a3 are proxies)


def test_a_clean_claim_passes():
    m = q24_shaped()
    c = R.check_item(MS, m, None)
    assert c is not None and c.flags == [] and c.source_label


@pytest.mark.parametrize("raw, why", [
    (_claim("Edward Jones should hire more advisors.", ["MS-10K#5"], "a4.MS"), "normative -> withheld"),
    (_claim("Advisor headcount - Edward Jones: not stated.", [], "a3.EDJ"), "uncited cell -> gaps"),
    (_claim(MS_TEXT, ["MS-10K#123"], "a4.MS"), "unmatched id"),
    (_claim(MS_TEXT, ["MS-10K#5", "MS-10K#123"], "a4.MS"), "one unmatched id"),
    (_claim("Morgan Stanley: 99,999 advisor counts are not comparable.", ["MS-10K#5"], "a4.MS"), "figure not in its chunk"),
    (_claim("Schwab: 16,000 RIA client firms.", ["SCHW-TR#10"], "a3.SCHW"), "claim on an adjacent-only cell"),
    (_claim(MS_TEXT, [], "a4.MS"), "no citation"),
    (_claim(P.BOUNDARY_HANDOFF, [], ""), "the hand-off sentence"),
    ({"text": "no chunk_ids key"}, "not a claim"),
])
def test_held_back_paths(raw, why):
    assert R.check_item(raw, q24_shaped(), None) is None, why


def test_outside_matrix_id_is_held_even_when_retrieved():
    m = q24_shaped()
    m.hits["EDJ-10Q#70"] = H("EDJ-10Q#70")   # retrieved, but no matrix item cites it
    assert R.check_item(_claim(MS_TEXT, ["EDJ-10Q#70"], "a4.MS"), m, None) is None


def test_a_wrong_date_is_held():
    m = q24_shaped()
    raw = _claim("For the quarter ended March 2019, Morgan Stanley said advisor counts are not comparable.",
                 ["MS-10K#5"], "a4.MS")
    assert R.check_item(raw, m, None) is None


def test_a_why_line_outside_a_recency_item_is_held():
    m = q24_shaped()
    raw = _claim(MS_TEXT + " Why it might matter: growth.", ["MS-10K#5"], "a4.MS")
    assert R.check_item(raw, m, None) is None   # clean_why_lines would change the text


def test_adjacent_items_are_never_shown_early_even_when_first():
    m, shown = q24_shaped(), []
    early = R.EarlyClaims(m, None, shown.append)
    early("adjacent", ITEMS["adjacent"][0])          # arrives first
    early("claims", MS)
    assert len(shown) == 1 and shown[0].text == MS_TEXT
    assert early.stats() == {"first_claim_s": early.first_claim_s, "shown": 1, "held": 1}
    assert early.first_claim_s is not None


# --- the streamed reduce call -----------------------------------------------------------------------

def _stream_of(args: str, step=11):
    parts = [args[k:k + step] for k in range(0, len(args), step)]
    chunks = [chunk(calls=[tc(0, parts[0], name=R.TOOL, id_="c1")])] + [chunk(calls=[tc(0, p)]) for p in parts[1:]]
    return chunks + [chunk(finish="tool_calls"), chunk(usage=USAGE, choices=False)]


def test_early_claims_are_a_subset_of_the_final_answer(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_EFFORT_REDUCE", "off")
    m = q24_shaped()
    dup = _claim("The comparison is not valid.", ["MS-10K#5"], "a4")
    out = {"answerable": True, "behavior": "answer", "gaps": [],
           "adjacent": [{**ITEMS["adjacent"][0]}],
           "claims": [dup, {**dup}, MS,
                      _claim("Edward Jones should cut fees.", ["EDJ-10Q#60"], "a3.EDJ")]}
    client = Client(iter(_stream_of(json.dumps(out))))
    shown = []
    early = R.EarlyClaims(m, None, shown.append)
    raw = R.call_reduce(m.question, m, None, "deepseek", client=client, on_item=early)
    assert raw == out and client.kwargs["stream"] is True
    assert [c.text for c in shown] == [dup["text"], dup["text"], MS_TEXT]
    final, _ = R.finish_answer(R.to_answer(raw, "deepseek", {"stop_reason": "tool_calls"}), m,
                               Query(question=m.question, entities=["EDJ", "SCHW", "MS"]), plan_of(m),
                               list(m.hits.values()), m.question)
    stats = early.stats(final)
    assert stats["shown"] == 3 and stats["held"] == 2   # the adjacent item and the normative claim
    # every early claim is in the final answer with the same text (the duplicate is removed there once)
    assert all(c.text in {x.text for x in final.claims} for c in shown) and stats["shown_not_final"] == 0


def test_a_cut_stream_shows_complete_claims_then_is_invalid(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_EFFORT_REDUCE", "off")
    m = q24_shaped()
    out = {"answerable": True, "behavior": "answer", "gaps": [], "adjacent": [],
           "claims": [MS, _claim("The comparison is not valid.", ["MS-10K#5"], "a4")]}
    text = json.dumps(out)
    chunks = _stream_of(text[:text.index("The comparison")])[:-2] + [chunk(finish="length")]
    shown = []
    with pytest.raises(llm.ModelOutputError, match="cut at max_tokens"):
        R.call_reduce(m.question, m, None, "deepseek", client=Client(iter(chunks)),
                      on_item=R.EarlyClaims(m, None, shown.append))
    assert [c.text for c in shown] == [MS_TEXT]   # the page then shows the failure


# --- Ask events, the page, the eval record ----------------------------------------------------------

def test_claim_events_come_after_evidence_and_before_the_answer(monkeypatch):
    from tests.test_ask_progress import HITS
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: HITS)
    seen = []
    result = pipeline.ask("Merrill profitability?", provider="mock", log=False,
                          progress=lambda s, st, t: seen.append(("stage", s, st)),
                          on_event=lambda kind, data: seen.append((kind, data)))
    kinds = [e[0] for e in seen if e[0] in ("plan", "evidence", "claim")]
    assert kinds == ["plan", "evidence", "claim"]
    claim_at = next(i for i, e in enumerate(seen) if e[0] == "claim")
    check_at = next(i for i, e in enumerate(seen) if e[:2] == ("stage", "check"))
    assert claim_at < check_at
    data = seen[claim_at][1]
    assert data["n"] == 1 and data["claim"].chunk_ids == ["BAC-10K-2025#244"]
    assert [h.chunk_id for h in data["hits"]] == ["BAC-10K-2025#244"]
    assert result.reduce["stream_items"] == {"first_claim_s": result.reduce["stream_items"]["first_claim_s"],
                                             "shown": 1, "held": 0, "shown_not_final": 0}


def test_the_page_shows_early_claims_then_replaces_them(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from tests.test_ask_page_trace import page
    from tests.test_ask_progress import HITS
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: HITS)
    monkeypatch.setattr(pipeline, "_log", lambda r, p: 1)
    at = AppTest.from_function(page).run()
    assert not at.exception and not at.error
    texts = " ".join(m.value for m in at.markdown)
    assert "CLAIM (CHECKING)" not in texts and "in progress" not in texts   # emptied once the answer is ready


def test_a_stall_shows_an_error_and_retry(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from tests.test_ask_page_trace import page
    from tests.test_ask_progress import HITS
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: HITS)

    def stalled(*a, **k):
        raise llm.StreamIdle("stream idle", {}, False, None, 120.0)
    monkeypatch.setattr(R, "raw_answer", stalled)
    monkeypatch.setattr(pipeline, "_log_attempt", lambda *a, **k: None)   # #277: no row in the local database
    at = AppTest.from_function(page).run()
    assert "no output for 120 s" in at.error[0].value
    assert [b.label for b in at.button] == ["Retry"]   # #277: Retry replaces "Try again"


def test_eval_saves_a_stalled_reduce_as_failed_with_its_partial_output(monkeypatch, tmp_path):
    from scripts import eval_run as er
    from tests.test_eval_run import _good, _reduce_setup
    qd, qry, m, calls = _reduce_setup(monkeypatch, _good)

    def stalled(question, matrix, query, provider, client=None, meta=None, on_item=None):
        raise llm.StreamIdle("stream idle: no chunk for 120 s", {"reasoning_content": "Let"}, True, 1.5, 120.0)
    monkeypatch.setattr(R, "call_reduce", stalled)
    r = er.RealRunner("deepseek", 5, "snap", tmp_path / "r1", cache_dir=tmp_path / "cache")
    a, how, info = r.reduce(qd, qry, plan_of(m), list(m.hits.values()), m)
    assert how == "failed" and a is None and r.made == 1
    rec = json.loads(next((tmp_path / "cache").glob("Q24-reduce-*.json")).read_text(encoding="utf-8"))
    assert rec["failed_call"] and rec["idle_timeout"] and rec["output_seen"] is True
    assert rec["partial"] == {"reasoning_content": "Let"} and rec["ttft_s"] == 1.5
    again = er.RealRunner("deepseek", 5, "snap", tmp_path / "r2", cache_dir=tmp_path / "cache")
    assert again.reduce(qd, qry, plan_of(m), list(m.hits.values()), m)[1] == "failed" and again.made == 0


def test_eval_record_keeps_the_first_claim_time(monkeypatch, tmp_path):
    from scripts import eval_run as er
    from tests.test_eval_run import _good, _reduce_setup
    qd, qry, m, calls = _reduce_setup(monkeypatch, _good)

    def streams(question, matrix, query, provider, client=None, meta=None, on_item=None):
        out = _good(matrix)
        for c in out["claims"]:
            on_item("claims", c)
        meta.update(stop_reason="tool_calls", usage={"output_tokens": 10})
        return out
    monkeypatch.setattr(R, "call_reduce", streams)
    r = er.RealRunner("deepseek", 1, "snap", tmp_path / "r1", cache_dir=tmp_path / "cache")
    a, how, info = r.reduce(qd, qry, plan_of(m), list(m.hits.values()), m)
    rec = json.loads(next((tmp_path / "cache").glob("Q24-reduce-*.json")).read_text(encoding="utf-8"))
    assert how == "called" and rec["first_claim_s"] is not None and rec["stream_items"]["shown"] == 1
    assert info["stream_items"]["shown_not_final"] == 0


# --- prompt version (REDUCE_PROMPT) -----------------------------------------------------------------

def test_prompt_v53_changes_only_the_reduce_key(monkeypatch):
    from scripts import eval_run as er
    m = q24_shaped()
    qd, qry = {"id": "Q24", "text": m.question}, Query(question=m.question, entities=["EDJ", "SCHW", "MS"])

    def key():
        return er.reduce_cache_key(qd, "snap", "deepseek", "m", 64000, "v", m, qry)
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")   # #297: the default is v5.2 again; v5.2 keys unchanged
    v52 = key()
    assert R.prompt_version() == "v5.2" and R.system_prompt() == P.SYSTEM_PROMPT_V5   # #272 keys unchanged
    monkeypatch.setenv("REDUCE_PROMPT", "v5.3")
    assert key() != v52 and R.prompt_version() == "v5.3" and "State each fact once" in R.system_prompt()
    assert P.SYSTEM_PROMPT_V53.replace(P.ONCE_RULE, "").replace("v5.3.", "v5.2.") == P.SYSTEM_PROMPT_V5
    client = Client(iter(_stream_of(json.dumps({"answerable": True, "behavior": "answer", "adjacent": [],
                                                "gaps": [], "claims": [_claim("x", ["MS-10K#5"], "a4")]}))))
    R.call_reduce(m.question, m, None, "deepseek", client=client)
    assert client.kwargs["messages"][0]["content"] == P.SYSTEM_PROMPT_V53
    monkeypatch.setenv("REDUCE_PROMPT", "v99")   # an unknown version (#297: v9 exists)
    with pytest.raises(ValueError, match="REDUCE_PROMPT"):
        R.prompt_version()
