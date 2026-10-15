param([switch]$InstallBrowser)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Native.ps1')
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$launcher = Join-Path (Split-Path $repositoryRoot -Parent) 'Enter-Project.ps1'
if (Test-Path -LiteralPath $launcher) { . $launcher }
$backendRoot = Join-Path $repositoryRoot 'backend'
$frontendRoot = Join-Path $repositoryRoot 'frontend'
$pythonExecutable = Join-Path $backendRoot '.venv\Scripts\python.exe'
$nodeExecutable = (Get-Command node.exe -ErrorAction Stop).Source
$logRoot = Join-Path $repositoryRoot '.logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$previousDatabaseUrl = $env:DATABASE_URL
$previousTarget = $env:STOCKFLOW_API_TARGET
$previousTestUrl = $env:STOCKFLOW_E2E_URL
$previousBrowsersPath = $env:PLAYWRIGHT_BROWSERS_PATH
$qaApi = $null
$qaVite = $null
$databaseStarted = $false

function Wait-QAEndpoint([string]$Url) {
    for ($attempt = 0; $attempt -lt 35; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 1
            if ($response.StatusCode -eq 200) { return }
        } catch { Start-Sleep -Milliseconds 250 }
    }
    throw "QA endpoint did not become ready: $Url. Inspect .logs/qa-*.log."
}

function Stop-QAProcess($Process) {
    if ($null -eq $Process -or $Process.HasExited) { return }
    # Only the process trees started by this invocation are stopped.
    $ErrorActionPreference = 'Continue'
    & taskkill.exe /PID $Process.Id /T /F 2>&1 | ForEach-Object { Write-Output $_.ToString() }
}

Push-Location $repositoryRoot
try {
    if (Get-NetTCPConnection -State Listen -LocalPort 8001,5174 -ErrorAction SilentlyContinue) {
        throw 'QA ports 8001/5174 are occupied. Stop the previous QA servers before running this helper.'
    }
    if (-not (Test-Path -LiteralPath $pythonExecutable)) { throw 'Install the backend development environment first.' }
    $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $repositoryRoot '.playwright-browsers'
    Set-Location $frontendRoot
    if ($InstallBrowser) { Invoke-CheckedNative $nodeExecutable @('node_modules/playwright/cli.js', 'install', 'chromium', '--no-shell') }
    Invoke-CheckedNative 'npm.cmd' @('test')
    Invoke-CheckedNative 'npm.cmd' @('run', 'build')
    Set-Location $repositoryRoot
    Invoke-CheckedNative 'docker' @('compose', '-f', 'compose.test.yml', 'up', '-d', '--wait')
    $databaseStarted = $true
    $env:DATABASE_URL = 'postgresql+psycopg://stockflow_test:stockflow_test_only@127.0.0.1:5433/stockflow_test'
    Set-Location $backendRoot
    Invoke-CheckedNative $pythonExecutable @('-m', 'alembic', 'upgrade', 'head')
    $qaApi = Start-Process -FilePath $pythonExecutable -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001') -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'qa-api.stdout.log') -RedirectStandardError (Join-Path $logRoot 'qa-api.stderr.log') -PassThru
    Wait-QAEndpoint 'http://127.0.0.1:8001/ready'
    $env:STOCKFLOW_API_TARGET = 'http://127.0.0.1:8001'
    $qaVite = Start-Process -FilePath $nodeExecutable -ArgumentList @('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5174','--strictPort') -WorkingDirectory $frontendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'qa-frontend.stdout.log') -RedirectStandardError (Join-Path $logRoot 'qa-frontend.stderr.log') -PassThru
    Wait-QAEndpoint 'http://127.0.0.1:5174/api/dashboard'
    $env:STOCKFLOW_E2E_URL = 'http://127.0.0.1:5174'
    Set-Location $frontendRoot
    Invoke-CheckedNative 'npm.cmd' @('run', 'test:e2e')
} finally {
    Stop-QAProcess $qaVite
    Stop-QAProcess $qaApi
    Set-Location $repositoryRoot
    try {
        if ($databaseStarted) { Invoke-CheckedNative 'docker' @('compose', '-f', 'compose.test.yml', 'down') }
    } finally {
        $env:DATABASE_URL = $previousDatabaseUrl
        $env:STOCKFLOW_API_TARGET = $previousTarget
        $env:STOCKFLOW_E2E_URL = $previousTestUrl
        $env:PLAYWRIGHT_BROWSERS_PATH = $previousBrowsersPath
        Pop-Location
    }
}
