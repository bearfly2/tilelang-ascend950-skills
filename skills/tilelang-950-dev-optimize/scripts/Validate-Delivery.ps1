[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TaskRoot
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$required = @(
    'TASK.md',
    'case_selection/cases_candidates.csv',
    'case_selection/cases.csv',
    'design/DESIGN.md',
    'baseline/precision.csv',
    'baseline/profile/manifest.json',
    'baseline/profile/summary.csv',
    'analysis/BOTTLENECKS.md',
    'analysis/CANDIDATES.md',
    'FINAL_REPORT.md'
)

foreach ($relative in $required) {
    $path = Join-Path $TaskRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Delivery artifact missing: $relative" }
}

$casesCsv = Join-Path $TaskRoot 'case_selection/cases.csv'
$baselineProfile = Join-Path $TaskRoot 'baseline/profile'
$cases = & (Join-Path $scriptDir 'Validate-Cases.ps1') -CasesCsv $casesCsv
$profile = & (Join-Path $scriptDir 'Validate-ProfileArtifacts.ps1') -RunDir $baselineProfile -CasesCsv $casesCsv

$iterationRoot = Join-Path $TaskRoot 'iterations'
if (-not (Test-Path -LiteralPath $iterationRoot -PathType Container)) { throw 'iterations directory missing' }
$iterations = @(Get-ChildItem -LiteralPath $iterationRoot -Directory)
foreach ($iteration in $iterations) {
    foreach ($relative in @('hypothesis.md', 'changes.patch', 'precision.csv', 'profile/manifest.json', 'profile/summary.csv', 'comparison.json', 'decision.md')) {
        if (-not (Test-Path -LiteralPath (Join-Path $iteration.FullName $relative) -PathType Leaf)) {
            throw "Iteration $($iteration.Name) missing artifact: $relative"
        }
    }
    & (Join-Path $scriptDir 'Validate-ProfileArtifacts.ps1') -RunDir (Join-Path $iteration.FullName 'profile') -CasesCsv $casesCsv | Out-Null
}

[PSCustomObject]@{
    valid = $true
    case_count = $cases.case_count
    baseline_run_id = $profile.run_id
    iteration_count = $iterations.Count
    task_root = (Resolve-Path -LiteralPath $TaskRoot).Path
}

