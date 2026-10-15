$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Native.ps1')
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$launcher = Join-Path (Split-Path $repositoryRoot -Parent) 'Enter-Project.ps1'
if (Test-Path -LiteralPath $launcher) { . $launcher }
$backendRoot = Join-Path $repositoryRoot 'backend'
$pythonExecutable = Join-Path $backendRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) { throw 'Install the backend development environment first; see README.md.' }
$previousTestUrl = $env:TEST_DATABASE_URL
Push-Location $repositoryRoot
try {
    Invoke-CheckedNative 'docker' @('compose', '-f', 'compose.test.yml', 'up', '-d', '--wait')
    $env:TEST_DATABASE_URL = 'postgresql+psycopg://stockflow_test:stockflow_test_only@127.0.0.1:5433/stockflow_test'
    Set-Location $backendRoot
    Invoke-CheckedNative $pythonExecutable @('-m', 'pytest', '-v')
} finally {
    Set-Location $repositoryRoot
    try {
        Invoke-CheckedNative 'docker' @('compose', '-f', 'compose.test.yml', 'down')
    } finally {
        $env:TEST_DATABASE_URL = $previousTestUrl
        Pop-Location
    }
}
