$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$modelPath = Join-Path $rootDir "ai\qwen3-0.6b-q4_k_m.gguf"
$outputDir = Join-Path $rootDir "src-tauri\binaries"
$targetTriple = (& rustc --print host-tuple).Trim()
$sidecarName = "jazrielle-backend-$targetTriple"
$outputPath = Join-Path $outputDir "$sidecarName.exe"

if ($targetTriple -ne "x86_64-pc-windows-msvc") {
    throw "Jazrielle's Windows sidecar build requires x86_64-pc-windows-msvc; found '$targetTriple'."
}

if (-not (Test-Path -LiteralPath $modelPath)) {
    throw "The local model is missing at '$modelPath'. Place qwen3-0.6b-q4_k_m.gguf there before building."
}

$condaCommand = Get-Command conda.exe -ErrorAction SilentlyContinue
if (-not $condaCommand) {
    $condaCandidates = @(
        (Join-Path $env:USERPROFILE "anaconda3\Scripts\conda.exe")
    )
    $condaPath = $condaCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
} else {
    $condaPath = $condaCommand.Source
}

if (-not $condaPath) {
    throw "Conda was not found. Install or initialize Conda, then create the jazrielle-backend environment."
}

$pyinstallerCheck = & $condaPath run --no-capture-output -n jazrielle-backend python -c "import PyInstaller" 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is unavailable in the jazrielle-backend Conda environment. Run conda env update -f backend/environment.yml --prune."
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$workDir = Join-Path $rootDir ".build\pyinstaller"
New-Item -ItemType Directory -Force -Path $workDir | Out-Null

Push-Location $backendDir
try {
    & $condaPath run --no-capture-output -n jazrielle-backend python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --noconsole `
        --name $sidecarName `
        --paths $backendDir `
        --distpath $outputDir `
        --workpath $workDir `
        --specpath $workDir `
        --collect-all llama_cpp `
        --collect-all pycaw `
        sidecar.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE." }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $outputPath)) {
    throw "PyInstaller completed but '$outputPath' was not created."
}

Write-Host "Built $outputPath"
