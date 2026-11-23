"""#283: sha256 of the map requests and map cache keys of a fixed question, for tests/test_prefix_cache.py
(off == main). Run on a worktree root: PYTHONPATH="<wt>/src;<wt>" python golden.py (0 calls)."""
import hashlib, json, os, sys
os.environ.update({"LLM_PROVIDER": "deepseek"})
for v in ("MAP_PREFIX", "MAP_PREFIX_TOKENS", "DEEPSEEK_EFFORT_MAP", "DEEPSEEK_STREAM"):
    os.environ.pop(v, None)
from cee.answer import extract, llm
from cee.retrieve.planner import Aspect, Plan, SubQuestion
from tests.test_extract import Q, hit
A = [Aspect(f"a{n}", f"Aspect number {n} of the firm.") for n in (1, 2, 3)]
firms = ("EDJ", "MS")
plan = Plan(aspects=A, subquestions=[SubQuestion(f"{a.id}.{f}", f, a, "named") for f in firms for a in A])
plan.pools = {"a2.EDJ": {"EDJ-10K-2025#0"}}
hits = [hit(f"{f}-10K-2025#{n}", entity=f, part=f"{a.id}.{f}") for f in firms for n, a in enumerate(A)]
hits.append(hit("R-1#1", entity=None, part="research"))
fs, _ = extract.map_specs(Q, plan, hits)
specs, _ = extract.fan_out(fs, Q.question, None, None, 60000)
reqs = [[extract.deepseek_extract_request(Q.question, s), extract.anthropic_extract_request(Q.question, s),
         extract.openai_extract_request(Q.question, s)] for s in specs]
from scripts import eval_run as er
from cee.answer import runcache
keys = [[er.map_cache_key({"id": "Q1", "text": Q.question}, "snap", "deepseek", "m", 1, llm.request_version("deepseek", "map"), s),
         runcache.map_key(Q.question, s, "deepseek")] for s in specs]
blob = json.dumps([reqs, keys], sort_keys=True)
print(hashlib.sha256(blob.encode()).hexdigest(), llm.request_version("deepseek", "map"), extract.EXTRACT_VERSION,
      [s.id for s in specs])
