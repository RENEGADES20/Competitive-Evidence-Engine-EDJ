"""URL checker for docs/source_matrix.csv. Offline: a fake fetcher answers, real network calls fail."""
import http.client
import socket
import urllib.request

import pytest

from cee.ingest import check_sources as cs
from cee.ingest.check_sources import Checker, NetError, Response, classify


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("a test tried to use the real network")
    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


class FakeWeb:
    """answers[(method, url)] = Response | NetError; records every request and user agent."""

    def __init__(self, answers):
        self.answers, self.calls, self.now, self.slept = answers, [], 0.0, []

    def fetch(self, url, method, ua):
        self.calls.append((method, url, ua))
        self.now += 0.1
        a = self.answers.get((method, url), self.answers.get(("*", url)))
        if isinstance(a, NetError):
            raise a
        return a

    def sleep(self, s):
        self.slept.append(s)
        self.now += s

    def checker(self, edgar_identity=""):
        return Checker(fetch=self.fetch, sleep=self.sleep, clock=lambda: self.now,
                       edgar_identity=edgar_identity)


U = "https://ir.example.com/news/releases"


def ok(url=U, body=b""):
    return Response(200, url, body)


@pytest.mark.parametrize("resp, status", [
    (Response(200, U), "ok"),
    (Response(200, "https://www.example.com/news/2026/item"), "ok"),       # same site, deeper page
    (Response(404, U), "dead"),
    (Response(410, U), "dead"),
    (Response(503, U), "error"),                                            # a bad day, not dead
    (Response(429, U), "error"),
    (Response(403, U), "blocked"),
    (Response(503, U, b"<title>Just a moment...</title> cf-chl"), "blocked"),
    (Response(200, "https://ir.example.com/"), "moved"),                   # front page
    (Response(200, "https://other.org/news/releases"), "moved"),           # another site
    (Response(200, "https://ir.example.com/login?next=/news"), "moved"),   # login page
])
def test_status_rules(resp, status):
    assert classify(U, resp, None).status == status


def test_network_failures():
    assert classify(U, None, NetError("dns", "x")).status == "dead"
    assert classify(U, None, NetError("timeout", "x")).status == "error"
    assert classify(U, None, NetError("ssl", "x")).net_failure


def test_paywall_403_is_expected_not_dead():
    r = classify(U, Response(403, U), None, access="paywall")
    assert r.status == "blocked" and "expected" in r.note


def test_one_get_per_url_and_a_200_challenge_page_is_blocked():
    web = FakeWeb({("GET", U): ok(body=b"<script src='/_Incapsula_Resource?x=1'></script>")})
    assert web.checker().check(U).status == "blocked"
    assert [c[0] for c in web.calls] == ["GET"]


def test_error_is_retried_once():
    web = FakeWeb({("*", U): Response(503, U)})
    assert web.checker().check(U).status == "error"
    assert len(web.calls) == 2                       # GET, wait, GET
    assert cs.RETRY_WAIT in web.slept


def test_temporary_dns_failure_is_an_error_not_dead():
    temp = cs._net_error(socket.gaierror(socket.EAI_AGAIN, "Temporary failure in name resolution"))
    gone = cs._net_error(socket.gaierror(socket.EAI_NONAME, "Name or service not known"))
    assert classify(U, None, temp).status == "error" and classify(U, None, temp).net_failure
    assert classify(U, None, gone).status == "dead"


@pytest.mark.parametrize("exc, kind", [
    (http.client.InvalidURL("URL can't contain control characters"), "bad-url"),
    (UnicodeEncodeError("ascii", "caf\u00e9", 3, 4, "x"), "bad-url"),
    (http.client.BadStatusLine("garbage"), "conn"),
])
def test_odd_urls_and_answers_become_results(monkeypatch, exc, kind):
    def raise_it(*a, **k):
        raise exc
    monkeypatch.setattr(urllib.request, "urlopen", raise_it)
    with pytest.raises(NetError) as e:
        cs.fetch(U, "GET", "ua")
    assert e.value.kind == kind


def test_site_that_never_answers_is_not_asked_again():
    urls = [f"https://ir.example.com/{n}" for n in range(3)]
    web = FakeWeb({("*", u): NetError("timeout", "timed out") for u in urls})
    checker = web.checker()
    results = [checker.check(u) for u in urls]
    assert [r.status for r in results] == ["error", "error", "error"]
    assert results[2].reason == "not-tried" and results[2].net_failure   # counts toward "offline"
    assert not any(c[1] == urls[2] for c in web.calls)


def test_each_url_once_and_polite_per_host():
    other = "https://ir.example.com/events"
    web = FakeWeb({("GET", U): ok(), ("GET", other): ok(other)})
    rows = [{"source_id": "A", "url": U, "sample_url": U},
            {"source_id": "B", "url": U, "sample_url": other}]
    results = cs.check_rows(rows, web.checker())
    assert len(results) == 4 and len(web.calls) == 2
    assert web.slept and min(web.slept) > 0          # second request to the same host waited


