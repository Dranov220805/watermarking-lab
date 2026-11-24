<#
.SYNOPSIS
    Sets up the Python .venv, installs backend/frontend dependencies if needed,
    activates .venv, and launches both services via `npm run start:all`.
.EXAMPLE
    .\start.ps1          # production mode (npm run start:all)
    .\start.ps1 -Dev     # development mode (npm run dev:all)
#>
param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvDir = Join-Path $BackendDir ".venv"
$VenvActivate = Join-Path $VenvDir "Scripts\Activate.ps1"

Write-Host "==> Setting up Python virtual environment in $VenvDir" -ForegroundColor Cyan
Push-Location $BackendDir
try {
    if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Failed to create Python virtual environment." }
    }

    Write-Host "==> Activating virtual environment (.venv/Scripts/Activate.ps1)" -ForegroundColor Cyan
    . $VenvActivate

    Write-Host "==> Installing backend dependencies from requirements.txt" -ForegroundColor Cyan
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install failed." }
} finally {
    Pop-Location
}

Write-Host "==> Switching to frontend ($FrontendDir) inside active .venv" -ForegroundColor Cyan
Push-Location $FrontendDir
try {
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host "==> Installing frontend npm packages" -ForegroundColor Cyan
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed." }
    }

    if ($Dev) {
        Write-Host "==> Starting backend + frontend in dev mode (npm run dev:all)" -ForegroundColor Green
        npm run dev:all
    } else {
        if (-not (Test-Path (Join-Path $FrontendDir ".next\BUILD_ID"))) {
            Write-Host "==> Building Next.js production bundle (npm run build)" -ForegroundColor Cyan
            npm run build
            if ($LASTEXITCODE -ne 0) { throw "npm run build failed." }
        }
        Write-Host "==> Starting backend + frontend in production mode (npm run start:all)" -ForegroundColor Green
        npm run start:all
    }
} finally {
    Pop-Location
}
