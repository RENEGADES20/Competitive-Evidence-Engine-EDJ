"""Drive the real app like a user and keep the evidence. Works on Windows and macOS.

Used by the verify-cee skill (.claude/skills/verify-cee/SKILL.md). Run with the project venv:

  python scripts/verify_cee.py doctor          # is everything ready to verify?
  python scripts/verify_cee.py run             # launch, drive every feature, clean up
  python scripts/verify_cee.py run ask-answer gap-path
  python scripts/verify_cee.py launch | drive <feature...> | cleanup
  python scripts/verify_cee.py shots           # README images into docs/assets, after launch (#270)
  python scripts/verify_cee.py run --source-db cee_84 --port 8684   # a private copy (#84)

It never touches your own database or app: it copies database `cee` (or --source-db) to
`cee_verify` (`<source-db>_verify`), starts its own Streamlit on port 8599 (or --port) with the
mock provider, and removes both at the end. Pass the same --source-db to drive and cleanup.
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


def _env_value(name: str) -> str:
    # Same rule as scripts/_common.* and Compose: the environment wins over .env.
    if os.environ.get(name, "").strip():
        return os.environ[name].strip().strip('"')
    env_file = REPO / ".env"
    value = ""
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(rf"^\s*{name}\s*=\s*(.*)$", line)
            if m:
                value = m.group(1).strip().strip('"')
    return value


CONTAINER = _env_value("CEE_DB_CONTAINER") or "cee-db"   # resolved once, at import (#129)
SOURCE_DB, VERIFY_DB = "cee", "cee_verify"
PORT = 8599
WINDOWS = os.name == "nt"

ANSWERABLE_Q = "What does Edward Jones's 10-K say about its number of financial advisors?"
NO_EVIDENCE_Q = "What does LPL Financial's 10-K say about its number of financial advisors?"
TWO_FIRM_Q = "How do Morgan Stanley and Raymond James approach advisor recruiting?"  # #245: 2 sub-questions
# Q21: five firms + a theme (#117). The firms the coverage note must name are read from the
# database (theme_gap_expected): exactly those with no on-theme chunk the question may retrieve.
# A firm with one, even below the floor, takes its theme slot (#190) and is no gap (corpus-2026-11-16:
# RJF is the gap; with trade press loaded (#57) RJF has on-theme articles and no firm is).
THEME_GAP_Q = "What do we know about the generational wealth transfer, and how are these five preparing for it?"
THEME_GAP_NOTE = "No passages on the theme (Generational wealth transfer) for"
# ask-stop-retry (#277) runs last: it leaves query_log rows with no answer (the other features read the newest
# answered row anyway)
FEATURES = ["ask-answer", "ask-progress", "open-citation", "gap-path", "invalid-chunk", "download-document", "coverage", "filters", "feedback",
            "architecture-page", "ask-stop-retry"]
ASSETS = REPO / "docs" / "assets"


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


def theme_gap_expected(db: str) -> list[str]:
    """Q21's gap firms, derived from the database, not hard-coded: each firm the question names
    with no chunk that passes its entity filter, the theme's keyword filter and the question's
    document-type scope (the same SQL filters search() applies to the on-theme pool, #117)."""
    import psycopg
    from cee.answer.validate import _short_name
    from cee.retrieve.fts import doc_type_scope_sql, entity_filter, on_theme_filter, resolve
    q = resolve(THEME_GAP_Q)
    on_theme, on_params = on_theme_filter(q.themes)
    scope, scope_params = doc_type_scope_sql(q)
    gaps = []
    with psycopg.connect(db_url(db)) as conn:
        for e in q.entities:
            where, params = entity_filter([e])
            n = conn.execute(f"SELECT count(*) FROM chunks c JOIN documents d USING (doc_id) "
                             f"WHERE {where} AND {on_theme} AND {scope}",
                             params | on_params | scope_params).fetchone()[0]
            if n == 0:
                gaps.append(_short_name(e))
    return gaps


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
    # MAP=on (#247): the default, set explicitly so a teammate's older .env (MAP=off) cannot change the run.
    # MOCK_FAIL_FILE (#277): the ask-stop-retry driver writes "reduce" there to inject a failure, then removes it.
    env = {**os.environ, "DATABASE_URL": db_url(VERIFY_DB), "LLM_PROVIDER": "mock", "MOCK_DELAY_S": "1.5",
           "MAP": "on", "MOCK_FAIL_FILE": str(run_dir / MOCK_FAIL_NAME)}
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
        if self.status != "FAIL":  # a step that could not run never hides one that failed
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


def check_part_gaps(rec, page, what: str) -> None:
    """ask-part-gap (#215): every plan part with no claim of the mock's gets one code-built gap,
    flagged part_gap, shown on the page with its chip. Expected parts read from the newest
    query_log row (plan parts, the mock's claim part ids), not hard-coded: the mock's top 3
    passages decide which parts it cites."""
    import base64
    import json as _json
    # base64: passage text holds non-ASCII characters the console code page cannot decode
    b64 = psql(VERIFY_DB, "SELECT encode(convert_to(json_build_object('parts', filters->'plan'->'parts', "
                          "'answer', answer)::text, 'UTF8'), 'base64') FROM query_log WHERE answer IS NOT NULL ORDER BY query_id DESC LIMIT 1")
    row = _json.loads(base64.b64decode("".join(b64.split())).decode("utf-8"))
    parts = [p["id"] for p in row["parts"] or []]
    # #247: the reduce answers a part with a claim, an adjacent item or a matrix gap (code-built)
    cited = {c.get("part_id") for c in [*row["answer"]["claims"], *row["answer"]["adjacent"]]}
    gapped = {g.get("part_id") for g in row["answer"]["gaps"] if "part_gap" not in (g.get("flags") or [])}
    expected = [p for p in parts if p not in cited and p not in gapped]
    gaps = [g for g in row["answer"]["gaps"] if "part_gap" in (g.get("flags") or [])]
    body = page.locator("body").inner_text()
    shown = [g["what"] for g in gaps if g["what"] in body]
    ok = (sorted(g["part_id"] for g in gaps) == sorted(expected) and len(shown) == len(gaps)
          and body.count("part_gap") == len(gaps))
    rec.step(f"Read the part gaps of {what}",
             f"one 'part_gap' gap per plan part without a mock claim ({expected or 'none'}), each shown with its chip",
             ok, f"parts {parts}; mock claim parts {sorted(p for p in cited if p)}; part gaps "
                 f"{[(g['part_id'], g['what'][:70]) for g in gaps]}; shown {len(shown)}; chips {body.count('part_gap')}")


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
    # #247: the answer is written from the evidence matrix: the shown behavior is the matrix's (or the
    # documented re-judge by withhold_normative), nothing is cited outside the matrix, every cited id is
    # in the logged chunk ids (retrieval + corrective re-search, B1) and every citation chip is linked.
    row = psql(VERIFY_DB,
               "SELECT (filters->'map'->>'behavior') || '|' || (answer->>'behavior') || '|' || "
               "coalesce(filters->'reduce'->>'behavior_rejudged', 'none') || '|' || "
               "coalesce(filters->'reduce'->>'outside_matrix', 'none') || '|' || "
               "(SELECT count(*) FROM jsonb_array_elements(answer->'claims') c, "
               "jsonb_array_elements_text(c->'chunk_ids') id WHERE NOT (id = ANY(q.chunk_ids))) "
               "FROM query_log q WHERE q.answer IS NOT NULL ORDER BY query_id DESC LIMIT 1")
    parts = row.split("|")
    same = len(parts) == 5 and (parts[0] == parts[1] or (parts[1] == "answer_with_boundary" and parts[2] == "true"))
    unlinked = "not in the retrieved set" in page.locator("body").inner_text()
    rec.step("Read the newest query_log row: answer from the evidence matrix (#247)",
             "shown behavior = filters.map.behavior, 0 outside the matrix, 0 cited ids outside the logged "
             "chunk ids, no unlinked chip",
             same and parts[3] == "0" and parts[4] == "0" and not unlinked, f"{row}; unlinked chip={unlinked}")
    check_part_gaps(rec, page, "the EDJ advisors question (one sub-question)")
    ask(page, base, TWO_FIRM_Q)
    check_part_gaps(rec, page, "the two-firm question (two sub-questions)")
    ask(page, base, THEME_GAP_Q)
    body = page.locator("body").inner_text()
    line = next((l.strip() for l in body.splitlines() if l.strip().startswith("Coverage:")), "no coverage note")
    expected = theme_gap_expected(VERIFY_DB)
    named = (line.split(THEME_GAP_NOTE, 1)[1].split(".")[0].strip().split(", ")
             if THEME_GAP_NOTE in line else [])  # no short name holds a period
    want = (f"coverage note says '{THEME_GAP_NOTE} {', '.join(expected)}.'" if expected
            else f"no '{THEME_GAP_NOTE}' in the coverage note")
    rec.step("Ask the five firms about the wealth transfer (Q21)",
             f"{want} (gap firms read from the database: no on-theme chunk)",
             line != "no coverage note" and sorted(named) == sorted(expected),
             f"expected gaps {expected}; note: {line}")


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
    # #272 progressive page: the plan first (the mock map waits MOCK_DELAY_S, so the evidence is not there
    # yet), then the map call's cited evidence (the mock reduce waits too, so the answer is not there yet).
    page.wait_for_function("() => document.body.innerText.includes('Plan:')", timeout=RENDER_TIMEOUT_S * 1000)
    body = page.locator("body").inner_text()
    rec.step("Ask; look as soon as the plan shows (#272)", "the plan line, no evidence and no answer yet",
             "Plan: Decomposing the question" in body and "Evidence so far" not in body and "LLM called:" not in body,
             next((l for l in body.splitlines() if l.startswith("Plan:")), "")[:200])
    page.wait_for_function("() => document.body.innerText.includes('Evidence so far')",
                           timeout=RENDER_TIMEOUT_S * 1000)
    body = page.locator("body").inner_text()
    cards = page.locator(".cee-claim", has_text="EVIDENCE - Edward Jones")
    chips = cards.first.locator(".cee-chip").count() if cards.count() else 0
    rec.step("Look again while the answer is still being written (#272)",
             "'Evidence so far' with at least one Edward Jones evidence card carrying a citation chip; no answer yet",
             cards.count() > 0 and chips > 0 and "LLM called:" not in body,
             f"evidence cards={cards.count()}, chips on the first={chips}, answer shown={'LLM called:' in body}")
    # The verify app's mock waits MOCK_DELAY_S in the mock map and the mock reduce (#248: the question
    # takes map.a1.EDJ -> behavior answer -> the reduce call): the page is caught mid-run.
    page.wait_for_function("() => document.body.innerText.includes('Synthesizing the answer')",
                           timeout=RENDER_TIMEOUT_S * 1000)
    body = page.locator("body").inner_text()
    bar = page.locator('[data-testid="stProgress"]').count() > 0
    early = bar and "Reading the question:" in body and "LLM called:" not in body
    rec.step("Ask; look while the answer is being built", "progress bar and step lines, no answer yet",
             early, f"progress bar={bar}, first step shown={'Reading the question:' in body}, "
                    f"answer shown={'LLM called:' in body}")
    # #275 streamed answer: the mock reduce feeds its output through the stream parser and waits MOCK_DELAY_S
    # after the claim, so the checked claim is on the page before the final answer.
    page.wait_for_function("() => document.body.innerText.includes('Answer (in progress')",
                           timeout=RENDER_TIMEOUT_S * 1000)
    body = page.locator("body").inner_text()
    early_cards = page.locator(".cee-claim", has_text="CLAIM (CHECKING)")
    early_chips = early_cards.first.locator(".cee-chip").count() if early_cards.count() else 0
    rec.step("Look while the answer streams (#275)",
             "'Answer (in progress: checks running)' with a checked claim card carrying a citation chip; "
             "no final answer yet",
             early_cards.count() > 0 and early_chips > 0 and "LLM called:" not in body,
             f"early claim cards={early_cards.count()}, chips on the first={early_chips}, "
             f"answer shown={'LLM called:' in body}")
    wait_for_text(page, ["LLM called:"], "the answer")
    body = page.locator("body").inner_text()
    rec.step("Look once the answer is ready (#275)", "the in-progress block is gone; the final answer shows",
             "Answer (in progress" not in body and "CLAIM (CHECKING)" not in body and "LLM called:" in body,
             f"in-progress shown={'Answer (in progress' in body}, answer shown={'LLM called:' in body}")
    status = page.get_by_text("How this answer was built", exact=False)
    hidden = not page.locator(".cee-trace").first.is_visible()
    rec.step("Look above the answer", "a collapsed 'How this answer was built' box",
             status.count() > 0 and hidden, f"box={status.count() > 0}, trace hidden={hidden}")
    lines = open_trace(page)
    from cee.ask import STAGES   # #248: 9 stages; the count is never a literal
    rec.step("Open the trace", f"{len(STAGES)} step lines", len(lines) == len(STAGES), " / ".join(lines)[:400])
    map_line = next((l for l in lines if l.startswith("Map step") or l.startswith("Extracting from")), "")
    rec.step("Read the extract line (#246, #248)",
             "'Extracting from 1 firm (mock, no model call): N cells: ...; behavior by code: answer'",
             map_line.startswith("Extracting from 1 firm (mock, no model call):")
             and map_line.endswith("behavior by code: answer"), map_line)
    research = next((l for l in lines if l.startswith("Re-search")), "")
    rec.step("Read the re-search line (#248)", "'Re-search...' (nothing to re-search, or what was re-searched)",
             research.startswith(("Re-search: every sub-question has evidence", "Re-searching sub-questions")),
             research)
    plan = next((l for l in lines if l.startswith("Decomposing the question")), "")
    rec.step("Read the decompose line (#214, #245, #248)",
             "'Decomposing the question (rules, no model call): 1 aspect x 1 firm = 1 sub-question: a1.EDJ'",
             "(rules, no model call): 1 aspect x 1 firm = 1 sub-question: a1.EDJ" in plan, plan)
    body = page.locator("body").inner_text()
    n_meta = re.search(r"(\d+) passages found", body)
    n_trace = re.search(r"Searching 1 sub-question: (\d+) passage", " ".join(lines))
    same = bool(n_meta and n_trace and n_meta.group(1) == n_trace.group(1))
    rec.step("Compare the search line with the footer", "same passage count", same,
             f"trace {n_trace.group(1) if n_trace else '?'} vs footer {n_meta.group(1) if n_meta else '?'}")
    # #248: the synthesize line is the reduce's (the extract line also says "no model call")
    model = next((l for l in lines if l.startswith("Synthesizing the answer")), "")
    check = next((l for l in lines if "Checking citations" in l), "")
    rec.step("Read the synthesize and citation lines",
             "'Synthesizing the answer from the evidence matrix (mock, one call)' and 'N matched'",
             "from the evidence matrix (mock, one call)" in model and "matched" in check, f"{model} | {check}")
    ask(page, base, NO_EVIDENCE_Q)
    lines = open_trace(page)
    model = next((l for l in lines if l.startswith("No passages found: no model call")), "")
    body = page.locator("body").inner_text()
    rec.step("Ask the no-evidence question, open the trace", "model step skipped, no model call",
             "no model call" in model and "LLM called: False" in body, model)
    # plan-parts (#214, #245): a two-firm question is one sub-question per firm, and the plan is logged
    ask(page, base, TWO_FIRM_Q)
    lines = open_trace(page)
    plan = next((l for l in lines if l.startswith("Decomposing the question")), "")
    search_line = next((l for l in lines if l.startswith("Searching ")), "")
    extract_line = next((l for l in lines if l.startswith("Extracting from")), "")
    rec.step("Ask a two-firm question, open the trace",
             "decompose '1 aspect x 2 firms = 2 sub-questions: a1.MS; a1.RJF', 'Searching 2 sub-questions: ...', "
             "'Extracting from 2 firms ...'",
             "1 aspect x 2 firms = 2 sub-questions: a1.MS; a1.RJF" in plan
             and search_line.startswith("Searching 2 sub-questions: ") and extract_line.startswith("Extracting from 2 firms"),
             f"{plan} | {search_line} | {extract_line}")
    row = psql(VERIFY_DB, "SELECT (filters->'plan'->>'source') || '|' || jsonb_array_length(filters->'plan'->'parts')"
                          " || '|' || (filters->'llm_calls')::text || '|' || (filters->'cost'->>'calls') || '|' || "
                          "(filters->'cost'->>'usd') FROM query_log WHERE answer IS NOT NULL ORDER BY query_id DESC LIMIT 1")
    rec.step("Read the newest query_log row (side effect)",
             "plan source rules, 2 sub-questions, llm_calls all 0 and cost 0 calls / $0 (#248; the mock map and "
             "reduce are not paid calls)",
             row.replace(" ", "") in ('rules|2|{"map":0,"remap":0,"answer":0,"planner":0}|0|0',
                                      'rules|2|{"map":0,"remap":0,"answer":0,"planner":0}|0|0.0'), row)


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
        with pymupdf.open(path) as doc:
            total = doc.page_count
            on_page = words(doc[int(n) - 1].get_text("text"))
        page.goto(page.url.split("?")[0] + "?chunk=" + quote(cid))
        # Texts only this chunk's page has: the previous source page also shows "Download stored
        # document", so waiting for that could read the old page before the PDF page renders.
        wait_for_text(page, [f"Page {n} of {total} of the stored PDF", f"Page {n} is not in the stored PDF",
                             "Could not open the PDF page", "is not in the stored corpus"],
                      f"the source page for {cid}")
        image = page.locator('[data-testid="stImage"] img')
        try:
            image.first.wait_for(timeout=RENDER_TIMEOUT_S * 1000)
        except Exception:  # no image: the step below reports it
            pass
        body = page.locator("body").inner_text()
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


def check_date_label(rec, page, source_chunk: str) -> None:
    """cite-date: an undated page (date_basis = retrieved, ADR-007 T-09) says "Page content as of",
    never "Filed:"; a source-dated chunk still says "Filed:"."""
    row = psql(VERIFY_DB, "SELECT c.chunk_id || '|' || d.published_at FROM chunks c JOIN documents d USING (doc_id) "
                          "WHERE d.date_basis = 'retrieved' ORDER BY c.chunk_id LIMIT 1")
    if not row:
        rec.unreachable("no date_basis = 'retrieved' document in the database (cite-date)")
        return
    cid, published = row.split("|", 1)
    page.goto(page.url.split("?")[0] + "?chunk=" + quote(cid))
    wait_for_text(page, [f"Chunk: {cid}", "is not in the stored corpus"], f"the source page for {cid}")
    body = page.locator("body").inner_text()
    want = f"Page content as of: {published}"
    rec.step(f"Open undated page chunk {cid} (cite-date)", f"'{want}' and no 'Filed:'",
             want in body and "Filed:" not in body,
             f"'{want}' {'shown' if want in body else 'missing'}, 'Filed:' {'shown' if 'Filed:' in body else 'absent'}")
    page.goto(page.url.split("?")[0] + "?chunk=" + quote(source_chunk))
    wait_for_text(page, [f"Chunk: {source_chunk}", "is not in the stored corpus"], f"the source page for {source_chunk}")
    body = page.locator("body").inner_text()
    rec.step(f"Reopen source-dated chunk {source_chunk} (cite-date)", "'Filed:' and no 'Page content as of'",
             "Filed:" in body and "Page content as of" not in body,
             f"'Filed:' {'shown' if 'Filed:' in body else 'missing'}")


def wait_for_cited(page, chunk_id: str) -> None:
    """#248 (flake in run 20261119-230844): the source page header ('Stored passage') can render before
    the cited passage; wait for its 'CITED PASSAGE · <id>' tag (or the 'not in the stored corpus' error)
    with the render timeout, so the body is never read half-drawn. A page that never draws it is a
    RenderTimeout, not a wrong FAIL."""
    wait_for_text(page, [f"CITED PASSAGE · {chunk_id}", "is not in the stored corpus"],
                  f"the cited passage {chunk_id}")


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
    wait_for_cited(source, chunk_id)   # #248: the passage itself renders after the page header
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
    check_date_label(rec, source, chunk_id)
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
    plain = "That is a valid result, not an error" in body or "do not answer this directly" in body
    rec.step("Read the line under the heading (#119)", "a plain sentence saying no evidence is a valid result",
             plain, "present" if plain else "missing")
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
    n, first, last = psql(VERIFY_DB, "SELECT count(*), min(published_at) FILTER (WHERE date_basis = 'source'), "
                                     "max(published_at) FILTER (WHERE date_basis = 'source') FROM documents "
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


FILTER_Q = "What do the firms say about advisor recruiting?"
FILTER_FIRM, FILTER_FROM, FILTER_TO, FILTER_KEYWORD = "RJF", "2026-01-01", "2026-06-30", "advisor"


def feature_filters(page, base, rec, ctx):
    page.goto(base)
    wait_idle(page)
    side = page.locator("[data-testid='stSidebar']")
    side.get_by_text("Filters", exact=True).wait_for(timeout=RENDER_TIMEOUT_S * 1000)
    side.locator("[data-testid='stMultiSelect'] input").click()
    page.get_by_role("option", name=re.compile(rf"^{FILTER_FIRM} ")).click()
    page.keyboard.press("Escape")
    dates = side.locator("[data-testid='stDateInput'] input")  # this Streamlit: a start and an end date box
    dates.nth(0).fill(FILTER_FROM)
    dates.nth(1).fill(FILTER_TO)
    dates.nth(1).press("Enter")
    side.get_by_role("textbox", name="Keywords").fill(FILTER_KEYWORD)
    side.get_by_role("textbox", name="Keywords").press("Enter")
    wait_idle(page)
    box = page.get_by_role("textbox", name="Question")
    box.fill(FILTER_Q)
    page.get_by_role("button", name="Ask").click()
    wait_for_text(page, ["LLM called:"], "the filtered answer")
    body = " ".join(page.locator("body").inner_text().split())
    want = f"filters: firms {FILTER_FIRM}; dates {FILTER_FROM} to {FILTER_TO}; keywords {FILTER_KEYWORD}"
    rec.step("Set firm, date range and keyword, then ask", f"meta line '{want}'", want in body,
             "meta line matches" if want in body else "filters missing from the meta line")
    ids = [l.inner_text().strip() for l in citation_links(page).all()]
    rec.step("Look at the claims", "at least one citation link", bool(ids), f"{len(ids)} citation links")
    rows = psql(VERIFY_DB, "SELECT c.chunk_id, d.entity_id, d.published_at, d.date_basis, "
                           f"(c.tsv @@ phraseto_tsquery('english', '{FILTER_KEYWORD}')) FROM chunks c "
                           "JOIN documents d USING (doc_id) WHERE c.chunk_id = ANY(ARRAY["
                           + ",".join("'" + i.replace("'", "''") + "'" for i in ids) + "]::text[])").splitlines() if ids else []
    rows = [r.split("|") for r in rows]
    other = [r[0] for r in rows if r[1] != FILTER_FIRM]
    rec.step("Read back the cited chunks: firm", f"every cited chunk is {FILTER_FIRM}", not other and bool(rows),
             f"{len(rows)} cited chunks, {len(other)} from another firm {other[:3]}")
    outside = [r[0] for r in rows if not (FILTER_FROM <= r[2] <= FILTER_TO and r[3] == "source")]
    rec.step("Read back the cited chunks: dates", f"published {FILTER_FROM} to {FILTER_TO}", not outside and bool(rows),
             f"{len(outside)} outside the range {outside[:3]}")
    nokw = [r[0] for r in rows if r[4] != "t"]
    rec.step("Read back the cited chunks: keyword", f"every cited chunk contains '{FILTER_KEYWORD}'",
             not nokw and bool(rows), f"{len(nokw)} without the keyword {nokw[:3]}")
    logged = psql(VERIFY_DB, "SELECT filters->>'firm_filter', filters->>'date_range', filters->>'keywords' "
                             "FROM query_log WHERE answer IS NOT NULL ORDER BY query_id DESC LIMIT 1")
    rec.step("Check the query log (side effect)", "filters stored with the query",
             FILTER_FIRM in logged and FILTER_FROM in logged and FILTER_KEYWORD in logged, logged)
    prompt = (REPO / "src/cee/answer/prompt.py").read_text(encoding="utf-8")
    rec.step("Filters stay out of the prompt", "prompt.py never reads the filter fields",
             not any(f in prompt for f in ("firm_filter", "date_range", "keywords")), "prompt.py checked")


def send_feedback(page, rating: str, comment: str) -> None:
    form = page.locator("[data-testid='stForm']")
    form.get_by_text(rating, exact=True).click()
    form.get_by_role("textbox", name="Comment (optional)").fill(comment)
    form.get_by_role("button", name="Send feedback").click()
    wait_for_text(page, ["Feedback saved for query", "Feedback updated for query"], "the feedback message")


def feature_feedback(page, base, rec, ctx):
    ask(page, base, ANSWERABLE_Q)
    m = re.search(r"Query #(\d+)", page.locator("body").inner_text())
    rec.step("Ask the EDJ advisors question", "a query number in the meta line", bool(m),
             f"query #{m.group(1)}" if m else "no query number")
    if not m:
        return
    qid = m.group(1)
    rows = lambda: psql(VERIFY_DB, f"SELECT rating, coalesce(comment, '') FROM query_feedback WHERE query_id = {qid}").splitlines()
    send_feedback(page, "Not helpful", "verify-cee: wrong period")
    body = page.locator("body").inner_text()
    rec.step("Send Not helpful with a comment", f"'Feedback saved for query #{qid}'",
             f"Feedback saved for query #{qid}" in body, "message shown" if "Feedback saved" in body else "no message")
    got = rows()
    rec.step("Read back query_feedback", "one row: -1 | verify-cee: wrong period",
             got == ["-1|verify-cee: wrong period"], f"{got}")
    rec.step("The answer stays on the page", "claims and citations still shown after sending",
             citation_links(page).count() > 0, f"{citation_links(page).count()} citation links")
    send_feedback(page, "Helpful", "")
    body = page.locator("body").inner_text()
    rec.step("Send again: Helpful, no comment", "'Feedback updated ... replaces the earlier one'",
             "replaces the earlier one" in body, "message shown" if "replaces the earlier one" in body else "no message")
    got = rows()
    rec.step("Read back query_feedback again", "still one row, now 1 with no comment", got == ["1|"], f"{got}")


ARCH_HOVER, ARCH_FOCUS = "F", "M"   # #270: Search (hover), Evidence matrix (keyboard focus)


def tip_text(page, mid: str) -> str:
    return " ".join(page.locator(f"#tip-{mid}").inner_text().split())


def _flat(text: str) -> str:
    return " ".join(text.split())


def feature_architecture_page(page, base, rec, ctx):
    from cee.app.architecture import KINDS, MODULES, by_id
    page.goto(base + "architecture")
    wait_for_text(page, ["Every module"], "the Architecture page")
    page.locator("#node-F").wait_for(timeout=RENDER_TIMEOUT_S * 1000)
    body = page.locator("body").inner_text()
    nav = (page.get_by_role("link", name="Architecture").count() > 0
           and page.get_by_role("link", name="Design", exact=True).count() == 0)
    rec.step("Open Architecture from the top navigation", "nav shows Architecture, not Design", nav,
             "Architecture in nav, no Design" if nav else "nav differs")
    missing = [m.label for m in MODULES if page.locator(f"#node-{m.id}").count() != 1 or m.label not in body]
    rec.step("Read the diagram", f"all {len(MODULES)} modules drawn as boxes", not missing,
             f"missing: {missing}" if missing else f"{len(MODULES)} boxes")
    hidden = not any(page.locator(f"#tip-{m.id}").is_visible() for m in MODULES)
    rec.step("Before any hover", "no explanation box is open", hidden, "none open" if hidden else "one is open")
    m = by_id()[ARCH_HOVER]
    page.locator(f"#node-{m.id}").hover()
    page.wait_for_timeout(400)
    tip = tip_text(page, m.id)
    ok = (page.locator(f"#tip-{m.id}").is_visible() and _flat(m.does) in tip and _flat(m.rule) in tip
          and KINDS[m.kind].upper() in tip)
    rec.step(f"Hover over '{m.label}'", f"its box shows what it does, '{KINDS[m.kind]}' and the rule",
             ok, tip[:200] if tip else "no tooltip text")
    page.mouse.move(2, 2)
    page.wait_for_timeout(300)
    m = by_id()[ARCH_FOCUS]
    # Keyboard: from the box before it, Tab moves focus to it, as a keyboard user would.
    order = [x.id for x in MODULES]
    page.locator(f"#node-{order[order.index(m.id) - 1]}").focus()
    page.keyboard.press("Tab")
    page.wait_for_timeout(400)
    focused = page.evaluate("() => document.activeElement && document.activeElement.id")
    tip = tip_text(page, m.id)
    ok = focused == f"node-{m.id}" and page.locator(f"#tip-{m.id}").is_visible() and _flat(m.rule) in tip
    rec.step(f"Tab to '{m.label}' with the keyboard", "focus lands on it and its explanation shows",
             ok, f"focus={focused}; {tip[:160]}")
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    items = page.locator("ol.arch-list li")
    listed = items.count() == len(MODULES) and all(
        _flat(x.rule) in _flat(items.nth(i).inner_text()) for i, x in enumerate(MODULES))
    rec.step("Read the list under the diagram", f"{len(MODULES)} modules with the same text (touch, screen readers)",
             listed, f"{items.count()} items")
    figures = re.search(r"\$\s?\d|\d[\d,]*\s?(billion|million)", body, re.I)
    rec.step("Look for firm figures", "none on the page", not figures, figures.group(0) if figures else "none")
    page.goto(base + "design")
    wait_idle(page)
    page.wait_for_timeout(1000)
    gone = "Design language" not in page.locator("body").inner_text()
    rec.step("Open the old /design address", "the Design gallery is gone", gone,
             "no Design gallery" if gone else "Design gallery still served")


def _save_clip(page, path: Path, top: float, bottom: float) -> None:
    """Streamlit scrolls inside its own container, so the viewport is made tall enough first."""
    main = page.locator('[data-testid="stMainBlockContainer"]').bounding_box()
    page.screenshot(path=str(path), clip={"x": main["x"], "y": top, "width": main["width"], "height": bottom - top})


def _answer_clip(page, path: Path) -> None:
    """From the question box to the meta line under the answer."""
    top = page.get_by_text("Question", exact=True).first.bounding_box()["y"] - 12
    meta = page.get_by_text("LLM called:").last.bounding_box()
    _save_clip(page, path, top, meta["y"] + meta["height"] + 12)


def shots() -> bool:
    """#270: the README images, from the verify instance (mock provider), into the run folder and
    docs/assets (answer, source, gap, architecture). Run after `launch`."""
    from playwright.sync_api import sync_playwright
    st = load_state()
    if not (st and health(st["port"])):
        raise RuntimeError("No verify instance is running. Run: python scripts/verify_cee.py launch")
    out = RUNS / st["run_id"] / "shots"
    out.mkdir(parents=True, exist_ok=True)
    base = f"http://localhost:{st['port']}/"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 2400})
        ask(page, base, ANSWERABLE_Q)
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        _answer_clip(page, out / "answer.png")
        chunk_id = citation_links(page).first.inner_text().strip()
        page.goto(base + "?chunk=" + quote(chunk_id))
        wait_for_text(page, SOURCE_PAGE_DONE, "the source page")
        wait_for_cited(page, chunk_id)
        top = page.get_by_text("Back to question").first.bounding_box()["y"] - 12
        cited = page.locator(".cee-ctx.cited").first.bounding_box()
        _save_clip(page, out / "source.png", top, cited["y"] + cited["height"] + 16)
        ask(page, base, NO_EVIDENCE_Q)
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        _answer_clip(page, out / "gap.png")
        page.goto(base + "architecture")
        wait_for_text(page, ["Every module"], "the Architecture page")
        page.set_viewport_size({"width": 1400, "height": 1100})
        page.locator("#node-F").hover()
        page.wait_for_timeout(500)
        box = page.locator(".arch-wrap").bounding_box()
        top = page.locator(".cee-eyebrow").first.bounding_box()["y"] - 16
        _save_clip(page, out / "architecture.png", top, box["y"] + box["height"] + 16)
        browser.close()
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name in ("answer", "source", "gap", "architecture"):
        shutil.copyfile(out / f"{name}.png", ASSETS / f"{name}.png")
        print(f"  {name}.png -> {ASSETS / (name + '.png')}")
    print(f"Shots kept in {out}")
    return True


