# Connect this package to GitHub (owner-approved: the remote may be replaced).
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File scripts\connect_github.ps1
# Requirements: git installed, authenticated (Git Credential Manager or a PAT).
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$remoteUrl = 'https://github.com/frogrest/CarlBot.git'

Write-Host "Repo root: $repoRoot"

# 1) Init if this is not yet a repo
if (-not (Test-Path (Join-Path $repoRoot '.git'))) {
    git init -b main
    if ($LASTEXITCODE -ne 0) { git init; git checkout -b main }
}

# 2) Stage everything (respects .gitignore)
git add -A
git status --short

# 3) First commit if none exists
$head = git rev-parse HEAD 2>$null
if (-not $head) {
    git -c core.autocrlf=false commit -m "AI helpdesk lab: services, upgraded prompts, frontend build prompt, docs"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Commit failed. Set identity first: git config user.name '...'; git config user.email '...'"
        exit 1
    }
}

# 4) Attach remote (replace if present)
$existing = git remote get-url origin 2>$null
if ($existing) { git remote set-url origin $remoteUrl } else { git remote add origin $remoteUrl }

# 5) Check what the remote currently holds (owner said it may be replaced)
git ls-remote --heads origin
if ($LASTEXITCODE -ne 0) {
    Write-Error "Cannot reach remote. Check network/auth (Git Credential Manager or PAT)."
    exit 1
}

# 6) Push (force allowed by repo owner) and set upstream
git branch -M main
git push --force -u origin main
if ($LASTEXITCODE -ne 0) { Write-Error "Push failed."; exit 1 }

Write-Host "DONE. Verify: git ls-remote --heads origin"
