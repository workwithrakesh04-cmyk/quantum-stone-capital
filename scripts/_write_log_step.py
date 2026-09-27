import pathlib

content = '''# log_step.ps1 - Append a single step to docs/STEP_LOG.md
# Usage: .\\scripts\\log_step.ps1 -Message "Created strategy_registry.py"

param(
    [Parameter(Mandatory=$true)]
    [string]$Message
)

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

$logPath = "docs/STEP_LOG.md"
if (-not (Test-Path $logPath)) {
    Write-Host "ERROR: docs/STEP_LOG.md not found." -ForegroundColor Red
    exit 1
}

$content = Get-Content $logPath -Raw
$matches = [regex]::Matches($content, "\\[Step (\\d+)\\]")
$maxStep = 0
foreach ($m in $matches) {
    $n = [int]$m.Groups[1].Value
    if ($n -gt $maxStep) { $maxStep = $n }
}
$nextStep = $maxStep + 1
$stepStr = "{0:D3}" -f $nextStep

$entry = "- [$timestamp] [Step $stepStr] $Message"

Add-Content -Path $logPath -Value $entry -Encoding utf8

$msg = "OK: Logged step " + $stepStr + ": " + $Message
Write-Host $msg -ForegroundColor Green
'''

pathlib.Path("scripts/log_step.ps1").write_text(content, encoding="utf-8")
print("OK: wrote scripts/log_step.ps1")
