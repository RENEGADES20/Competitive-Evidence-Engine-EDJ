"""Embeddings (#124, optional module since #144): no database and no network. Runs without the
vectors extra (fastembed is faked); the real-model test runs only when fastembed is installed and
the model is already in the cache (it never downloads)."""
import sys
import types
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
    assert "chunk_embeddings" in conn.sql[0] and "NOT EXISTS" in conn.sql[0]
    assert [len(b) for b in seen] == [2, 2, 1]
    assert len(conn.updates) == 3 and conn.commits == 4  # after the select + one per batch
    sql, params = conn.updates[0]
    assert sql == embed.INSERT_ONE and sql.startswith("INSERT INTO chunk_embeddings")
    assert params[0][0] == "D#0"
    assert params[0][1].startswith("[0.0,") and params[0][1].count(",") == embed.DIM - 1


def test_fill_missing_rejects_a_wrong_size():
    conn = FakeConn([{"chunk_id": "D#0", "body": "x"}])
    with pytest.raises(ValueError):
        embed.fill_missing(conn, embed=lambda t: [[0.0] * 10], log=lambda *_: None)


class FakeTextEmbedding:
    calls = []

    def __init__(self, **kw):
        FakeTextEmbedding.calls.append(kw)


@pytest.fixture
def fake_fastembed(monkeypatch):
    """A stand-in fastembed module: records every TextEmbedding call, never downloads."""
    FakeTextEmbedding.calls = []
    monkeypatch.setitem(sys.modules, "fastembed", types.SimpleNamespace(TextEmbedding=FakeTextEmbedding))
    embed.model.cache_clear()
    yield FakeTextEmbedding.calls
    embed.model.cache_clear()


def _cache_with_model(root: Path) -> Path:
    snap = root / embed.MODEL_FOLDER / "snapshots" / "abc"
    snap.mkdir(parents=True)
    (snap / "model_optimized.onnx").write_bytes(b"")
    return root


def test_empty_cache_raises_clear_error_without_download(monkeypatch, tmp_path, fake_fastembed):
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    with pytest.raises(embed.ModelNotCached) as e:
        embed.model()
    assert "FASTEMBED_CACHE_PATH" in str(e.value) and "--fetch" in str(e.value)
    assert fake_fastembed == []  # fastembed never called: no download attempt


def test_missing_cache_folder_is_not_created(monkeypatch, tmp_path, fake_fastembed, capsys):
    missing = tmp_path / "does-not-exist"
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(missing))
    assert embed.main(["--query", "x"]) == 1
    assert "FASTEMBED_CACHE_PATH" in capsys.readouterr().err
    assert not missing.exists() and fake_fastembed == []


def test_cached_model_loads_local_files_only(monkeypatch, tmp_path, fake_fastembed):
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(_cache_with_model(tmp_path / "fe")))
    embed.model()
    assert len(fake_fastembed) == 1 and fake_fastembed[0]["local_files_only"] is True


def test_fetch_calls_the_downloader(monkeypatch, tmp_path, fake_fastembed):
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path / "fe"))
    assert embed.main(["--fetch"]) == 0
    assert fake_fastembed == [{"model_name": embed.MODEL, "cache_dir": str(tmp_path / "fe")}]
    assert (tmp_path / "fe").is_dir()


def test_missing_refuses_when_vectors_are_off(monkeypatch, capsys):
    monkeypatch.setenv("CEE_VECTORS", "off")
    import cee.db
    monkeypatch.setattr(cee.db, "connect", lambda *a, **k: pytest.fail("must not connect"))
    assert embed.main(["--missing"]) == 2
    assert "CEE_VECTORS" in capsys.readouterr().err


def test_real_model_query_is_384_and_unit_length():
    pytest.importorskip("fastembed")
    if not embed.model_cached():
        pytest.skip("embedding model not in the cache (never downloaded by tests)")
    embed.model.cache_clear()
    v = embed.embed_query("Morgan Stanley net new assets")
    assert len(v) == embed.DIM
    assert abs(sum(x * x for x in v) - 1.0) < 1e-3
