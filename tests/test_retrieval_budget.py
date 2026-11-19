"""Retrieval budget (#181, ADR-013): k grows with the number of named firms, and Merrill (MER
documents plus BAC chunks in GWIM) takes one firm's share. No database: select() and budget()
work on fixtures."""
from cee.retrieve import fts
from cee.retrieve.fts import Hit, Query, apply_filters, budget, quota_firms, resolve, select

FIVE = ["MS", "SCHW", "EDJ", "MER", "RJF"]


def hit(cid, rank, entity, doc_type="10-Q", segment=None):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=segment,
               doc_type=doc_type, source_tier=2, published_at="2026-01-01", period_end=None,
               section=None, page=None, rank=rank, text=f"unique words for {cid} " * 5)


def five_firm_pool() -> list[Hit]:
    """Every firm has plenty of strong chunks; Merrill has its own (MER press) and BAC GWIM ones."""
    pool = []
    for firm in ["MS", "SCHW", "EDJ", "RJF"]:
        pool += [hit(f"{firm}-D{i}#1", 10 - i * 0.01, firm) for i in range(10)]
    pool += [hit(f"MER-PR-{i}#1", 10 - i * 0.01, "MER", "press") for i in range(10)]
    pool += [hit(f"BAC-10Q-{i}#1", 10 - i * 0.01, "BAC", "10-Q", "GWIM") for i in range(10)]
    return sorted(pool, key=lambda h: (-h.rank, h.chunk_id))


def test_merrill_counted_once():
    kept = select(five_firm_pool(), k=20, firm_of=quota_firms(FIVE))
    count = {f: sum(h.entity_id == f for h in kept) for f in ["MS", "SCHW", "EDJ", "RJF", "MER", "BAC"]}
    assert count["MS"] == count["SCHW"] == count["EDJ"] == count["RJF"] == 4
    assert count["MER"] + count["BAC"] == 4
    assert count["MER"] and count["BAC"]  # document types still take turns inside Merrill


def test_without_the_merrill_key_merrill_took_two_shares():
    # the freeze behavior (#120): BAC GWIM was its own group, so the other four got fewer slots
    kept = select(five_firm_pool(), k=20)
    assert sum(h.entity_id in ("MER", "BAC") for h in kept) > 4


def test_named_parent_keeps_its_own_quota():
    assert quota_firms(FIVE) == {"BAC": "MER"}
    assert quota_firms(["BAC", "MER"]) == {}
    assert quota_firms(["MS", "RJF"]) == {}


def test_budget_by_firm_count():
    assert budget(Query("x")) == fts.K                                  # theme: no firm
    assert budget(Query("x", entities=["MS"])) == fts.K
    assert budget(Query("x", entities=["MER"])) == fts.K                # Merrill is one firm
    assert budget(Query("x", entities=["MS", "MER"])) == 20
    assert budget(Query("x", entities=["MS", "MER", "RJF"])) == 20
    assert budget(Query("x", entities=FIVE)) == 30
    assert budget(Query("x", entities=["MS"], unmapped=["LPLA", "AMP"])) == fts.K  # no documents, no slots


def test_budget_follows_the_resolved_question_and_the_firm_filter():
    q = resolve("Net new assets by quarter for each of the five, with each firm's own definition.")
    assert q.entities == FIVE and budget(q) == 30
    assert budget(apply_filters(q, firms=["MS", "SCHW"])) == 20


def test_budget_rule_is_swappable(monkeypatch):
    monkeypatch.setattr(fts, "BUDGET_RULE", lambda n: 8 * n)
    assert budget(Query("x", entities=FIVE)) == 40
    assert budget(Query("x", entities=["MS"])) == fts.K  # one firm never changes


def test_single_firm_list_is_unchanged_by_the_merrill_key():
    pool = [hit(f"MS-D{i}#1", 10 - i, "MS", t) for i, t in enumerate(["10-Q", "10-K", "transcript"] * 4)]
    assert select(pool, k=20, firm_of=quota_firms(["MS"])) == select(pool, k=20)
