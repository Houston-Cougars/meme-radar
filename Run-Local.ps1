$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path .venv/Scripts/python.exe)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12+ and try again.' }
    & ./.venv/Scripts/python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
if (!(Test-Path .env)) { Copy-Item .env.example .env }
& ./.venv/Scripts/python.exe run_once.py
if ($LASTEXITCODE -ne 0) { throw 'Run failed; see the output above.' }
