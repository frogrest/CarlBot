# Phase 0 bootstrap — one command for the next agent or human.
#   powershell -ExecutionPolicy Bypass -File scripts\phase0_bootstrap.ps1
# Does: verify tooling -> install Python via winget if missing -> venv ->
# pip install -> compileall -> pytest -> optional Docker smoke.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

function Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }

# 1) Python present?
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Step "Python not found - installing Python 3.13 via winget"
    winget install --id Python.Python.3.13 -e --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { Write-Error "winget install failed. Install Python manually from python.org (check Add to PATH), then re-run this script."; exit 1 }
    Write-Host "Installed. Close and reopen PowerShell so PATH updates, then re-run this script." -ForegroundColor Yellow
    exit 0
}
python --version

# 2) venv + dependencies (uses .venv python directly - no activation needed)
if (-not (Test-Path '.venv')) { Step "Creating .venv"; python -m venv .venv }
$py = '.\.venv\Scripts\python.exe'
& $py -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit 1 }
& $py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }

# 3) baseline validation
Step "compileall services tests"
& $py -m compileall services tests
if ($LASTEXITCODE -ne 0) { Write-Error "Compile failed - paste the output to the AI agent."; exit 1 }

Step "pytest -q  (expect 20 passed: 2 original + 18 Phase 1)"
& $py -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Error "Tests FAILED - paste the full output to the AI agent for fixes."; exit 1 }

# 4) optional Docker smoke (Phase 1 exit criteria)
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Step "docker compose up --build -d"
    docker compose up --build -d
    docker compose ps
    Write-Host "Smoke: POST /api/simulate/fault rtsp_down on CAM-027, watch http://localhost:8002/api/status" -ForegroundColor Yellow
} else {
    Write-Host "Docker not installed - skipping stack smoke (install later; required before Phase 5)." -ForegroundColor Yellow
}

Write-Host "PHASE 0 DONE - baseline green. Next: Phase 2 (orchestrator) or mark Progress log validated." -ForegroundColor Green
