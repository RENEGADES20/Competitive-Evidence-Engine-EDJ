"""Check that every URL in docs/source_matrix.csv still resolves (feed rot, specs/transcripts-ir.md).

Owner: C2 (Mingmin Kong). Run by hand once a month; no schedule, no alerts (docs/BRIEF.md).
Usage: python -m cee.ingest.check_sources            # report only
       python -m cee.ingest.check_sources --update   # also write last_checked / url_status / sample_status
Exit codes: 0 no dead URL, 1 at least one dead URL, 2 bad CSV or looks offline (nothing written).

One GET per unique URL (only the first MAX_BYTES are read, so a bot-challenge page that
answers 200 is still recognised), at least HOST_DELAY seconds between requests to the same
host. Only 404, 410 and a domain that does not exist count as dead; a site that refuses scripts is "blocked" and is
checked by hand in a browser (manual_check_on in the CSV). A site that gives no answer at all
to two URLs in a row is not asked again in that run.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import http.client
import os
import socket
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from cee.config import REPO_ROOT, settings

MATRIX_PATH = REPO_ROOT / "docs" / "source_matrix.csv"
URL_COLUMNS = {"url": "url_status", "sample_url": "sample_status"}  # checked column -> status column
REQUIRED = ["source_id", "access", "url", "sample_url", "last_checked", "url_status", "sample_status"]

USER_AGENT = ("cee-source-check/0.1 (WashU student prototype; "
              "+https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ)")
TIMEOUT = 15        # seconds per request
HOST_DELAY = 1.0    # seconds between requests to the same host
RETRY_WAIT = 2.0    # seconds before the single retry of an "error" result
HOST_GIVE_UP = 2    # after this many URLs in a row with no answer, skip the rest of that site
MAX_BYTES = 64 * 1024
PAYWALLED = {"paywall", "metered", "licensed", "library"}
SHARED_HOSTING = ("cloudfront.net", "amazonaws.com", "azureedge.net", "akamaized.net")
DNS_NOT_FOUND = {socket.EAI_NONAME, getattr(socket, "EAI_NODATA", None), 11001, 11004} - {None}
LOGIN_MARKERS = ("login", "signin", "sign-in", "subscribe", "register")
CHALLENGE_MARKERS = ("cf-chl", "challenge-platform", "just a moment...", "_incapsula_resource",
                     "px-captcha", "captcha-delivery")


class MatrixError(Exception):
    pass


class NetError(Exception):
    """The request never got an HTTP answer. kind: dns | dns-temp | conn | timeout | ssl | bad-url."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass
class Response:
    code: int
    final_url: str
    body: bytes = b""


@dataclass
class Result:
    status: str              # ok | moved | blocked | error | dead | skipped
    reason: str              # HTTP code or failure kind, e.g. "200", "404", "dns", "timeout"
    final_url: str = ""
    note: str = ""
    net_failure: bool = False

    def text(self) -> str:
        """What goes into the CSV status column."""
        s = f"{self.status} {self.reason}".strip()
        if self.note:
            s += f" ({self.note})"
        if self.status == "moved":
            s += f" -> {self.final_url}"
        return s


def _ssl_context() -> ssl.SSLContext:
    try:  # certifi ships with requests; some Python builds have no system CA bundle
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url: str, method: str, user_agent: str) -> Response:
    """One real HTTP request (redirects followed). Raises NetError when there is no HTTP answer."""
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_context()) as r:
            return Response(r.status, r.geturl(), r.read(MAX_BYTES) if method == "GET" else b"")
    except urllib.error.HTTPError as e:
        try:
            body = e.read(MAX_BYTES) if method == "GET" else b""
        except Exception:
            body = b""
        return Response(e.code, e.geturl() or url, body)
    except urllib.error.URLError as e:
        raise _net_error(e.reason) from e
    except (TimeoutError, ConnectionError, OSError) as e:
        raise _net_error(e) from e
    except (http.client.InvalidURL, ValueError) as e:   # spaces or non-ASCII in the URL
        raise NetError("bad-url", f"cannot request this URL: {type(e).__name__}") from e
    except http.client.HTTPException as e:              # malformed answer, dropped body
        raise NetError("conn", f"bad response: {type(e).__name__}") from e


