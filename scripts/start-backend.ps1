param([int]$Port = 8000, [switch]$Reload)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Native.ps1')
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$launcher = Join-Path (Split-Path $repositoryRoot -Parent) 'Enter-Project.ps1'
if (Test-Path -LiteralPath $launcher) { . $launcher }
$backendRoot = Join-Path $repositoryRoot 'backend'
$pythonExecutable = Join-Path $backendRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) { throw 'Create backend/.venv and install requirements-dev.lock.txt first; see README.md.' }
Push-Location $repositoryRoot
try {
    Invoke-CheckedNative 'docker' @('compose', 'up', '-d', '--wait', 'postgres')
    Set-Location $backendRoot
    Invoke-CheckedNative $pythonExecutable @('-m', 'alembic', 'upgrade', 'head')
    $serverArguments = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', $Port.ToString())
    if ($Reload) { $serverArguments += '--reload' }
    Invoke-CheckedNative $pythonExecutable $serverArguments
} finally {
    Pop-Location
}
