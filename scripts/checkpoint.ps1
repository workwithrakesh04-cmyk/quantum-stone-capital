# checkpoint.ps1 - Full checkpoint: log, refresh, test, commit, push
# Usage: .\scripts\checkpoint.ps1 -Label "Phase 3 - step 5"

param(
    [Parameter(Mandatory=$true)]
    [string]$Label,

    [string]$CommitMessage = ""
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

Write-Host ""
Write-Host "=== CHECKPOINT: $Label ===" -ForegroundColor Cyan

# 1. Log the checkpoint
Write-Host "[1/6] Logging checkpoint..." -ForegroundColor Yellow
$logPath = "docs/STEP_LOG.md"
$content = Get-Content $logPath -Raw
$matches = [regex]::Matches($content, "\[Step (\d+)\]")
$maxStep = 0
foreach ($m in $matches) {
    $n = [int]$m.Groups[1].Value
    if ($n -gt $maxStep) { $maxStep = $n }
}
$nextStep = $maxStep + 1
$stepStr = "{0:D3}" -f $nextStep
$checkpointMsg = "`n### [CHECKPOINT] " + $Label + "`n- [$timestamp] [Step " + $stepStr + "] Checkpoint: " + $Label
Add-Content -Path $logPath -Value $checkpointMsg -Encoding utf8

# 2. Refresh FILE_TREE.md
Write-Host "[2/6] Refreshing FILE_TREE.md..." -ForegroundColor Yellow
python scripts/update_file_tree.py

# 3. Run tests
Write-Host "[3/6] Running tests..." -ForegroundColor Yellow
$testOutput = pytest tests/ -q 2>&1 | Out-String
Write-Host $testOutput

$testPassMatch = [regex]::Match($testOutput, "(\d+) passed")
$testCount = if ($testPassMatch.Success) { $testPassMatch.Groups[1].Value } else { "?" }

# 4. Update PROJECT_STATE.md
Write-Host "[4/6] Updating PROJECT_STATE.md..." -ForegroundColor Yellow
$lastCommit = git log --oneline -1
$branch = git rev-parse --abbrev-ref HEAD

$stateLines = @(
    "# PROJECT STATE - Quantum Stone Capital",
    "",
    "**Last updated:** $timestamp",
    "**Repo:** https://github.com/workwithrakesh04-cmyk/quantum-stone-capital",
    "**Local:** E:\quantum-stone-capital",
    "**Branch:** $branch",
    "",
    "## Current Snapshot",
    "- **Last commit:** $lastCommit",
    "- **Tests passing:** $testCount",
    "- **Last checkpoint:** $Label",
    "",
    "## Quick Resume",
    "- docs/RESUME_PROMPT.md",
    "- docs/PHASE_LOG.md",
    "- docs/STEP_LOG.md",
    "- docs/FILE_TREE.md",
    "",
    "## Resume Commands",
    "    cd E:\quantum-stone-capital",
    "    .\venv\Scripts\Activate.ps1",
    "    pytest tests/ -v",
    "    git log --oneline",
    "    git ls-files",
    ""
)
Set-Content -Path "PROJECT_STATE.md" -Value $stateLines -Encoding utf8

# 5. Git add + commit
Write-Host "[5/6] Committing..." -ForegroundColor Yellow
git add .
$msg = if ($CommitMessage) { $CommitMessage } else { "checkpoint: $Label" }
git commit -m $msg

# 6. Push
Write-Host "[6/6] Pushing..." -ForegroundColor Yellow
git push

Write-Host ""
Write-Host "Checkpoint complete: $Label" -ForegroundColor Green
$summary = "Step: " + $stepStr + " | Tests: " + $testCount
Write-Host $summary -ForegroundColor Green
git log --oneline -1
