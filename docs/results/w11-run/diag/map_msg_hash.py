"""#250 (plans/0250-final-runs.md, conditions C1-C3): 0-call diagnostic. Runs a worktree's own
`scripts/eval_run.py` with `--max-calls 0` and logs, for every map / remap call the run serves (a reused
record or a call refused at the cap), the record file name and sha256 of what that call sends: the rendered
`extract_message`, the system prompt, the extraction schema and the whole provider request.

It only observes: it wraps the `call` that `RealRunner.map` hands to `extract.run_map` and remembers each
spec's cache key through `eval_run.map_cache_key`. It never builds a client and refuses any `--max-calls`
other than 0. It aborts unless `eval_run` and `cee.answer.extract` are imported from the given worktree.

    python map_msg_hash.py --wt <worktree> --tsv <out.tsv> [--provider deepseek] -- <eval_run.py args>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    argv = sys.argv[1:]
    if "--" not in argv:
        print("usage: map_msg_hash.py --wt <worktree> --tsv <file> [--provider P] -- <eval_run args>")
        return 2
    cut = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--wt", required=True, type=Path)
    ap.add_argument("--tsv", required=True, type=Path)
    ap.add_argument("--provider", default="deepseek")
    args = ap.parse_args(argv[:cut])
    run_args = argv[cut + 1:]
    wt = args.wt.resolve()

    # C1 / round-2 nb 6: a hard refusal of anything but --max-calls 0, and no key in the process
    caps = [run_args[i + 1] for i, a in enumerate(run_args[:-1]) if a == "--max-calls"]
    caps += [a.split("=", 1)[1] for a in run_args if a.startswith("--max-calls=")]
    if caps != ["0"]:
        print(f"refused: map_msg_hash runs only with exactly one --max-calls 0 (got {caps})")
        return 3
    for k in ("DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        os.environ[k] = ""
    if (wt / ".env").exists():
        print(f"refused: {wt / '.env'} exists")
        return 3

    # C1: the worktree's own code first, eval_run before any cee import
    for p in (wt / "src", wt / "scripts"):
        sys.path.insert(0, str(p))
    os.chdir(wt)
    import eval_run  # noqa: E402  (from <wt>/scripts)
    from cee.answer import extract  # noqa: E402

    head = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    files = {"eval_run": Path(eval_run.__file__).resolve(), "extract": Path(extract.__file__).resolve()}
    for name, f in files.items():
        if wt not in f.parents:
            print(f"abort: {name} imported from {f}, not under {wt}")
            return 3

    keys: dict[int, str] = {}
    rows: list[list[str]] = []
    orig_key = eval_run.map_cache_key

    def map_cache_key(q, snapshot, provider, model, max_tokens, request, spec, *a, **kw):
        key = orig_key(q, snapshot, provider, model, max_tokens, request, spec, *a, **kw)
        keys[id(spec)] = f"{q['id']}-{spec.id}-{key}.json"
        return key

    eval_run.map_cache_key = map_cache_key
    builder = getattr(extract, f"{args.provider}_extract_request")
    orig_run_map = extract.run_map

    def log(spec, question, win, firms, served: str):
        msg = extract.extract_message(question, spec, win, firms)
        req = builder(question, spec, win, firms)
        rows.append([keys.get(id(spec), f"?-{spec.id}"), spec.id, str(spec.round), served, sha(msg),
                     sha(extract.system_prompt(spec.research)),
                     sha(json.dumps(extract.extraction_schema(spec, strict=True), sort_keys=True, default=str)),
                     sha(json.dumps(req, sort_keys=True, default=str))])

    def run_map(q, plan, hits, provider=None, call=None, *a, allow=None, **kw):
        if call is None:
            return orig_run_map(q, plan, hits, provider, call, *a, allow=allow, **kw)

        def wrapped_call(spec, question, win, firms):
            r = call(spec, question, win, firms)
            log(spec, question, win, firms, "reused" if getattr(r, "cached", False) else "new")
            return r

        def wrapped_allow(spec):
            ok = allow(spec) if allow else True
            if ok is False:   # refused at the cap: a call the paid run would make (never a reuse)
                rows.append([keys.get(id(spec), f"?-{spec.id}"), spec.id, str(spec.round), "capped", "", "", "", ""])
            return ok

        return orig_run_map(q, plan, hits, provider, wrapped_call, *a, allow=wrapped_allow, **kw)

    extract.run_map = run_map

    code = eval_run.main(run_args)
    args.tsv.parent.mkdir(parents=True, exist_ok=True)
    with args.tsv.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# worktree\t{wt}\n# head\t{head}\n# eval_run\t{files['eval_run']}\n# extract\t{files['extract']}\n")
        fh.write(f"# provider\t{args.provider}\n# args\t{' '.join(run_args)}\n")
        fh.write("file\tcall_id\tround\tserved\tsha_message\tsha_system\tsha_schema\tsha_request\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    print(f"map_msg_hash: {len(rows)} map / remap rows -> {args.tsv} (head {head[:7]})")
    return code or 0


if __name__ == "__main__":
    sys.exit(main())