MOCK_FAIL_NAME = "mock-fail.txt"   # #277: MOCK_FAIL_FILE of the verify app, inside the run folder


def mock_fail_file() -> Path:
    st = load_state()
    return RUNS / st["run_id"] / MOCK_FAIL_NAME


def newest_run_row(answered: bool | None = None) -> dict:
    """The newest query_log row's id, whether it has an answer, and filters.run (#277)."""
    where = "" if answered is None else ("WHERE answer IS NOT NULL" if answered else "WHERE answer IS NULL")
    raw = psql(VERIFY_DB, "SELECT json_build_object('id', query_id, 'answered', answer IS NOT NULL, "
                          f"'run', filters->'run')::text FROM query_log {where} ORDER BY query_id DESC LIMIT 1")
    return json.loads(raw) if raw else {}


def wait_for_row(pred, what: str, timeout_s: float = 15) -> dict:
    """The stopped run's row is written by its worker once it has ended (after the page shows Stopped)."""
    end = time.monotonic() + timeout_s
    row: dict = {}
    while time.monotonic() < end:
        row = newest_run_row()
        if row and pred(row):
            return row
        time.sleep(0.5)
    return row


def feature_ask_stop_retry(page, base, rec, ctx):
    """#277: Stop during the map, Retry after the stop (finished map call reused), Retry after an injected failure."""
    fail = mock_fail_file()
    fail.unlink(missing_ok=True)
    before = newest_run_row().get("id") or 0
    page.goto(base)
    wait_idle(page)
    page.get_by_role("textbox", name="Question").fill(TWO_FIRM_Q)
    page.get_by_role("button", name="Ask").click()
    # The verify app's mock map waits MOCK_DELAY_S x (k + 1) per call: map.a1.MS lands at ~1.5 s, map.a1.RJF at ~3 s.
    page.wait_for_function("() => document.body.innerText.includes('EVIDENCE - ')", timeout=RENDER_TIMEOUT_S * 1000)
    shown = page.locator(".cee-claim", has_text="EVIDENCE - ").count()
    stop = page.get_by_role("button", name="Stop")
    rec.step("Ask the two-firm question; look when the first evidence card lands",
             "a Stop button, at least one evidence card, no answer yet",
             stop.count() == 1 and shown >= 1 and "LLM called:" not in page.locator("body").inner_text(),
             f"Stop buttons={stop.count()}, evidence cards={shown}")
    t0 = time.monotonic()
    stop.click()
    try:
        page.wait_for_function("() => document.body.innerText.includes('Stopped while')", timeout=10000)
    except Exception:   # playwright TimeoutError: reported by the step below
        pass
    took = time.monotonic() - t0
    wait_idle(page)   # the old run's elements leave once the rerun is drawn
    body = page.locator("body").inner_text()
    cards = page.locator(".cee-claim", has_text="EVIDENCE - ").count()
    rec.step("Click Stop during the map (#277)",
             "'Stopped while extracting evidence' within 5 s; the evidence card(s) stay; no answer "
             "('LLM called:'), no 'Answer (in progress', no Stop button",
             "Stopped while extracting evidence" in body and took <= 5 and cards >= 1 and "LLM called:" not in body
             and "Answer (in progress" not in body and page.get_by_role("button", name="Stop").count() == 0,
             f"stopped after {took:.1f} s, evidence cards={cards}, answer shown={'LLM called:' in body}")
    page.wait_for_timeout(5000)
    body = page.locator("body").inner_text()
    later = page.locator(".cee-claim", has_text="EVIDENCE - ").count()
    rec.step("Wait 5 s after the stop", "no new evidence card, still no answer, Retry offered",
             later == cards and "LLM called:" not in body and page.get_by_role("button", name="Retry").count() == 1,
             f"evidence cards {cards} -> {later}, answer shown={'LLM called:' in body}")
    row = wait_for_row(lambda r: r["id"] > before and not r["answered"], "the stopped row")
    run = row.get("run") or {}
    recs = {(x["id"], x["status"]) for x in run.get("records", [])}
    n_ok = sum(st == "ok" for _, st in recs)
    n_cut = sum(st == "cancelled" for _, st in recs)
    rec.step("Read the newest query_log row (side effect)",
             "answer NULL; filters.run: status stopped, reason stop (the Stop button, not 'page'), stage extract, "
             "map.a1.MS ok, map.a1.RJF cancelled (and map.research, queued behind it), stop_s <= 5",
             row.get("answered") is False and run.get("status") == "stopped" and run.get("stage") == "extract"
             and run.get("reason") == "stop"
             and ("map.a1.MS", "ok") in recs and ("map.a1.RJF", "cancelled") in recs
             and run.get("stop_s") is not None and run["stop_s"] <= 5,   # 0.0 is a valid (fast) stop
             f"row {row.get('id')}: status={run.get('status')}, reason={run.get('reason')}, stage={run.get('stage')}, "
             f"records={sorted(recs)}, "
             f"stop_s={run.get('stop_s')}")
    stopped_id = row.get("id")
    page.get_by_role("button", name="Retry").click()
    wait_for_text(page, ["LLM called:"], "the answer after Retry")
    row = newest_run_row(answered=True)
    run = row.get("run") or {}
    rec.step("Click Retry (#277)",
             f"the answer shows; the newest row: attempt 2, retry_of the stopped row, map reused {n_ok} (the ok calls), "
             f"made map {n_cut} (the cancelled ones) + reduce 1",
             row.get("id", 0) > (stopped_id or 0) and run.get("attempt") == 2 and run.get("retry_of") == stopped_id
             and run.get("reused") == {"map": n_ok} and run.get("made") == {"map": n_cut, "reduce": 1},
             f"row {row.get('id')}: attempt={run.get('attempt')}, retry_of={run.get('retry_of')}, "
             f"reused={run.get('reused')}, made={run.get('made')}")
    # Retry after an injected failure: the mock reduce fails while MOCK_FAIL_FILE names it
    fail.write_text("reduce", encoding="utf-8")
    try:
        page.goto(base)
        wait_idle(page)
        page.get_by_role("textbox", name="Question").fill(TWO_FIRM_Q)
        page.get_by_role("button", name="Ask").click()
        wait_for_text(page, ["The answer could not be built"], "the injected failure")
        body = page.locator("body").inner_text()
        rec.step("Ask again with an injected reduce failure (MOCK_FAIL_FILE)",
                 "'The answer could not be built ... injected reduce failure', a Retry button, no answer",
                 "injected reduce failure" in body and "LLM called:" not in body
                 and page.get_by_role("button", name="Retry").count() == 1,
                 next((l for l in body.splitlines() if "could not be built" in l), "")[:200])
        failed = wait_for_row(lambda r: not r["answered"] and (r.get("run") or {}).get("status") == "failed",
                              "the failed row")
    finally:
        fail.unlink(missing_ok=True)
    page.get_by_role("button", name="Retry").click()
    wait_for_text(page, ["LLM called:"], "the answer after Retry")
    row = newest_run_row(answered=True)
    run = row.get("run") or {}
    frun = failed.get("run") or {}
    rec.step("Remove the injected failure; click Retry (#277)",
             f"the answer shows; failed row: stage synthesize; newest row: every map call reused ({n_ok + n_cut}), "
             "made reduce 1",
             frun.get("stage") == "synthesize" and run.get("retry_of") == failed.get("id")
             and run.get("reused") == {"map": n_ok + n_cut} and run.get("made") == {"reduce": 1},
             f"failed row {failed.get('id')} stage={frun.get('stage')}; row {row.get('id')}: "
             f"retry_of={run.get('retry_of')}, reused={run.get('reused')}, made={run.get('made')}")


DRIVERS = {"ask-answer": feature_ask_answer, "ask-progress": feature_ask_progress,
           "open-citation": feature_open_citation,
           "gap-path": feature_gap_path, "invalid-chunk": feature_invalid_chunk,
           "download-document": feature_download_document, "coverage": feature_coverage,
           "filters": feature_filters, "feedback": feature_feedback,
           "architecture-page": feature_architecture_page, "ask-stop-retry": feature_ask_stop_retry}


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

def set_source_db(name: str) -> None:
    global SOURCE_DB, VERIFY_DB
    SOURCE_DB, VERIFY_DB = name, ("cee_verify" if name == "cee" else f"{name}_verify")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["doctor", "launch", "drive", "cleanup", "run", "shots"])
    ap.add_argument("features", nargs="*", help=f"default: all of {', '.join(FEATURES)}")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--source-db", default=SOURCE_DB,
                    help=f"database to copy (default {SOURCE_DB}); the copy is <source-db>_verify")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", a.source_db):
        ap.error("--source-db: lower-case letters, digits and _ only")
    set_source_db(a.source_db)
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
        if a.command == "shots":
            return 0 if shots() else 1
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