def _net_error(reason) -> NetError:
    if isinstance(reason, socket.gaierror):
        if reason.errno in DNS_NOT_FOUND:
            return NetError("dns", "no such domain")
        return NetError("dns-temp", "name lookup failed")
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return NetError("timeout", "timed out")
    if isinstance(reason, ssl.SSLError):
        return NetError("ssl", "SSL error")
    return NetError("conn", f"connection failed: {type(reason).__name__}")


def _site(host: str | None) -> str:
    """Registered domain, e.g. investors.example.com -> example.com (full host on shared hosting)."""
    host = (host or "").lower()
    return host if host.endswith(SHARED_HOSTING) else ".".join(host.split(".")[-2:])


def _moved(url: str, final_url: str) -> bool:
    a, b = urlsplit(url), urlsplit(final_url)
    if _site(a.hostname) != _site(b.hostname):
        return True                                          # another site
    if a.path.strip("/") and not b.path.strip("/"):
        return True                                          # dropped on the front page
    login = lambda p: any(m in p.lower() for m in LOGIN_MARKERS)
    return login(b.path) and not login(a.path)               # dropped on a login page


def classify(url: str, resp: Response | None, err: NetError | None, access: str = "") -> Result:
    """Turn one HTTP answer (or the lack of one) into a status. Pure function, no network."""
    if err is not None:
        if err.kind == "dns":
            return Result("dead", "dns", note="no such domain", net_failure=True)
        if err.kind == "bad-url":
            return Result("error", "bad-url", note=str(err))
        return Result("error", err.kind, net_failure=True)
    code, body = resp.code, resp.body.lower()
    challenge = any(m.encode() in body for m in CHALLENGE_MARKERS)
    if 200 <= code < 300:
        if challenge:
            return Result("blocked", str(code), resp.final_url, "bot challenge")
        if _moved(url, resp.final_url):
            return Result("moved", str(code), resp.final_url)
        return Result("ok", str(code), resp.final_url)
    if code in (404, 410):
        return Result("dead", str(code), resp.final_url)
    if code in (401, 403) or (code == 503 and challenge):
        note = "expected: " + access.lower() if access.lower() in PAYWALLED else ""
        return Result("blocked", str(code), resp.final_url, note or ("bot challenge" if challenge else ""))
    if code == 429:
        return Result("error", "429", resp.final_url, "rate limited")
    return Result("error", str(code), resp.final_url)


class Checker:
    def __init__(self, fetch: Callable[[str, str, str], Response] = fetch,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic,
                 edgar_identity: str = ""):
        self.fetch, self.sleep, self.clock = fetch, sleep, clock
        self.edgar_identity = edgar_identity
        self.last_request: dict[str, float] = {}
        self.silent_hosts: dict[str, int] = {}   # host -> URLs in a row that got no HTTP answer

    def _request(self, url: str, method: str, ua: str) -> tuple[Response | None, NetError | None]:
        host = urlsplit(url).hostname or ""
        if host in self.last_request:
            wait = HOST_DELAY - (self.clock() - self.last_request[host])
            if wait > 0:
                self.sleep(wait)
        try:
            return self.fetch(url, method, ua), None
        except NetError as e:
            return None, e
        finally:
            self.last_request[host] = self.clock()

    def _attempt(self, url: str, ua: str, access: str) -> Result:
        resp, err = self._request(url, "GET", ua)   # GET, not HEAD: the body shows bot challenges
        return classify(url, resp, err, access)

    def check(self, url: str, access: str = "") -> Result:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return Result("error", "bad-url", note="not an http(s) URL")
        host = parts.hostname
        if self.silent_hosts.get(host, 0) >= HOST_GIVE_UP:
            return Result("error", "not-tried", note="site gave no answer to earlier URLs",
                          net_failure=True)
        ua = USER_AGENT
        if host == "sec.gov" or host.endswith(".sec.gov"):
            if not self.edgar_identity:
                return Result("skipped", "", note="sec.gov needs EDGAR_IDENTITY in .env")
            ua = self.edgar_identity                       # SEC asks for a name and email
        result = self._attempt(url, ua, access)
        if result.status == "error" and result.reason != "bad-url":
            self.sleep(RETRY_WAIT)
            result = self._attempt(url, ua, access)
        no_answer = result.status == "error" and result.net_failure
        self.silent_hosts[host] = self.silent_hosts.get(host, 0) + 1 if no_answer else 0
        return result


