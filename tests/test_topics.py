"""Topic tagging rules (C3, #81; src/cee/ingest/topics.py). Offline: no database."""
import yaml

from cee.config import REPO_ROOT, entities_config
from cee.ingest.topics import load_topics, tag_chunks, tag_text


def test_topics_yaml_matches_the_seed_themes():
    topics = load_topics()
    ids = [t.topic_id for t in topics]
    assert len(ids) == len(set(ids))
    assert all(t.parent in ids for t in topics if t.parent)
    top = {t.topic_id for t in topics if t.parent is None}
    assert top == {t["id"] for t in entities_config()["themes"]}


def test_whole_words_only():
    assert "ai_advice" not in tag_text("The CEO said retail clients remain loyal.")
    assert "ai_advice" in tag_text("Advisors now use AI to draft meeting notes.")


def test_subtopic_needs_its_parent():
    # "trillion" and "estimated" alone are transfer_estimates keywords, but no wealth_transfer word.
    assert tag_text("Assets reached an estimated 5 trillion.") == set()
    tags = tag_text("The great wealth transfer is estimated in the trillions over the next decades.")
    assert {"wealth_transfer", "transfer_estimates"} <= tags


def test_subtopic_brings_its_parent():
    tags = tag_text("Firms rolled out a generative AI copilot available to advisors.")
    assert "ai_advisor_tools" in tags and "ai_advice" in tags


def test_fallback_gives_every_chunk_a_topic_and_is_counted():
    texts = ["Important disclosures. Past performance is no guarantee.",
             "Millennials and Gen Z investors prefer mobile apps.",
             "Younger investors under 40 rely on social media.",
             "AI is changing advice."]
    tags, n_fallback = tag_chunks(texts)
    assert all(tags)
    assert n_fallback == 1
    assert tags[0] == {"younger_investors"}  # the document's most frequent top-level topic


def test_no_match_anywhere_is_left_empty():
    tags, n_fallback = tag_chunks(["Table of contents", "Page 2"])
    assert tags == [set(), set()] and n_fallback == 0


def test_every_keyword_tags_its_own_topic_when_the_parent_is_present():
    raw = yaml.safe_load((REPO_ROOT / "config" / "topics.yaml").read_text(encoding="utf-8"))["topics"]
    first_kw = {t["id"]: t["keywords"][0] for t in raw}
    for t in raw:
        for kw in t["keywords"]:
            text = kw if not t.get("parent") else f"{kw}. {first_kw[t['parent']]}."
            assert t["id"] in tag_text(text), (t["id"], kw)
