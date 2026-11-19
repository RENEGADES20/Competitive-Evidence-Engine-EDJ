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


# --- token budget (#213, ADR-019) ------------------------------------------------------------

def thit(cid, rank, n_chars, entity="MS", doc_type="10-Q", tier=2):
    """A hit of exactly n_chars characters of words found in no other hit (no near-duplicates)."""
    words = " ".join(f"{cid.lower()}w{j}" for j in range(n_chars))
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type=doc_type,
               source_tier=tier, published_at="2026-01-01", period_end=None, section=None, page=None,
               rank=rank, text=words[:n_chars])


def tokens_of(hits):
    return sum(fts.hit_tokens(h) for h in hits)


def test_committed_values_are_the_grid_pick():
    assert (fts.POOL_PER_GROUP, fts.TOKEN_BUDGET) == (30, 40000)              # #213 grid, ADR-019
    assert fts.budget_tokens(Query("x", entities=["MS"])) == 40000
    assert fts.budget_tokens(Query("x", entities=FIVE)) == 60000


def test_without_a_token_budget_the_passage_rule_is_unchanged(monkeypatch):
    monkeypatch.setattr(fts, "TOKEN_BUDGET", None)
    assert fts.budget_tokens(Query("x", entities=FIVE)) is None
    pool = five_firm_pool()
    assert select(pool, k=20, firm_of=quota_firms(FIVE)) == select(pool, k=20, firm_of=quota_firms(FIVE),
                                                                   tokens=None)


def test_budget_tokens_grow_per_firm_like_the_passage_rule(monkeypatch):
    monkeypatch.setattr(fts, "TOKEN_BUDGET", 20000)
    assert fts.budget_tokens(Query("x")) == 20000                              # theme: no firm
    assert fts.budget_tokens(Query("x", entities=["MS"])) == 20000
    assert fts.budget_tokens(Query("x", entities=["MER"])) == 20000            # Merrill is one firm
    assert fts.budget_tokens(Query("x", entities=["MS", "MER"])) == 20000
    assert fts.budget_tokens(Query("x", entities=["MS", "MER", "RJF"])) == 20000
    assert fts.budget_tokens(Query("x", entities=FIVE)) == 30000               # exactly 1.5 x B
    assert fts.budget_tokens(Query("x", entities=["MS"], unmapped=["LPLA"])) == 20000
    q = resolve("Net new assets by quarter for each of the five, with each firm's own definition.")
    assert fts.budget_tokens(q) == 30000 and fts.budget_tokens(apply_filters(q, firms=["MS", "SCHW"])) == 20000
    for b in (30000, 40000):
        monkeypatch.setattr(fts, "TOKEN_BUDGET", b)
        assert fts.budget_tokens(Query("x", entities=FIVE)) == b * 3 // 2


def test_hit_tokens_are_characters_over_four():
    assert fts.hit_tokens(thit("A#1", 1.0, 10)) == 2.5


def test_token_mode_fills_to_the_budget_at_most_one_chunk_over():
    pool = [thit(f"MS-D{i}#1", 10 - i * 0.01, 400 + 40 * i, doc_type=t)
            for i, t in enumerate(["10-Q", "10-K", "transcript"] * 6)]
    for budget in (500, 1000, 1700):
        kept = select(pool, k=1, tokens=budget)                  # k does not cap a token budget
        assert tokens_of(kept) >= budget
        assert tokens_of(kept[:-1]) < budget                     # the last chunk made it full
        assert tokens_of(kept) <= budget + max(fts.hit_tokens(h) for h in kept)


def test_token_mode_stops_short_when_the_pool_runs_out():
    pool = [thit(f"MS-D{i}#1", 10 - i, 400) for i in range(3)]
    kept = select(pool, k=20, tokens=10_000)
    assert len(kept) == 3 and tokens_of(kept) == 300


def test_answer_turn_is_not_attached_once_the_budget_is_full(monkeypatch):
    monkeypatch.setattr(fts, "PAIR_TURNS", "attach")
    question = thit("MS-TR-1#5", 10.0, 400, doc_type="transcript")
    answer = thit("MS-TR-1#6", 1.0, 800, doc_type="transcript")
    pool = [question, thit("MS-10Q-1#1", 9.0, 400)]
    left: list[str] = []
    kept = select(pool, k=20, tokens=100, answers={question.chunk_id: answer}, unattached=left)
    assert [h.chunk_id for h in kept] == ["MS-TR-1#5"] and left == ["MS-TR-1#5"]
    left = []
    kept = select(pool, k=20, tokens=150, answers={question.chunk_id: answer}, unattached=left)
    assert [h.chunk_id for h in kept] == ["MS-TR-1#5", "MS-TR-1#6"] and left == []
    assert tokens_of(kept) <= 150 + max(fts.hit_tokens(h) for h in kept)


def trade_pool(trade_chars):
    """Three 10-Q documents with two chunks each (100 tokens per chunk) and one trade article that
    waits for them (TIER_LAST = 0)."""
    pool = [thit(f"MS-10Q-{d}#{c}", 10 - d * 0.1 - c * 0.01, 400) for d in range(3) for c in (1, 2)]
    pool.append(thit("MS-TRADE-1#1", 9.0, trade_chars, doc_type="trade", tier=4))
    return sorted(pool, key=lambda h: (-h.rank, h.chunk_id))


def test_trade_keep_in_token_mode_never_makes_the_list_longer():
    assert fts.TIER_LAST == 0 and fts.TRADE_KEEP
    long_trade = select(trade_pool(800), k=20, tokens=500)
    assert "MS-TRADE-1#1" not in {h.chunk_id for h in long_trade} and tokens_of(long_trade) == 500
    short_trade = select(trade_pool(200), k=20, tokens=500)
    assert "MS-TRADE-1#1" in {h.chunk_id for h in short_trade} and tokens_of(short_trade) == 450
    # passage mode: the swap ignores length, as before (#198)
    assert "MS-TRADE-1#1" in {h.chunk_id for h in select(trade_pool(800), k=5)}


def test_explicit_k_keeps_the_passage_rule(monkeypatch):
    monkeypatch.setattr(fts, "TOKEN_BUDGET", 10)                 # would stop after one chunk
    pool = five_firm_pool()
    assert len(select(pool, k=20, firm_of=quota_firms(FIVE))) == 20

