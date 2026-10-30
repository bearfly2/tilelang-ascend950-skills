[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunDir,
    [Parameter(Mandatory = $true)]
    [string]$CasesCsv,
    [ValidateSet('ascendc', 'pto')]
    [string]$Backend = 'ascendc'
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$casesResult = & (Join-Path $scriptDir 'Validate-Cases.ps1') -CasesCsv $CasesCsv

$manifestPath = Join-Path $RunDir 'manifest.json'
$summaryPath = Join-Path $RunDir 'summary.csv'
$rawDir = Join-Path $RunDir 'raw'

foreach ($path in @($manifestPath, $summaryPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required profile artifact missing: $path"
    }
}
if (-not (Test-Path -LiteralPath $rawDir -PathType Container)) {
    throw "Raw profile directory missing: $rawDir"
}
if (@(Get-ChildItem -LiteralPath $rawDir -File -Recurse -ErrorAction Stop).Count -eq 0) {
    throw "Raw profile directory is empty: $rawDir"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$requiredPaths = @(
    'schema_version', 'run_id', 'kind', 'timestamp_utc', 'operator', 'backend',
    'source.operator_repo', 'source.operator_commit', 'source.framework_repo', 'source.framework_commit',
    'device.full_soc', 'device.npu_arch', 'device.device_id',
    'environment.cann', 'environment.tilelang', 'environment.ptoas',
    'measurement.boundary', 'measurement.warmup', 'measurement.repeat',
    'measurement.concurrency', 'measurement.command', 'cases_csv'
)

function Get-NestedValue([object]$Object, [string]$Path) {
    $value = $Object
    foreach ($part in $Path.Split('.')) {
        if ($null -eq $value -or $value.PSObject.Properties.Name -notcontains $part) { return $null }
        $value = $value.$part
    }
    return $value
}

foreach ($path in $requiredPaths) {
    $value = Get-NestedValue $manifest $path
    if ($null -eq $value -or ($value -is [string] -and [string]::IsNullOrWhiteSpace($value))) {
        throw "Manifest field missing or empty: $path"
    }
}

if ([int]$manifest.schema_version -ne 1) { throw 'Unsupported manifest schema_version' }
if ([string]$manifest.backend -ne $Backend) { throw "Expected backend=$Backend; found $($manifest.backend)" }
if ([int]$manifest.device.npu_arch -ne 3510) { throw "Expected npu_arch=3510; found $($manifest.device.npu_arch)" }
if ([string]$manifest.device.full_soc -notmatch '^Ascend950(PR|DT)') {
    throw "Unsupported full_soc for this workflow: $($manifest.device.full_soc)"
}
if ([int]$manifest.measurement.warmup -lt 0 -or [int]$manifest.measurement.repeat -lt 1 -or [int]$manifest.measurement.concurrency -lt 1) {
    throw 'Invalid warmup/repeat/concurrency values'
}

$summary = @(Import-Csv -LiteralPath $summaryPath)
if ($summary.Count -eq 0) { throw 'summary.csv is empty' }
$summaryHeaders = @($summary[0].PSObject.Properties.Name)
foreach ($required in @('case_id', 'kernel_name', 'latency_us', 'status')) {
    if ($summaryHeaders -notcontains $required) { throw "summary.csv missing column: $required" }
}

$caseIds = @($casesResult.case_ids | Sort-Object)
$summaryIds = @($summary.case_id | Sort-Object)
if (Compare-Object $caseIds $summaryIds) {
    throw 'summary.csv case IDs do not exactly match cases.csv'
}
foreach ($row in $summary) {
    if ([string]$row.status -ne 'pass') { throw "Case $($row.case_id) does not have status=pass" }
    if ([string]::IsNullOrWhiteSpace([string]$row.kernel_name)) { throw "Case $($row.case_id) has no kernel_name" }
    $latency = 0.0
    if (-not [double]::TryParse([string]$row.latency_us, [ref]$latency) -or $latency -le 0) {
        throw "Case $($row.case_id) has invalid latency_us: $($row.latency_us)"
    }
}

[PSCustomObject]@{
    valid = $true
    run_id = $manifest.run_id
    kind = $manifest.kind
    case_count = $summary.Count
    full_soc = $manifest.device.full_soc
    npu_arch = $manifest.device.npu_arch
    run_dir = (Resolve-Path -LiteralPath $RunDir).Path
}
