[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CasesCsv
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $CasesCsv -PathType Leaf)) {
    throw "cases.csv not found: $CasesCsv"
}

$rows = @(Import-Csv -LiteralPath $CasesCsv)
if ($rows.Count -lt 1 -or $rows.Count -gt 20) {
    throw "cases.csv must contain 1..20 rows; found $($rows.Count)"
}

$headers = @($rows[0].PSObject.Properties.Name)
foreach ($required in @('case_id', 'source_nodeid')) {
    if ($headers -notcontains $required) {
        throw "Missing required column: $required"
    }
}

foreach ($required in @('case_id', 'source_nodeid')) {
    $values = @($rows | ForEach-Object { [string]$_.$required })
    if (@($values | Where-Object { [string]::IsNullOrWhiteSpace($_) }).Count -gt 0) {
        throw "Column $required contains empty values"
    }
    $duplicates = @($values | Group-Object | Where-Object Count -gt 1)
    if ($duplicates.Count -gt 0) {
        throw "Column $required contains duplicates: $($duplicates.Name -join ', ')"
    }
}

[PSCustomObject]@{
    valid = $true
    case_count = $rows.Count
    case_ids = @($rows.case_id)
    path = (Resolve-Path -LiteralPath $CasesCsv).Path
}

