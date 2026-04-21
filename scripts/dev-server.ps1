Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location "$PSScriptRoot\..\jarvis-server"

$runtimeConfig = python -c "from app.config import get_server_runtime_config_json; print(get_server_runtime_config_json())" | ConvertFrom-Json
$serverHost = [string]$runtimeConfig.host
$serverPort = [int]$runtimeConfig.port

if ($env:JARVIS_SERVER_DRY_RUN -eq '1') {
    Write-Output "HOST=$serverHost"
    Write-Output "PORT=$serverPort"
    exit 0
}

python -m uvicorn app.main:create_app --factory --reload --host $serverHost --port $serverPort
