$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$targetTriple = (& rustc --print host-tuple).Trim()
$sidecar = Join-Path $rootDir "src-tauri\binaries\jazrielle-backend-$targetTriple.exe"
$assetDir = Join-Path $rootDir "ai"
$port = Get-Random -Minimum 18000 -Maximum 28000

if (-not (Test-Path -LiteralPath $sidecar)) {
    throw "Sidecar not found. Run npm run build:backend-sidecar from frontend first."
}

$env:MODEL_PATH = Join-Path $assetDir "qwen3-0.6b-q4_k_m.gguf"
$env:SYSTEM_PROMPT_PATH = Join-Path $assetDir "system-prompt.md"
$env:ACTION_CONFIG_PATH = Join-Path $assetDir "assistant-actions.json"
$env:CORS_ORIGINS = "http://localhost:20380,http://127.0.0.1:20380,tauri://localhost,http://tauri.localhost"
$existingConnection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($existingConnection) {
    throw "Smoke-test port $port is already in use."
}

$process = Start-Process -FilePath $sidecar -ArgumentList @("--host", "127.0.0.1", "--port", "$port") -PassThru -WindowStyle Hidden

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt += 1) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:$port/health" -TimeoutSec 2
            if ($response.status -eq "ok") {
                $ready = $true
                break
            }
        } catch { }
    }

    if (-not $ready) {
        throw "Sidecar did not become healthy within 15 seconds."
    }

    Write-Host "Sidecar health check passed."
} finally {
    $process.Refresh()
    Start-Process -FilePath taskkill.exe `
        -ArgumentList @("/PID", $process.Id, "/T", "/F") `
        -Wait `
        -WindowStyle Hidden | Out-Null
    Start-Sleep -Milliseconds 500
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Sidecar process tree still owns smoke-test port $port after shutdown."
    }
}