def read_matrix(path: Path = MATRIX_PATH) -> tuple[list[str], list[dict]]:
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:   # -sig: survives a BOM added by Excel
            reader = csv.DictReader(f)
            fields, rows = list(reader.fieldnames or []), []
            for r in reader:
                if None in r or None in r.values():
                    raise MatrixError(f"{path.name} line {reader.line_num} ({r.get('source_id')}): "
                                      "wrong number of fields (an unquoted comma?)")
                rows.append(r)
    except (UnicodeDecodeError, csv.Error) as e:
        raise MatrixError(f"{path.name} is not a valid UTF-8 CSV ({e}); save it as 'CSV UTF-8' "
                          "or edit it in a text editor") from e
    missing = [c for c in REQUIRED if c not in fields]
    if missing:
        raise MatrixError(f"{path.name} is missing columns: {', '.join(missing)}")
    seen, dupes = set(), set()
    for r in rows:
        (dupes if r["source_id"] in seen else seen).add(r["source_id"])
    if dupes:
        raise MatrixError(f"duplicate source_id: {', '.join(sorted(dupes))}")
    return fields, rows


def write_matrix(fields: list[str], rows: list[dict], path: Path = MATRIX_PATH) -> None:
    """Write via a temp file + rename, so a failed run never leaves half a CSV behind."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".source_matrix.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, path)
    except PermissionError as e:
        raise MatrixError(f"cannot write {path.name}; is it open in Excel? ({e})") from e
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def check_rows(rows: list[dict], checker: Checker) -> dict[tuple[str, str], Result]:
    """Result per (source_id, column). Each unique URL is requested once per kind of access."""
    cache: dict[tuple[str, bool], Result] = {}
    results = {}
    for r in rows:
        for col in URL_COLUMNS:
            url = (r.get(col) or "").strip()
            if not url:
                continue
            key = (url, r.get("access", "").lower() in PAYWALLED)   # the "expected: ..." note differs
            if key not in cache:
                cache[key] = checker.check(url, r.get("access", ""))
            results[(r["source_id"], col)] = cache[key]
    return results


def looks_offline(results: dict[tuple[str, str], Result]) -> bool:
    unique = [r for r in {id(r): r for r in results.values()}.values()
              if r.status != "skipped" and r.reason != "bad-url"]
    failed = sum(r.net_failure for r in unique)
    return failed >= max(3, len(unique) // 2 + 1)


def _ascii(s: str) -> str:
    return s.encode("ascii", "replace").decode("ascii")  # safe on any Windows console


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check the URLs in docs/source_matrix.csv.")
    ap.add_argument("--csv", type=Path, default=MATRIX_PATH)
    ap.add_argument("--update", action="store_true", help="write the results back into the CSV")
    args = ap.parse_args(argv)
    try:
        fields, rows = read_matrix(args.csv)
    except (MatrixError, OSError) as e:
        print(f"ERROR: {_ascii(str(e))}")
        return 2

    results = check_rows(rows, Checker(edgar_identity=settings().edgar_identity))
    if looks_offline(results):
        print("Most requests got no answer (DNS / connection / timeout / SSL). Check the internet "
              "connection and try again. Nothing was written.")
        return 2

    counts: dict[str, int] = {}
    for (source_id, col), res in results.items():
        counts[res.status] = counts.get(res.status, 0) + 1
        if res.status != "ok":
            print(_ascii(f"{source_id:34} {col:10} {res.text()}"))
    unique_urls = len({row_url for row_url in (r.get(c, "").strip() for r in rows for c in URL_COLUMNS) if row_url})
    print(_ascii("Checked {} URL cells ({} unique URLs): {}".format(
        len(results), unique_urls, ", ".join(f"{n} {s}" for s, n in sorted(counts.items())))))

    if args.update:
        today = dt.date.today().isoformat()
        for r in rows:
            for col, status_col in URL_COLUMNS.items():
                res = results.get((r["source_id"], col))
                r[status_col] = res.text() if res else ""
            r["last_checked"] = today
        try:
            write_matrix(fields, rows, args.csv)
        except MatrixError as e:
            print(f"ERROR: {_ascii(str(e))}")
            return 2
        print(f"Updated {args.csv.name}.")
    return 1 if counts.get("dead") else 0


if __name__ == "__main__":
    sys.exit(main())
