Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location (Join-Path $projectRoot 'jarvis-server')
try {
    $runtimeConfig = python -c "from app.config import get_server_runtime_config_json; print(get_server_runtime_config_json())" | ConvertFrom-Json
}
finally {
    Pop-Location
}

$serverHost = [string]$runtimeConfig.host
$serverPort = [int]$runtimeConfig.port
$waitTargets = @(
    "tcp:$serverHost`:$serverPort",
    'file:dist-electron/main.js'
)

if ($env:JARVIS_SERVER_DRY_RUN -eq '1') {
    Write-Output "WAIT_ON=$($waitTargets -join ' ')"
    exit 0
}

Remove-Item Env:VITE_DEV_SERVER_URL -ErrorAction SilentlyContinue
Set-Location $projectRoot
wait-on @waitTargets
$env:JARVIS_SIDECAR_MANAGED = 'external'
electron .
