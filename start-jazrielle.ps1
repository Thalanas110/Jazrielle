$ErrorActionPreference = "Stop"

$rootDir = $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

$condaCommand = Get-Command conda.exe -ErrorAction SilentlyContinue
if (-not $condaCommand) {
    $condaCandidates = @(
        (Join-Path $env:USERPROFILE "anaconda3\Scripts\conda.exe"),
        (Join-Path $env:USERPROFILE "miniconda3\Scripts\conda.exe")
    )
    $condaPath = $condaCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
} else {
    $condaPath = $condaCommand.Source
}

if (-not $condaPath) {
    throw "Conda was not found. Install or initialize Conda before starting Jazrielle."
}

if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js before starting Jazrielle."
}

$backendCommand = "& '$condaPath' run --no-capture-output -n jazrielle-backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
$frontendCommand = "npm.cmd run dev"

Start-Process powershell.exe `
    -WorkingDirectory $backendDir `
    -ArgumentList @("-NoExit", "-NoProfile", "-Command", $backendCommand) | Out-Null

Start-Process powershell.exe `
    -WorkingDirectory $frontendDir `
    -ArgumentList @("-NoExit", "-NoProfile", "-Command", $frontendCommand) | Out-Null

Write-Host "Jazrielle backend and frontend started in separate PowerShell windows."
