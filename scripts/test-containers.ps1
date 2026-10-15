param([switch]$SkipBrowser)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Native.ps1')
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$launcher = Join-Path (Split-Path $repositoryRoot -Parent) 'Enter-Project.ps1'
if (Test-Path -LiteralPath $launcher) { . $launcher }
$project = 'stockflow-container-qa'
$envFile = Join-Path $repositoryRoot '.logs/container-qa.env'
$composeArguments = @('compose', '-p', $project, '--env-file', $envFile, '-f', 'docker-compose.yml')
$oldTestUrl = $env:STOCKFLOW_E2E_URL
$oldBrowsersPath = $env:PLAYWRIGHT_BROWSERS_PATH
$oldEvidence = $env:STOCKFLOW_EVIDENCE_PREFIX
# Process variables take precedence over --env-file. Clear and restore these
# names so a user's development configuration cannot redirect isolated QA.
$qaSettings = @{
    POSTGRES_DB = 'stockflow_container_test'; POSTGRES_USER = 'stockflow_container_test'
    POSTGRES_PASSWORD = 'stockflow_container_test_only'; POSTGRES_PORT = '5434'
    BACKEND_PORT = '8002'; FRONTEND_PORT = '3001'; API_UPSTREAM = 'backend:8000'; NGINX_RESOLVER = '127.0.0.11'
}
$previousSettings = @{}
$started = $false
Push-Location $repositoryRoot
try {
    if (Get-NetTCPConnection -State Listen -LocalPort 3001,8002,5434 -ErrorAction SilentlyContinue) {
        throw 'Container QA ports 3001/8002/5434 are occupied. Stop the previous QA stack first.'
    }
    $existingVolume = & docker volume ls --filter "label=com.docker.compose.project=$project" --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Docker volumes.' }
    if ($existingVolume) { throw 'Existing container QA volume found. Inspect it before explicitly removing the old disposable QA project.' }
    New-Item -ItemType Directory -Force -Path (Split-Path $envFile -Parent) | Out-Null
    $qaSettings.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" } | Set-Content -LiteralPath $envFile -Encoding ASCII
    foreach ($key in $qaSettings.Keys) {
        $previousSettings[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $null, 'Process')
    }
    Invoke-CheckedNative 'docker' ($composeArguments + @('config', '--quiet'))
    $started = $true
    Invoke-CheckedNative 'docker' ($composeArguments + @('up', '-d', '--build', '--wait', '--wait-timeout', '120'))
    Invoke-CheckedNative 'docker' ($composeArguments + @('ps', '--all'))
    Invoke-CheckedNative 'docker' ($composeArguments + @('logs', '--no-color', 'migrate'))
    $services = & docker @composeArguments ps --all --format json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect QA services.' }
    $migration = @($services | Where-Object { $_.Service -eq 'migrate' })
    if ($migration.Count -ne 1 -or $migration[0].ExitCode -ne 0) { throw 'Migration did not exit successfully.' }
    foreach ($service in @('backend','frontend')) {
        $container = @($services | Where-Object { $_.Service -eq $service })[0]
        if ($container.Health -ne 'healthy') { throw "$service is not healthy." }
        $details = (& docker inspect $container.ID | ConvertFrom-Json)[0]
        if ($details.Config.User -match '^($|0(:|$)|root(:|$))') { throw "$service runs as root." }
        if (-not $details.HostConfig.ReadonlyRootfs) { throw "$service root filesystem is writable." }
        Write-Output "PASS: $service healthy; user $($details.Config.User); read-only root filesystem."
        Invoke-CheckedNative 'docker' ($composeArguments + @('exec','-T',$service,'id'))
    }
    Invoke-CheckedNative 'docker' ($composeArguments + @('exec','-T','backend','python','-m','pip','check'))
    Invoke-CheckedNative 'docker' ($composeArguments + @('exec','-T','backend','python','-m','alembic','check'))
    Invoke-CheckedNative 'docker' ($composeArguments + @('exec','-T','frontend','nginx','-t'))
    Invoke-CheckedNative 'node.exe' @('scripts/verify-containers.mjs','before')
    # Replace only the backend; Nginx must recover without being restarted.
    $frontendBefore = (& docker @composeArguments ps --quiet frontend).Trim()
    Invoke-CheckedNative 'docker' ($composeArguments + @('up','-d','--no-deps','--force-recreate','--wait','--wait-timeout','120','backend'))
    $recovered = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:3001/api/dashboard' -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $recovered = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $recovered) { throw 'Nginx did not recover after backend replacement.' }
    $frontendAfter = (& docker @composeArguments ps --quiet frontend).Trim()
    if ($frontendBefore -ne $frontendAfter) { throw 'Frontend was unexpectedly replaced.' }
    Write-Output 'PASS: Nginx API proxy recovered after backend replacement; frontend container unchanged.'
    if (-not $SkipBrowser) {
        $env:STOCKFLOW_E2E_URL = 'http://127.0.0.1:3001'
        $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $repositoryRoot '.playwright-browsers'
        $env:STOCKFLOW_EVIDENCE_PREFIX = 'container'
        Set-Location (Join-Path $repositoryRoot 'frontend')
        Invoke-CheckedNative 'npm.cmd' @('run','test:e2e')
        Set-Location $repositoryRoot
    }
    # Preserve this project's named volume for the actual persistence check.
    Invoke-CheckedNative 'docker' ($composeArguments + @('down'))
    Invoke-CheckedNative 'docker' ($composeArguments + @('up','-d','--wait','--wait-timeout','120'))
    Invoke-CheckedNative 'node.exe' @('scripts/verify-containers.mjs','after')
    Invoke-CheckedNative 'docker' ($composeArguments + @('logs','--no-color','--tail','12','migrate','backend','frontend'))
    Write-Output 'All container verification checks passed.'
} finally {
    Set-Location $repositoryRoot
    try {
        # Only this explicitly named, disposable QA project's volume is removed.
        # The development project stockflow and its inventory are never targeted.
        if ($started) { Invoke-CheckedNative 'docker' ($composeArguments + @('down','--volumes')) }
    } finally {
        foreach ($key in $previousSettings.Keys) { [Environment]::SetEnvironmentVariable($key, $previousSettings[$key], 'Process') }
        $env:STOCKFLOW_E2E_URL = $oldTestUrl
        $env:PLAYWRIGHT_BROWSERS_PATH = $oldBrowsersPath
        $env:STOCKFLOW_EVIDENCE_PREFIX = $oldEvidence
        Pop-Location
    }
}
