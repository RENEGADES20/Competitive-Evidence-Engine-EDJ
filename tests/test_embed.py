"""Embeddings (#124): no database and no network. The real-model test runs only when the
model is already in the cache (it never downloads)."""
from pathlib import Path

import pytest

from cee.retrieve import embed


def test_cache_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path / "fe"))
    monkeypatch.setenv("HF_HOME", "kept")
    assert embed.cache_dir() == tmp_path / "fe"
    assert embed.os.environ["HF_HOME"] == "kept"  # an existing HF_HOME is never changed


def test_cache_dir_default_is_inside_the_repo(monkeypatch):
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", "")
    monkeypatch.delenv("HF_HOME", raising=False)
    assert embed.cache_dir() == embed.REPO_ROOT / ".cache" / "fastembed"
    assert embed.os.environ["HF_HOME"] == str(embed.REPO_ROOT / ".cache" / "huggingface")


def test_vector_literal():
    assert embed.vector_literal([0.5, -1, 2.25]) == "[0.5,-1.0,2.25]"


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def executemany(self, sql, params):
        self.conn.updates.append((sql, list(params)))


class FakeConn:
    def __init__(self, rows):
        self.rows, self.sql, self.updates, self.commits = rows, [], [], 0

    def execute(self, sql, *a):
        self.sql.append(sql)
        rows = self.rows

        class R:
            def fetchall(self):
                return rows
        return R()

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


def test_fill_missing_embeds_only_null_rows_in_batches():
    rows = [{"chunk_id": f"D#{i}", "body": f"text {i}"} for i in range(5)]
    conn = FakeConn(rows)
    seen = []

    def fake_embed(texts):
        seen.append(list(texts))
        return [[0.0] * embed.DIM for _ in texts]

    n = embed.fill_missing(conn, batch=2, embed=fake_embed, log=lambda *_: None)
    assert n == 5
    assert "WHERE embedding IS NULL" in conn.sql[0]
    assert [len(b) for b in seen] == [2, 2, 1]
    assert len(conn.updates) == 3 and conn.commits == 4  # after the select + one per batch
    sql, params = conn.updates[0]
    assert sql == embed.UPDATE_ONE and params[0][1] == "D#0"
    assert params[0][0].startswith("[0.0,") and params[0][0].count(",") == embed.DIM - 1


def test_fill_missing_rejects_a_wrong_size():
    conn = FakeConn([{"chunk_id": "D#0", "body": "x"}])
    with pytest.raises(ValueError):
        embed.fill_missing(conn, embed=lambda t: [[0.0] * 10], log=lambda *_: None)


def _model_cached() -> bool:
    return any(Path(embed.cache_dir()).glob("models--*bge-small-en-v1.5*/snapshots/*/model_optimized.onnx"))


@pytest.mark.skipif(not _model_cached(), reason="embedding model not in the cache (never downloaded by tests)")
def test_real_model_query_is_384_and_unit_length():
    v = embed.embed_query("Morgan Stanley net new assets")
    assert len(v) == embed.DIM
    assert abs(sum(x * x for x in v) - 1.0) < 1e-3


def test_load_cached_logs_the_first_error_and_chains_it(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path / "fe"))

    class Broken:
        def __init__(self, model_name, cache_dir, local_files_only=False):
            if local_files_only:
                raise RuntimeError("bad wheel")
            raise OSError("no network")

    with pytest.raises(OSError, match="no network") as e:
        embed.load_cached(Broken, "some/model", "1 MB")
    assert isinstance(e.value.__cause__, RuntimeError)
    err = capsys.readouterr().err
    assert "RuntimeError: bad wheel" in err and "Downloading some/model (1 MB)" in err


def test_load_cached_uses_the_cache_without_downloading(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path / "fe"))
    calls = []

    class Cached:
        def __init__(self, model_name, cache_dir, local_files_only=False):
            calls.append(local_files_only)

    embed.load_cached(Cached, "some/model", "1 MB")
    assert calls == [True] and capsys.readouterr().err == ""
