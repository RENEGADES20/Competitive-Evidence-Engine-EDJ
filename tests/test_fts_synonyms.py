"""Synonym expansion and the peer set "the five" (#89). No database."""
import pytest

from cee.retrieve.fts import _search_terms, _tsquery_sql, expand_synonyms, resolve

FIVE = ["MS", "SCHW", "EDJ", "MER", "RJF"]


@pytest.mark.parametrize("question", [
    # Q11, Q22 (evals/questions.yaml)
    "How does each of the five define and report advisor headcount -- and what does each "
    "definition include or exclude?",
    "Net new assets by quarter for each of the five, with each firm's own definition of the metric.",
    "What do the five say about recruiting?",
    "Advisor headcount across the five.",
    "Have all five reported net new assets?",
])
def test_peer_phrase_resolves_to_the_five(question):
    q = resolve(question)
    assert q.entities == FIVE
    assert q.mode == ("entity+theme" if q.themes else "entity")   # "recruiting" names a theme (#117)


def test_peer_phrase_merges_with_a_named_firm():
    assert resolve("How does Merrill compare with the five?").entities == FIVE
    assert resolve("Compare Bank of America with the five.").entities == ["MS", "SCHW", "EDJ", "BAC", "MER", "RJF"]


def test_no_peer_phrase_resolves_as_before():
    assert resolve("What is Schwab's strategy for its RIA custody business?").entities == ["SCHW"]
    assert resolve("Five things Raymond James said about recruiting").entities == ["RJF"]


def test_peer_phrase_is_not_a_search_term():
    terms = _search_terms(resolve("Net new assets by quarter for each of the five"))
    assert "five" not in terms.lower()
    assert "Net new assets by quarter" in terms


def test_expansion_runs_key_to_values_only():
    assert expand_synonyms("advisor headcount") == [
        "adviser", "number of financial advisors", "advisor count", "financial advisors (actual)"]
    # "adviser" is a value of "advisor", not a key: nothing comes back the other way
    assert expand_synonyms("adviser") == []


def test_all_caps_key_matches_exact_case_only():
    assert expand_synonyms("What are firms saying about AI?")[:4] == [
        "artificial intelligence", "generative AI", "GenAI", "machine learning"]
    # "ai" inside "said"/"affiliation" never fires `AI`; "affiliation models" fires `affiliation model` (#203)
    assert expand_synonyms("What has Raymond James said about its affiliation models?") == [
        "affiliation model", "affiliation options", "affiliation choice"]
    assert expand_synonyms("what about ai in advice") == []
    assert expand_synonyms("FAs and NNA") == [  # config order; "FA" does not fire inside "FAs"
        "net new assets", "financial advisors", "financial advisers"]


def test_lower_case_key_matches_any_case():
    # a multi-word key is searched as a phrase too, ahead of its values (#203)
    assert expand_synonyms("Net New Assets by quarter") == [
        "net new assets", "NNA", "core net new assets", "net new assets for the period"]


def test_multi_word_key_is_a_phrase_probe():
    # Q22 (#203): "net new assets" as one phrase, not three common words
    sql, params = _tsquery_sql("Net new assets by quarter")
    assert params["syn0"] == "net new assets"
    assert expand_synonyms("advisor") == ["adviser"]          # a one-word key adds no phrase of itself


def test_key_matches_hyphen_and_inflected_last_word():
    # #203: "stock-plan" (Q13) fires `stock plan`; `recruit` fires on "recruiting" (Q7) and "recruit" (Q2)
    assert expand_synonyms("stock-plan participants")[:3] == ["stock plan", "equity compensation", "workplace"]
    assert "payout" in expand_synonyms("approach advisor recruiting and retention")
    assert "payout" in expand_synonyms("positioning itself to recruit advisors")
    assert expand_synonyms("advisors") == ["adviser"]
    assert expand_synonyms("recruitment") == []                 # only s, es, ed, ing
    assert expand_synonyms("FAS") == []                         # all-caps keys: exact case, whole word


def test_new_vocabulary_entries():
    # #203: Q13 conversion, Q17 deployed AI tools, Q20 under-40 wording
    assert expand_synonyms("convert workplace participants") == [
        "channel migration", "originating from", "originating from workplace", "workplace channel"]
    assert {"AI-powered", "AI-enabled"} <= set(expand_synonyms("AI in advice delivery"))
    assert "next generation" in expand_synonyms("clients under 40")


def test_gap_question_q25_keeps_its_plain_key_match():
    # #203 plan review: "compensation structures" (Q25, a gap question) must not fire `compensation
    # structure` -> "payout grid"; the key is in config `synonym_exact`
    q25 = "What has each of the five actually disclosed about advisor compensation structures?"
    assert "payout grid" not in expand_synonyms(q25)


def test_synonym_exact_key_keeps_the_whole_phrase_match(monkeypatch):
    from cee.retrieve import fts
    cfg = dict(fts.entities_config())
    cfg["synonym_exact"] = ["compensation structure"]
    monkeypatch.setattr(fts, "entities_config", lambda: cfg)
    assert "payout grid" not in expand_synonyms("advisor compensation structures")
    assert "payout grid" in expand_synonyms("advisor compensation structure")


def test_multi_word_synonym_is_searched_as_a_phrase():
    sql, params = _tsquery_sql("advisor headcount")
    assert sql["tsquery"].count("phraseto_tsquery('english', %(syn") == 4
    assert params["syn1"] == "number of financial advisors"
    assert "plainto_tsquery('english', %(terms)s)" in sql["tsquery"]  # the question's own words stay OR'ed


def test_no_synonym_leaves_the_words_only():
    sql, params = _tsquery_sql("positioning itself away from wirehouses")
    assert "phraseto_tsquery" not in sql["tsquery"]
    assert params == {}


def test_synonym_only_word_is_searched_through_its_synonyms():
    # Q29: the bare verb "pay" matched a clearing-guarantee note ("pay any net liquidation amount")
    from cee.retrieve.fts import keyword_terms, synonym_only_words
    assert "pay" in synonym_only_words()
    terms, synonyms = keyword_terms(resolve("What does Morgan Stanley pay its financial advisors?"))
    assert "pay" not in terms.split() and "financial advisors" in terms
    assert synonyms[:3] == ["adviser", "compensation", "payout"]   # "advisors" fires `advisor` (#203)


def test_question_without_a_synonym_only_word_keeps_its_terms():
    from cee.retrieve.fts import keyword_terms
    q = resolve("What is Morgan Stanley's strategy to increase their net new assets?")
    assert keyword_terms(q) == (_search_terms(q), expand_synonyms(_search_terms(q)))


def test_inflected_synonym_only_word_is_stripped_too():
    # #203: with the inflected key match, "pays"/"paying" leave the words like "pay" (the stemmer
    # folds them to the same lexeme, searched only through its synonyms)
    from cee.retrieve.fts import keyword_terms
    terms, synonyms = keyword_terms(resolve("How is Morgan Stanley paying its financial advisors?"))
    assert "paying" not in terms.split() and "financial advisors" in terms
    assert "payout" in synonyms
