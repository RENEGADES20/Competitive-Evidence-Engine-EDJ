"""Drive the real app like a user and keep the evidence. Works on Windows and macOS.

Used by the verify-cee skill (.claude/skills/verify-cee/SKILL.md). Run with the project venv:

  python scripts/verify_cee.py doctor          # is everything ready to verify?
  python scripts/verify_cee.py run             # launch, drive every feature, clean up
  python scripts/verify_cee.py run ask-answer gap-path
  python scripts/verify_cee.py launch | drive <feature...> | cleanup

It never touches your own database or app: it copies database `cee` to `cee_verify`, starts
its own Streamlit on port 8599 with the mock provider, and removes both at the end.
Evidence (screenshots, page text, steps.jsonl) stays in .verify-runs/<run-id>/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from urllib.parse import quote
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
RUNS = REPO / ".verify-runs"
STATE = RUNS / "instance.json"
CONTAINER = "cee-db"
SOURCE_DB, VERIFY_DB = "cee", "cee_verify"
PORT = 8599
WINDOWS = os.name == "nt"

ANSWERABLE_Q = "What does Edward Jones's 10-K say about its number of financial advisors?"
NO_EVIDENCE_Q = "What does LPL Financial's 10-K say about its number of financial advisors?"
FEATURES = ["ask-answer", "ask-progress", "open-citation", "gap-path", "invalid-chunk", "download-document", "coverage"]


# ---------- helpers ----------

def venv_python() -> Path:
    return REPO / (".venv/Scripts/python.exe" if WINDOWS else ".venv/bin/python")


def sh(args: list[str], check: bool = True, **kw) -> subprocess.CompletedProcess:
    r = subprocess.run(args, capture_output=True, text=True, **kw)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:4])}... failed: {(r.stderr or r.stdout).strip()[:400]}")
    return r


def psql(db: str, sql: str) -> str:
    return sh(["docker", "exec", CONTAINER, "psql", "-qtA", "-U", "cee", "-d", db, "-c", sql]).stdout.strip()


def db_url(db: str) -> str:
    from cee.config import settings
    base = settings().database_url
    return base.rsplit("/", 1)[0] + "/" + db


def health(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/_stcore/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def snapshot_name() -> str:
    # Every laptop has its own database; results are only comparable on the same snapshot.
    return psql(SOURCE_DB, "SELECT obj_description('public.documents'::regclass)") or "none (built locally)"


def git_head() -> str:
    r = sh(["git", "rev-parse", "HEAD"], check=False, cwd=REPO)
    return r.stdout.strip() or "unknown"


def load_state() -> dict | None:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None


def pid_alive(pid: int) -> bool:
    if WINDOWS:
        r = sh(["tasklist", "/FI", f"PID eq {pid}", "/NH"], check=False)
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------- doctor ----------

def doctor(port: int = PORT) -> bool:
    checks: list[tuple[str, bool, str]] = []

    def check(name, fn):
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        checks.append((name, ok, detail))
        print(f"[{'ok' if ok else 'FAIL'}] {name}: {detail}")

    check("python", lambda: (sys.version_info[:2] == (3, 11),
                             f"{sys.version.split()[0]} (need 3.11; run with {venv_python().relative_to(REPO)})"))
    check("docker", lambda: (shutil.which("docker") is not None
                             and sh(["docker", "info"], check=False).returncode == 0,
                             "running" if shutil.which("docker") else "not installed"))
    check("database", lambda: (psql(SOURCE_DB, "SELECT 1") == "1", f"container {CONTAINER}, db {SOURCE_DB}"))
    check("corpus", lambda: (lambda n: (n > 0, f"{n} chunks, snapshot {snapshot_name()} (restore one if 0)"))(
        int(psql(SOURCE_DB, "SELECT count(*) FROM chunks"))))

    def browser():
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            b.close()
        return True, "playwright + chromium ready"
    check("browser", browser)

    def port_free():
        st = load_state()
        if health(port):
            mine = st and st.get("port") == port and pid_alive(st["pid"])
            return bool(mine), "our verify instance is up" if mine else f"port {port} used by another program"
        return True, f"port {port} free"
    check("port", port_free)

    bad = [c for c in checks if not c[1]]
    print("DOCTOR " + ("PASS" if not bad else f"FAIL ({', '.join(c[0] for c in bad)})"))
    return not bad


# ---------- launch / cleanup ----------

def launch(port: int = PORT) -> dict:
    st = load_state()
    if st and pid_alive(st["pid"]) and health(st["port"]):
        print(f"Reusing verify instance on port {st['port']} (run {st['run_id']})")
        return st
    if health(port):
        raise RuntimeError(f"Port {port} is used by a program this script did not start. Stop it or pass --port.")
    RUNS.mkdir(exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + git_head()[:7]
    print(f"Copying database {SOURCE_DB} -> {VERIFY_DB}")
    psql("postgres", f"DROP DATABASE IF EXISTS {VERIFY_DB} WITH (FORCE);")
    psql("postgres", f"CREATE DATABASE {VERIFY_DB};")
    sh(["docker", "exec", CONTAINER, "sh", "-c",
        f"pg_dump -U cee -Fc {SOURCE_DB} | pg_restore -U cee -d {VERIFY_DB} --no-owner"])
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True)
    # MOCK_DELAY_S: the mock waits like a model would, so the progress trace can be seen mid-run (#80).
    env = {**os.environ, "DATABASE_URL": db_url(VERIFY_DB), "LLM_PROVIDER": "mock", "MOCK_DELAY_S": "1.5"}
    log = open(run_dir / "app.log", "w", encoding="utf-8")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if WINDOWS else 0
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(REPO / "src/cee/app/streamlit_app.py"),
         "--server.port", str(port), "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=flags,
        start_new_session=not WINDOWS)
    st = {"pid": proc.pid, "port": port, "run_id": run_id, "head": git_head(), "snapshot": snapshot_name(),
          "started": datetime.now().isoformat(timespec="seconds")}
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")
    for _ in range(60):
        if health(port):
            print(f"App ready at http://localhost:{port} (pid {proc.pid}, run {run_id})")
            return st
        if proc.poll() is not None:
            break
        time.sleep(1)
    cleanup()
    raise RuntimeError(f"App did not start; see {run_dir / 'app.log'}")


def cleanup() -> None:
    st = load_state()
    if st and pid_alive(st["pid"]):
        if WINDOWS:
            sh(["taskkill", "/PID", str(st["pid"]), "/T", "/F"], check=False)
        else:
            try:
                os.killpg(st["pid"], signal.SIGTERM)
            except OSError:
                pass
        print(f"Stopped app pid {st['pid']}")
    STATE.unlink(missing_ok=True)
    try:
        psql("postgres", f"DROP DATABASE IF EXISTS {VERIFY_DB} WITH (FORCE);")
        print(f"Dropped database {VERIFY_DB}")
    except RuntimeError as e:
        print(f"Could not drop {VERIFY_DB}: {e}")
    if st:
        print(f"Evidence kept in {RUNS / st['run_id']}")


# ---------- drive ----------

class Recorder:
    def __init__(self, run_dir: Path, feature: str, page):
        self.dir = run_dir / feature
        self.dir.mkdir(parents=True, exist_ok=True)
        self.feature, self.page, self.steps, self.n = feature, page, [], 0
        self.status = "PASS"

    def step(self, action: str, expected: str, ok: bool, actual: str) -> bool:
        self.n += 1
        shot = self.dir / f"{self.n:02d}.png"
        self.page.screenshot(path=str(shot), full_page=True)
        (self.dir / f"{self.n:02d}.page.txt").write_text(self.page.locator("body").inner_text(), encoding="utf-8")
        row = {"feature": self.feature, "step": self.n, "action": action, "expected": expected,
               "actual": actual, "result": "PASS" if ok else "FAIL", "screenshot": shot.name}
        self.steps.append(row)
        if not ok:
            self.status = "FAIL"
        print(f"  [{row['result']}] {action} -> {actual}")
        return ok

    def unreachable(self, why: str) -> None:
        self.status = "UNREACHABLE"
        self.steps.append({"feature": self.feature, "result": "UNREACHABLE", "actual": why})
        print(f"  [UNREACHABLE] {why}")


RENDER_TIMEOUT_S = 90


class RenderTimeout(RuntimeError):
    pass


def wait_idle(page) -> None:
    page.wait_for_load_state("networkidle")
    page.wait_for_function(
        "() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=60000)
    page.wait_for_timeout(300)


def wait_for_text(page, texts: list[str], what: str) -> None:
    """Wait until the page shows a text only the finished render has (#83). wait_idle alone can
    return before Streamlit starts the rerun (websocket, no status widget yet): old page read."""
    try:
        page.wait_for_function("ts => document.body && ts.some(t => document.body.innerText.includes(t))",
                               arg=texts, timeout=RENDER_TIMEOUT_S * 1000)
    except Exception:  # playwright TimeoutError
        raise RenderTimeout(f"{what} did not render within {RENDER_TIMEOUT_S} s "
                            f"(waited for: {' / '.join(texts)})") from None
    wait_idle(page)


def ask(page, base: str, question: str) -> None:
    page.goto(base)
    wait_idle(page)
    box = page.get_by_role("textbox", name="Question")
    box.wait_for(timeout=RENDER_TIMEOUT_S * 1000)
    box.fill(question)
    page.get_by_role("button", name="Ask").click()
    # Every behavior (answer, boundary, gap, refuse) ends with the meta line "... | LLM called: ...".
    wait_for_text(page, ["LLM called:"], "the answer")


SOURCE_PAGE_DONE = ["Stored passage", "is not in the stored corpus"]


def citation_links(page):
    return page.locator("a[href*='?chunk=']")


def feature_ask_answer(page, base, rec, ctx):
    before = int(psql(VERIFY_DB, "SELECT count(*) FROM query_log"))
    ask(page, base, ANSWERABLE_Q)
    body = page.locator("body").inner_text()
    heading = next((h for h in ("Answer (evidence only", "Answer", "Not in the corpus", "No evidence")
                    if page.get_by_role("heading", name=h).count()), None)
    rec.step("Ask the EDJ advisors question", "an answer heading", heading is not None, f"heading={heading!r}")
    n = citation_links(page).count()
    rec.step("Look at the claims", "at least one citation link", n > 0, f"{n} citation links")
    rec.step("Read the coverage note", "a visible line starting 'Coverage: searched'",
             "Coverage: searched" in body,
             next((l.strip() for l in body.splitlines() if l.strip().startswith("Coverage:")), "no coverage note"))
    rec.step("Read the footer", "mock provider, no LLM call", "LLM called: False" in body,
             "LLM called: False" if "LLM called: False" in body else "footer missing or LLM called")
    after = int(psql(VERIFY_DB, "SELECT count(*) FROM query_log"))
    rec.step("Check the query was logged (side effect)", "query_log +1", after == before + 1,
             f"query_log {before} -> {after}")


def open_trace(page) -> list[str]:
    """Click the collapsed trace open; return its lines."""
    page.get_by_text("How this answer was built", exact=False).first.click()
    page.locator(".cee-trace").first.wait_for(state="visible", timeout=10000)
    # Without the ✓/… marks: they are a visual cue only, and a GBK console cannot print them.
    lines = page.locator(".cee-trace").first.inner_text().splitlines()
    return [l.strip().lstrip("…✓–✗·").strip() for l in lines if l.strip()]


def feature_ask_progress(page, base, rec, ctx):
    page.goto(base)
    wait_idle(page)
    page.get_by_role("textbox", name="Question").fill(ANSWERABLE_Q)
    page.get_by_role("button", name="Ask").click()
    # The verify app's mock waits MOCK_DELAY_S in the model step: the page is caught mid-run.
    page.wait_for_function("() => document.body.innerText.includes('Asking the model')",
                           timeout=RENDER_TIMEOUT_S * 1000)
    body = page.locator("body").inner_text()
    bar = page.locator('[data-testid="stProgress"]').count() > 0
    early = bar and "Reading the question:" in body and "LLM called:" not in body
    rec.step("Ask; look while the answer is being built", "progress bar and step lines, no answer yet",
             early, f"progress bar={bar}, first step shown={'Reading the question:' in body}, "
                    f"answer shown={'LLM called:' in body}")
    wait_for_text(page, ["LLM called:"], "the answer")
    status = page.get_by_text("How this answer was built", exact=False)
    hidden = not page.locator(".cee-trace").first.is_visible()
    rec.step("Look above the answer", "a collapsed 'How this answer was built' box",
             status.count() > 0 and hidden, f"box={status.count() > 0}, trace hidden={hidden}")
    lines = open_trace(page)
    rec.step("Open the trace", "six step lines", len(lines) == 6, " / ".join(lines)[:300])
    body = page.locator("body").inner_text()
    n_meta = re.search(r"(\d+) chunks retrieved", body)
    n_trace = re.search(r"Searching the corpus: (\d+) passage", " ".join(lines))
    same = bool(n_meta and n_trace and n_meta.group(1) == n_trace.group(1))
    rec.step("Compare the search line with the footer", "same passage count", same,
             f"trace {n_trace.group(1) if n_trace else '?'} vs footer {n_meta.group(1) if n_meta else '?'}")
    model = next((l for l in lines if "model" in l), "")
    check = next((l for l in lines if "Checking citations" in l), "")
    rec.step("Read the model and citation lines", "'(mock, one call)' and 'N matched'",
             "(mock, one call)" in model and "matched" in check, f"{model} | {check}")
    ask(page, base, NO_EVIDENCE_Q)
    lines = open_trace(page)
    model = next((l for l in lines if "model" in l), "")
    body = page.locator("body").inner_text()
    rec.step("Ask the no-evidence question, open the trace", "model step skipped, no model call",
             "no model call" in model and "LLM called: False" in body, model)


PDF_PAGE_SAMPLES = ["MS-SUPP-2026Q3#16", "SCHW-DECK-2026Q2#53"]  # a table page and a deck page (#53 comment)


def check_context(rec, page, chunk_id: str) -> None:
    """cite-context: the cited chunk is marked and its same-section neighbours are shown."""
    row = psql(VERIFY_DB, "SELECT doc_id || '|' || seq || '|' || coalesce(section, '') FROM chunks "
                          f"WHERE chunk_id = '{chunk_id}'")
    doc_id, seq, section = row.split("|", 2)
    quoted = "'" + section.replace("'", "''") + "'" if section else "NULL"
    want = int(psql(VERIFY_DB, f"SELECT count(*) FROM chunks WHERE doc_id = '{doc_id}' AND seq <> {seq} "
                               f"AND seq BETWEEN {int(seq) - 2} AND {int(seq) + 2} "
                               f"AND section IS NOT DISTINCT FROM {quoted}"))
    body = page.locator("body").inner_text()
    cited = body.count("CITED PASSAGE")
    neighbours = body.count("NEIGHBOURING PASSAGE")
    rec.step("Check the passage is shown in context (cite-context)",
             f"one CITED PASSAGE tag for {chunk_id} and {want} neighbouring passages from the same section",
             cited == 1 and f"CITED PASSAGE · {chunk_id}" in body and neighbours == want,
             f"{cited} cited, {neighbours} neighbouring (database: {want})")


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


def check_pdf_pages(rec, page) -> None:
    """cite-page: for PDF chunks the page shown is chunks.page, and that page holds the chunk's text."""
    import pymupdf
    from cee.config import FileNotAvailable, resolve_path
    ids = list(PDF_PAGE_SAMPLES)
    others = psql(VERIFY_DB, "SELECT c.chunk_id FROM chunks c JOIN documents d USING (doc_id) "
                             "WHERE c.page IS NOT NULL AND d.doc_type IN ('deck', 'supplement') "
                             "AND length(c.text) > 300 ORDER BY md5(c.chunk_id) LIMIT 6")
    ids += [i for i in others.split() if i not in ids][: 5 - len(ids)]
    checked = 0
    for cid in ids:
        row = psql(VERIFY_DB, "SELECT c.page || '|' || d.storage_path FROM chunks c JOIN documents d USING (doc_id) "
                              f"WHERE c.chunk_id = '{cid}'")
        if not row:
            continue
        n, storage = row.split("|", 1)
        try:
            path = resolve_path(storage)
        except FileNotAvailable:
            rec.unreachable(f"raw PDF for {cid} not available (precondition: CORPUS_SHARE_PATH or data/raw/)")
            return
        page.goto(page.url.split("?")[0] + "?chunk=" + quote(cid))
        wait_for_text(page, ["Download stored document", "not found locally", "is not in the stored corpus"],
                      "the source page")
        body = page.locator("body").inner_text()
        with pymupdf.open(path) as doc:
            total = doc.page_count
            on_page = words(doc[int(n) - 1].get_text("text"))
        chunk_words = words(psql(VERIFY_DB, f"SELECT text FROM chunks WHERE chunk_id = '{cid}'"))
        share = len(chunk_words & on_page) / max(len(chunk_words), 1)
        shown = page.locator('[data-testid="stImage"] img').count()
        ok = f"Page {n} of {total} of the stored PDF" in body and shown == 1 and share >= 0.8
        rec.step(f"Check the PDF page for {cid} (cite-page)",
                 f"page {n} of {total} is shown as an image, and the chunk's words are on that PDF page",
                 ok, f"caption {'ok' if f'Page {n} of {total}' in body else 'missing'}, {shown} page image, "
                     f"{share:.0%} of the chunk's words on page {n}")
        checked += 1
    if not checked:
        rec.unreachable("no PDF chunks with a page number in the corpus")


def feature_open_citation(page, base, rec, ctx):
    ask(page, base, ANSWERABLE_Q)
    link = citation_links(page).first
    if not link.count():
        rec.step("Find a citation", "a citation link", False, "no citation links")
        return
    # Count every chip, linked or not: an unmatched citation is shown unlinked but still labelled.
    n = page.locator(".cee-chip").count()
    labelled = page.locator(".cee-cite .cee-chip").count()
    tiered = page.locator(".cee-cite .cee-tier").count()
    rec.step("Check each citation shows source and tier", "every citation chip has a source label and a tier badge",
             n > 0 and labelled == n == tiered, f"{n} citations, {labelled} with a source label, {tiered} with a tier")
    chunk_id = link.inner_text().strip()
    # Streamlit opens markdown links in a new tab, as a user would see it.
    with page.context.expect_page() as new_tab:
        link.click()
    source = new_tab.value
    wait_for_text(source, SOURCE_PAGE_DONE, "the source page")
    rec.page = source
    body = source.locator("body").inner_text()
    rec.step(f"Click citation {chunk_id}", "a new tab with the source page for that chunk",
             f"Chunk: {chunk_id}" in body and "Stored passage" in body,
             "source page opened" if "Stored passage" in body else body.strip()[:120])
    stored = psql(VERIFY_DB, f"SELECT left(text, 200) FROM chunks WHERE chunk_id = '{chunk_id}'")
    snippet = " ".join(stored.split())[:80]
    match = bool(snippet) and snippet in " ".join(body.split())
    rec.step("Compare the source page passage with the database (read-back)", "the stored text",
             match, f"first 80 chars {'match' if match else 'differ'}")
    check_context(rec, source, chunk_id)
    check_pdf_pages(rec, source)
    source.close()
    rec.page = page
    ctx["chunk_id"] = chunk_id


def feature_gap_path(page, base, rec, ctx):
    ask(page, base, NO_EVIDENCE_Q)
    body = page.locator("body").inner_text()
    gap = any(page.get_by_role("heading", name=h).count() for h in ("Not in the corpus", "No evidence"))
    rec.step("Ask about a firm with no stored filings", "'Not in the corpus' or 'No evidence'", gap,
             next((h for h in ("Not in the corpus", "No evidence", "Answer") if h in body), "no heading"))
    rec.step("Look for invented citations", "no citation links", citation_links(page).count() == 0,
             f"{citation_links(page).count()} citation links")
    rec.step("Look for the gap note", "a 'Gap:' box", "Gap:" in body, "present" if "Gap:" in body else "missing")
    footer = re.search(r"firms: ([^|]*)\|", body)
    firms = footer.group(1).strip() if footer else "no footer"
    rec.step("Read the footer's firms", "the gap firm, e.g. 'LPLA (no documents)', not 'none' (#50)",
             firms not in ("none", "no footer"), firms)


def feature_invalid_chunk(page, base, rec, ctx):
    page.goto(base + "?chunk=NOT-A-REAL-CHUNK")
    wait_for_text(page, SOURCE_PAGE_DONE, "the source page")
    body = page.locator("body").inner_text()
    rec.step("Open a chunk ID that does not exist", "a clear 'not in the stored corpus' error",
             "is not in the stored corpus" in body, "error shown" if "is not in the stored corpus" in body else "no error")


def feature_download_document(page, base, rec, ctx):
    chunk_id = ctx.get("chunk_id") or psql(VERIFY_DB, "SELECT chunk_id FROM chunks LIMIT 1")
    page.goto(base + "?chunk=" + quote(chunk_id))
    wait_for_text(page, ["Download stored document", "not found locally", "is not in the stored corpus"],
                  "the source page")
    button = page.get_by_role("button", name="Download stored document")
    if not button.count():
        body = page.locator("body").inner_text()
        note = next((l for l in body.splitlines() if "not found locally" in l), "no download button")
        rec.step("Open the source page", "a download button or a clear 'not found locally' note",
                 "not found locally" in body, note[:160])
        rec.unreachable("raw file not in data/raw/ (precondition: copy it from the team Box link)")
        return
    with page.expect_download() as d:
        button.click()
    path = rec.dir / d.value.suggested_filename
    d.value.save_as(path)
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    want = psql(VERIFY_DB, f"SELECT d.sha256 FROM chunks c JOIN documents d USING (doc_id) WHERE c.chunk_id = '{chunk_id}'")
    rec.step("Download the stored document", "sha256 matches the documents table", got == want,
             f"sha256 {'match' if got == want else 'differs'} ({got[:12]})")


def feature_coverage(page, base, rec, ctx):
    page.goto(base + "coverage")
    wait_for_text(page, ["are not shown yet"], "the Coverage page")
    body = " ".join(page.locator("body").inner_text().split())
    rec.step("Open the Coverage page", "a table with firms and document types",
             "EDJ" in body and "10-K" in body,
             "table shown" if "EDJ" in body else "no table")
    n, first, last = psql(VERIFY_DB, "SELECT count(*), min(published_at), max(published_at) FROM documents "
                                     "WHERE entity_id = 'EDJ' AND doc_type = '10-K'").split("|")
    n = int(n)
    from cee.app.views.coverage_page import cell_state
    cadence = psql(VERIFY_DB, "SELECT expected_cadence FROM source_registry "
                              "WHERE entity_id = 'EDJ' AND doc_type = '10-K' LIMIT 1") or None
    state = cell_state(n, cadence).upper()
    span = first if first == last else f"{first} to {last}"
    want = f"{state} " + ("0 docs" if n == 0 else f"{n} doc{'' if n == 1 else 's'} {span}")
    rec.step("Read back EDJ 10-K from the database", f"cell '{want}'", want in body,
             "cell matches" if want in body else "cell differs from the database")
    empty = psql(VERIFY_DB, "SELECT count(*) FROM source_registry r WHERE r.entity_id = 'EDJ' AND NOT EXISTS "
                            "(SELECT 1 FROM documents d WHERE d.entity_id = r.entity_id AND d.doc_type = r.doc_type)")
    rec.step("Empty combinations are marked", "an EMPTY cell for each registry type with no document",
             int(empty) == 0 or "EMPTY 0 docs" in body, f"{empty} EDJ types empty in the database")
    rec.step("Themes note", "says themes are not shown yet", "Themes (tier 5 research) are not shown yet" in body,
             "note present" if "are not shown yet" in body else "note missing")


DRIVERS = {"ask-answer": feature_ask_answer, "ask-progress": feature_ask_progress,
           "open-citation": feature_open_citation,
           "gap-path": feature_gap_path, "invalid-chunk": feature_invalid_chunk,
           "download-document": feature_download_document, "coverage": feature_coverage}


def drive(features: list[str]) -> bool:
    from playwright.sync_api import sync_playwright
    st = load_state()
    if not (st and health(st["port"])):
        raise RuntimeError("No verify instance is running. Run: python scripts/verify_cee.py launch")
    run_dir = RUNS / st["run_id"]
    base = f"http://localhost:{st['port']}/"
    results, ctx = [], {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        for f in features:
            print(f"{f}:")
            rec = Recorder(run_dir, f, page)
            try:
                DRIVERS[f](page, base, rec, ctx)
            except Exception as e:
                rec.step(f"Run {f}", "no error", False, f"{type(e).__name__}: {str(e)[:200]}")
            with open(run_dir / "steps.jsonl", "a", encoding="utf-8") as out:
                for s in rec.steps:
                    out.write(json.dumps(s) + "\n")
            results.append({"feature": f, "status": rec.status})
        browser.close()
    summary = {**st, "results": results, "finished": datetime.now().isoformat(timespec="seconds")}
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSnapshot: {st.get('snapshot')}  Commit: {st['head'][:7]}")
    print("SUMMARY  " + "  ".join(f"{r['feature']}={r['status']}" for r in results))
    print(f"Evidence: {run_dir}")
    return all(r["status"] != "FAIL" for r in results)


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["doctor", "launch", "drive", "cleanup", "run"])
    ap.add_argument("features", nargs="*", help=f"default: all of {', '.join(FEATURES)}")
    ap.add_argument("--port", type=int, default=PORT)
    a = ap.parse_args()
    unknown = [f for f in a.features if f not in DRIVERS]
    if unknown:
        ap.error(f"unknown feature(s) {unknown}; choose from {FEATURES}")
    features = a.features or FEATURES
    try:
        if a.command == "doctor":
            return 0 if doctor(a.port) else 1
        if a.command == "launch":
            launch(a.port)
            return 0
        if a.command == "drive":
            return 0 if drive(features) else 1
        if a.command == "cleanup":
            cleanup()
            return 0
        if not doctor(a.port):
            return 1
        try:
            launch(a.port)
            ok = drive(features)
        finally:
            cleanup()
        print("VERIFY " + ("PASS" if ok else "FAIL"))
        return 0 if ok else 1
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
