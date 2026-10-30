[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BaselineSummary,
    [Parameter(Mandatory = $true)]
    [string]$CandidateSummary,
    [Parameter(Mandatory = $true)]
    [string]$OutputJson
)

$ErrorActionPreference = 'Stop'
$baseline = @(Import-Csv -LiteralPath $BaselineSummary)
$candidate = @(Import-Csv -LiteralPath $CandidateSummary)
if ($baseline.Count -eq 0 -or $candidate.Count -eq 0) { throw 'Profile summary is empty' }

$baselineById = @{}
foreach ($row in $baseline) {
    if ($baselineById.ContainsKey($row.case_id)) { throw "Duplicate baseline case_id: $($row.case_id)" }
    $baselineById[$row.case_id] = $row
}
$candidateById = @{}
foreach ($row in $candidate) {
    if ($candidateById.ContainsKey($row.case_id)) { throw "Duplicate candidate case_id: $($row.case_id)" }
    $candidateById[$row.case_id] = $row
}

if (Compare-Object @($baselineById.Keys | Sort-Object) @($candidateById.Keys | Sort-Object)) {
    throw 'Baseline and candidate case sets differ'
}

$comparisons = @()
$logSpeedups = @()
foreach ($caseId in @($baselineById.Keys | Sort-Object)) {
    $baseUs = [double]$baselineById[$caseId].latency_us
    $candidateUs = [double]$candidateById[$caseId].latency_us
    if ($baseUs -le 0 -or $candidateUs -le 0) { throw "Non-positive latency for case $caseId" }
    $speedup = $baseUs / $candidateUs
    $improvement = (($baseUs - $candidateUs) / $baseUs) * 100.0
    $logSpeedups += [math]::Log($speedup)
    $comparisons += [PSCustomObject]@{
        case_id = $caseId
        baseline_us = [math]::Round($baseUs, 6)
        candidate_us = [math]::Round($candidateUs, 6)
        speedup = [math]::Round($speedup, 6)
        improvement_pct = [math]::Round($improvement, 4)
    }
}

$geomean = [math]::Exp((($logSpeedups | Measure-Object -Average).Average))
$worst = $comparisons | Sort-Object improvement_pct | Select-Object -First 1
$result = [ordered]@{
    schema_version = 1
    case_count = $comparisons.Count
    geometric_mean_speedup = [math]::Round($geomean, 6)
    worst_case_id = $worst.case_id
    worst_improvement_pct = $worst.improvement_pct
    cases = $comparisons
}

$parent = Split-Path -Parent $OutputJson
if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutputJson -Encoding utf8
[PSCustomObject]$result

