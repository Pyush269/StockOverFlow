function Invoke-CheckedNative {
    param([string]$Executable, [string[]]$Arguments)
    # Windows PowerShell 5 treats redirected native stderr (including Docker's
    # successful progress messages) as ErrorRecords. Normalize that output and
    # use the actual process exit code to determine success.
    $ErrorActionPreference = 'Continue'
    & $Executable @Arguments 2>&1 | ForEach-Object { Write-Output $_.ToString() }
    $nativeExitCode = $LASTEXITCODE
    if ($nativeExitCode -ne 0) { throw "Command failed with exit code ${nativeExitCode}: $Executable" }
}