def test_sec_gov_uses_edgar_identity_or_is_skipped(capsys):
    sec = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=815917"
    web = FakeWeb({("GET", sec): ok(sec)})
    assert web.checker().check(sec).status == "skipped"
    assert web.calls == []
    assert web.checker("Jane Doe jane@example.edu").check(sec).status == "ok"
    assert web.calls[0][2] == "Jane Doe jane@example.edu"
    assert "jane@example.edu" not in capsys.readouterr().out


FIELDS = ["source_id", "entity_id", "access", "url", "sample_url", "notes",
          "last_checked", "url_status", "sample_status", "extra"]


def write_csv(path, rows):
    cs.write_matrix(FIELDS, [{k: r.get(k, "") for k in FIELDS} for r in rows], path)


def test_unchanged_file_round_trips_byte_for_byte(tmp_path):
    p = tmp_path / "m.csv"
    write_csv(p, [{"source_id": "A", "url": U, "notes": 'Barron’s, "quoted", comma'}])
    before = p.read_bytes()
    fields, rows = cs.read_matrix(p)
    cs.write_matrix(fields, rows, p)
    assert p.read_bytes() == before and b"\r\n" not in before


def test_bom_from_excel_is_tolerated(tmp_path):
    p = tmp_path / "m.csv"
    write_csv(p, [{"source_id": "A", "url": U}])
    p.write_bytes(b"\xef\xbb\xbf" + p.read_bytes())
    assert cs.read_matrix(p)[1][0]["source_id"] == "A"


def test_csv_saved_by_excel_as_cp1252_is_refused_cleanly(tmp_path):
    p = tmp_path / "m.csv"
    write_csv(p, [{"source_id": "A", "url": U, "notes": "Barron\u2019s"}])
    p.write_bytes(p.read_text(encoding="utf-8").encode("cp1252"))
    assert cs.main(["--csv", str(p)]) == 2


def test_row_with_wrong_field_count_is_refused_before_any_request(tmp_path):
    p = tmp_path / "m.csv"
    write_csv(p, [{"source_id": "A", "url": U}])
    p.write_text(p.read_text(encoding="utf-8") + "B,MS,free,https://x.example.com/,,a,b,,,,,extra\n", encoding="utf-8")
    assert cs.main(["--csv", str(p)]) == 2


def test_duplicate_source_id_is_refused(tmp_path):
    p = tmp_path / "m.csv"
    write_csv(p, [{"source_id": "A", "url": U}, {"source_id": "A", "url": U}])
    assert cs.main(["--csv", str(p)]) == 2


def run_main(monkeypatch, tmp_path, rows, answers, update=True):
    p = tmp_path / "m.csv"
    write_csv(p, rows)
    web = FakeWeb(answers)
    monkeypatch.setattr(cs, "Checker", lambda **k: web.checker())
    code = cs.main(["--csv", str(p)] + (["--update"] if update else []))
    return code, p


def test_update_writes_only_status_columns(monkeypatch, tmp_path):
    rows = [{"source_id": "A", "entity_id": "MS", "url": U, "notes": "keep", "extra": "x"},
            {"source_id": "B", "entity_id": "RJF", "url": U + "/old"}]
    code, p = run_main(monkeypatch, tmp_path, rows,
                       {("GET", U): ok(), ("*", U + "/old"): Response(404, U + "/old")})
    assert code == 1                                  # one dead URL
    fields, out = cs.read_matrix(p)
    assert fields == FIELDS and [r["source_id"] for r in out] == ["A", "B"]
    assert out[0]["url_status"] == "ok 200" and out[0]["notes"] == "keep" and out[0]["extra"] == "x"
    assert out[1]["url_status"] == "dead 404" and out[1]["last_checked"]
    assert out[0]["sample_status"] == ""              # no sample_url, nothing checked


def test_offline_with_many_urls_on_one_site_still_stops(monkeypatch, tmp_path):
    rows = [{"source_id": f"R{n}", "url": f"https://www.example.com/{n}"} for n in range(6)]
    answers = {("*", r["url"]): NetError("timeout", "timed out") for r in rows}
    p = tmp_path / "m.csv"
    write_csv(p, rows)
    before = p.read_bytes()
    code, _ = run_main(monkeypatch, tmp_path, rows, answers)
    assert code == 2 and p.read_bytes() == before


def test_offline_stops_and_writes_nothing(monkeypatch, tmp_path):
    rows = [{"source_id": c, "url": f"https://{c.lower()}.example.com/"} for c in "ABCD"]
    answers = {("*", r["url"]): NetError("dns", "no such domain") for r in rows}
    p = tmp_path / "m.csv"
    write_csv(p, rows)
    before = p.read_bytes()
    code, _ = run_main(monkeypatch, tmp_path, rows, answers)
    assert code == 2 and p.read_bytes() == before
