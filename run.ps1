# Run the same Linux image and persistent state volume used by the Unix launcher.
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$launchArgs = @($args)
if ($launchArgs.Count -gt 1 -or ($launchArgs.Count -eq 1 -and $launchArgs[0] -notin @('--setup', '--info', '--update', '--help', '-h'))) {
    throw 'Usage: .\run.cmd [--setup | --info | --update]'
}
$option = if ($launchArgs.Count) { $launchArgs[0] } else { '' }
if ($option -in @('--help', '-h')) {
    Write-Output 'Usage: .\run.cmd [--setup | --info | --update]'
    Write-Output 'Requires Docker running with Linux containers.'
    Write-Output 'First run downloads the demo image. --update refreshes it explicitly.'
    exit 0
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Install Docker and start its Linux container engine, then run .\run.cmd again.'
}
try { $engine = & docker info --format '{{.OSType}}' 2>$null }
catch { throw 'Docker is unavailable. Start Docker and check access to its daemon.' }
if ($LASTEXITCODE -ne 0) { throw 'Docker is unavailable. Start Docker and check access to its daemon.' }
if ($engine -ne 'linux') { throw 'Switch Docker to Linux containers, then run .\run.cmd again.' }
$image = if ($env:CONFIDO_IMAGE) { $env:CONFIDO_IMAGE } else { 'ghcr.io/genxnetwork/confidential-ai-example:latest' }
$present = $false
try {
    & docker image inspect $image *> $null
    $present = $LASTEXITCODE -eq 0
} catch { $present = $false }
if ($option -eq '--update' -or -not $present) {
    & docker pull --platform linux/amd64 $image
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if ($option -eq '--setup') {
    Write-Output 'Ready. Start the demo with .\run.cmd'
    exit 0
}
if ($option -in @('--info', '--update')) {
    & docker run --rm --platform linux/amd64 --network none $image python3 -m demo.runtime
    exit $LASTEXITCODE
}
$volume = if ($env:CONFIDO_STATE_VOLUME) { $env:CONFIDO_STATE_VOLUME } else { 'confidential-ai-example-state' }
if ($volume -notmatch '^[a-zA-Z0-9][a-zA-Z0-9_.-]*$') { throw 'Invalid Docker state volume name.' }
$color = if ($env:CONFIDO_COLOR) { $env:CONFIDO_COLOR } else { 'auto' }
$dockerArgs = @('run', '--rm', '--platform', 'linux/amd64', '--interactive')
if (-not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected) { $dockerArgs += '--tty' }
$dockerArgs += @('--publish', '127.0.0.1:8765:8765', '--mount', "type=volume,source=$volume,target=/state", '--env', "CONFIDO_COLOR=$color")
if ($env:CONFIDO_POLICY_DIR) {
    $policies = (Resolve-Path -LiteralPath $env:CONFIDO_POLICY_DIR).ProviderPath
    $dockerArgs += @('--mount', "type=bind,source=$policies,target=/policies,readonly", '--env', 'CONFIDO_POLICY_DIR=/policies')
}
& docker @dockerArgs $image
exit $LASTEXITCODE
