# Local quality gate. Run before every commit. No CI runs in the cloud.
# Each step must exit 0 on its own.
$ErrorActionPreference = "Stop"
# Work from the repository root whatever the caller's current folder is.
Set-Location (Split-Path -Parent $PSScriptRoot)

ruff format --check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
mypy --strict src
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
pytest
exit $LASTEXITCODE
