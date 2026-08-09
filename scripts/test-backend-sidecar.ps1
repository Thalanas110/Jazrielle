$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$targetTriple = (& rustc --print host-tuple).Trim()
$sidecar = Join-Path $rootDir "src-tauri\binaries\jazrielle-backend-$targetTriple.exe"
$assetDir = Join-Path $rootDir "ai"

if (-not (Test-Path -LiteralPath $sidecar)) {
    throw "Sidecar not found. Run npm run build:backend-sidecar from frontend first."
}

$env:MODEL_PATH = Join-Path $assetDir "qwen3-0.6b-q4_k_m.gguf"
$env:SYSTEM_PROMPT_PATH = Join-Path $assetDir "system-prompt.md"
$env:ACTION_CONFIG_PATH = Join-Path $assetDir "assistant-actions.json"
$env:CORS_ORIGINS = "http://localhost:20380,http://127.0.0.1:20380,tauri://localhost,http://tauri.localhost"
$process = Start-Process -FilePath $sidecar -ArgumentList @("--host", "127.0.0.1", "--port", "8000") -PassThru -WindowStyle Hidden

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt += 1) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
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
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
}
