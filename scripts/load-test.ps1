param(
    [Parameter(Mandatory=$true)][string]$BaseUrl,
    [ValidateRange(5,300)][int]$DurationSeconds = 120,
    [ValidateRange(1,32)][int]$Concurrency = 8,
    [ValidateRange(1,200)][int]$RequestsPerSecond = 60
)
$ErrorActionPreference = 'Stop'
& python (Join-Path $PSScriptRoot 'load-test.py') --base-url $BaseUrl --duration $DurationSeconds --concurrency $Concurrency --rps $RequestsPerSecond
if ($LASTEXITCODE -ne 0) { throw "Read-only load test failed with exit code $LASTEXITCODE" }
