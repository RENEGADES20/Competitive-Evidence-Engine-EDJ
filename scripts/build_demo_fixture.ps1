# Build the demo-mode fixture (#299). Wrapper for scripts/build_demo_fixture.py; arguments pass through.
# Default: mock answers, 0 model calls. A real run names its call cap. Mac twin: scripts/build_demo_fixture.sh.
#
#   powershell -ExecutionPolicy Bypass -File scripts\build_demo_fixture.ps1 --check
#   powershell -ExecutionPolicy Bypass -File scripts\build_demo_fixture.ps1 --provider anthropic --max-calls 30
. "$PSScriptRoot\_common.ps1"
& $Python (Join-Path $RepoRoot "scripts\build_demo_fixture.py") @args
exit $LASTEXITCODE
