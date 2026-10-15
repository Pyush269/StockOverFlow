param([int]$Port = 5173)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Native.ps1')
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$launcher = Join-Path (Split-Path $repositoryRoot -Parent) 'Enter-Project.ps1'
if (Test-Path -LiteralPath $launcher) { . $launcher }
$frontendRoot = Join-Path $repositoryRoot 'frontend'
if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot 'node_modules\vite\bin\vite.js'))) {
    throw 'Run npm.cmd ci in frontend/ first; see README.md.'
}
$nodeExecutable = (Get-Command node.exe -ErrorAction Stop).Source
Push-Location $frontendRoot
try {
    Invoke-CheckedNative $nodeExecutable @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', $Port.ToString(), '--strictPort')
} finally { Pop-Location }
