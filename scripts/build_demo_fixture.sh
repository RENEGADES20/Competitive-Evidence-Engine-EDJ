#!/usr/bin/env bash
# Build the demo-mode fixture (#299). Wrapper for scripts/build_demo_fixture.py; arguments pass through.
# Default: mock answers, 0 model calls. A real run names its call cap. Windows twin: scripts/build_demo_fixture.ps1.
#
#   bash scripts/build_demo_fixture.sh --check
#   bash scripts/build_demo_fixture.sh --provider anthropic --max-calls 30
. "$(dirname "$0")/_common.sh"
exec "$PYTHON" "$(native_path "$REPO_ROOT/scripts/build_demo_fixture.py")" "$@"
