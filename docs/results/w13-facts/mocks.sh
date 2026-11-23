#!/usr/bin/env bash
# #285: the four mock runs (0 calls): clean main cda5ebf vs the branch, rule plans and #272 plans, FACTS unset (off).
S=/d/ALLPROJECTS/EDJ/wt-285/docs/results/w12-latency/run-mock.sh
export EV=/d/ALLPROJECTS/EDJ/cache/ev285 PY=/d/ALLPROJECTS/EDJ/repo/.venv/Scripts/python.exe
unset FACTS
( WT=/d/ALLPROJECTS/EDJ/wt-285main OUT=mock-main-rule bash $S ) &
( WT=/d/ALLPROJECTS/EDJ/wt-285 OUT=mock-new-rule bash $S ) &
wait
( WT=/d/ALLPROJECTS/EDJ/wt-285main OUT=mock-main-p272 REUSE_PLANS=1 CACHE=/d/ALLPROJECTS/EDJ/cache/ev284/plans-272 PLAN_VERSION=ds-strict-2-plan-off-c8000-s1 bash $S ) &
( WT=/d/ALLPROJECTS/EDJ/wt-285 OUT=mock-new-p272 REUSE_PLANS=1 CACHE=/d/ALLPROJECTS/EDJ/cache/ev284/plans-272 PLAN_VERSION=ds-strict-2-plan-off-c8000-s1 bash $S ) &
wait
