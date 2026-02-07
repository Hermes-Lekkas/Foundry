# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

# ============================================================================
#  The Foundry — One-Click Installer (Windows PowerShell)
# ============================================================================
#
#  Usage:  Right-click > Run with PowerShell
#    -or-  powershell -ExecutionPolicy Bypass -File install.ps1
#
# ============================================================================

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$PYTHON_MIN = [version]"3.10"
$NODE_MIN = 18
$PORT_API = 8420
$PORT_UI = 5173

# -- Helpers -----------------------------------------------------------------
function Write-Banner {
    Write-Host ""
    Write-Host "  +======================================+" -ForegroundColor Cyan
    Write-Host "  |  T H E   F O U N D R Y              |" -ForegroundColor Cyan
    Write-Host "  |  Local LLM Training Ecosystem       |" -ForegroundColor Cyan
    Write-Host "  +======================================+" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step($num, $msg) { Write-Host "`n[$num/7] $msg" -ForegroundColor White }
function Write-Info($msg)    { Write-Host "  [INFO]  $msg" -ForegroundColor Cyan }
function Write-OK($msg)      { Write-Host "  [OK]    $msg" -ForegroundColor Green }
function Write-Warn($msg)    { Write-Host "  [WARN]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)     { Write-Host "  [ERROR] $msg" -ForegroundColor Red }

# -- Find project dir ---------------------------------------------------------
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

Write-Banner

# ============================================================================
Write-Step 1 "Detecting platform..."
# ============================================================================

$HasWSL = $null -ne (Get-Command wsl -ErrorAction SilentlyContinue)
if ($HasWSL) {
    Write-Warn "WSL2 is available. For best performance, run install.sh inside WSL2."
    Write-Info "Open WSL2: wsl -d Ubuntu"
}
Write-OK "Platform: Windows (PowerShell $($PSVersionTable.PSVersion))"

# ============================================================================
Write-Step 2 "Checking Python..."
# ============================================================================

$PythonCmd = $null
foreach ($candidate in @("python", "python3")) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            $ver = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ([version]$ver -ge $PYTHON_MIN) {
                $PythonCmd = $candidate
                break
            }
        } catch {}
    }
}

# Try py launcher
if (-not $PythonCmd) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $ver = & py -3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ([version]$ver -ge $PYTHON_MIN) {
                $PythonCmd = "py -3"
            }
        } catch {}
    }
}

if (-not $PythonCmd) {
    Write-Err "Python >= $PYTHON_MIN not found."
    Write-Err 'Download from: https://www.python.org/downloads/'
    Write-Err 'Make sure to check "Add Python to PATH" during install.'
    Read-Host "Press Enter to exit"
    exit 1
}

$PyFullVer = & $PythonCmd --version 2>&1
Write-OK "Python found: $PyFullVer"

# ============================================================================
Write-Step 3 "Checking Node.js..."
# ============================================================================

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Err "Node.js not found. Download from: https://nodejs.org/"
    Read-Host "Press Enter to exit"
    exit 1
}

$nodeVer = (node -v) -replace 'v','' -split '\.' | Select-Object -First 1
if ([int]$nodeVer -lt $NODE_MIN) {
    Write-Err "Node.js >= $NODE_MIN required (found v$nodeVer)."
    Write-Err "Download from: https://nodejs.org/"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-OK "Node.js found: $(node -v)"

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    Write-Err "npm not found. Reinstall Node.js from https://nodejs.org/"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-OK "npm found: $(npm -v)"

# ============================================================================
Write-Step 4 "Setting up Python environment..."
# ============================================================================

$VenvDir = Join-Path $ProjectDir ".venv"
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"

if (Test-Path $ActivateScript) {
    Write-Info "Virtual environment already exists, reusing..."
} else {
    Write-Info "Creating virtual environment..."
    & $PythonCmd -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to create virtual environment."
        Read-Host "Press Enter to exit"
        exit 1
    }
}

& $ActivateScript
Write-OK "Virtual environment activated"

# ============================================================================
Write-Step 5 "Installing dependencies..."
# ============================================================================

Write-Info "Upgrading pip..."
python -m pip install --upgrade pip -q 2>$null | Out-Null

Write-Info "Installing Foundry core dependencies..."
pip install -e "." -q
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to install Python dependencies."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-OK "Core dependencies installed"

Write-Host ""
Write-Host "  Optional dependency groups:" -ForegroundColor Yellow
Write-Host '    pip install -e ".[training]"  -- PyTorch, Unsloth, TRL, QLoRA'
Write-Host '    pip install -e ".[eval]"      -- Evaluation benchmarks'
Write-Host '    pip install -e ".[dev]"       -- Dev tools (pytest, ruff, mypy)'
Write-Host '    pip install -e ".[all]"       -- Everything'
Write-Host ""

Write-Info "Installing frontend dependencies..."
Push-Location (Join-Path $ProjectDir "frontend")
npm install --silent 2>&1 | Out-Null
Pop-Location
Write-OK "Frontend dependencies installed"

# ============================================================================
Write-Step 6 "Running tests..."
# ============================================================================

pip install pytest pytest-asyncio pytest-cov httpx -q 2>$null | Out-Null
$testResult = python -m pytest tests/ -q --tb=line 2>&1
Write-Host $testResult
if ($LASTEXITCODE -eq 0) {
    Write-OK "All tests passed"
} else {
    Write-Warn "Some tests failed -- this may be expected without GPU/torch"
}

# ============================================================================
Write-Step 7 "Finalizing..."
# ============================================================================

# Create .env if missing
$envFile = Join-Path $ProjectDir ".env"
$envExample = Join-Path $ProjectDir ".env.example"
if ((-not (Test-Path $envFile)) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-OK "Created .env from .env.example"
}

# Create start.ps1 launcher
$launcherPath = Join-Path $ProjectDir "start.ps1"
@'
# The Foundry — Launcher
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

& (Join-Path $ProjectDir ".venv\Scripts\Activate.ps1")

Write-Host ""
Write-Host "Starting The Foundry..." -ForegroundColor Cyan
Write-Host "  API:      http://localhost:8420"
Write-Host "  Frontend: http://localhost:5173"
Write-Host ""

# Start backend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$ProjectDir\.venv\Scripts\Activate.ps1'; python -m foundry serve --port 8420" -WorkingDirectory $ProjectDir

# Start frontend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectDir\frontend'; npx vite --port 5173" -WorkingDirectory "$ProjectDir\frontend"

Write-Host "The Foundry is running!" -ForegroundColor Green
Write-Host "  API:      http://localhost:8420"
Write-Host "  Frontend: http://localhost:5173"
Write-Host ""
Write-Host "Close the spawned terminal windows to stop the servers."
'@ | Set-Content $launcherPath -Encoding UTF8
Write-OK "Launcher created: start.ps1"

# Also create start.bat
$batPath = Join-Path $ProjectDir "start.bat"
@"
@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo.
echo Starting The Foundry...
echo   API:      http://localhost:8420
echo   Frontend: http://localhost:5173
echo.
start "Foundry API" cmd /c "call .venv\Scripts\activate.bat && python -m foundry serve --port 8420"
cd frontend
start "Foundry UI" cmd /c "npx vite --port 5173"
echo.
echo The Foundry is running!
echo   API:      http://localhost:8420
echo   Frontend: http://localhost:5173
echo.
pause
"@ | Set-Content $batPath -Encoding ASCII
Write-OK "Launcher created: start.bat"

# ============================================================================
Write-Host ""
Write-Host "  +======================================+" -ForegroundColor Green
Write-Host "  |  Installation Complete!              |" -ForegroundColor Green
Write-Host "  +======================================+" -ForegroundColor Green
Write-Host ""
Write-Host "  Quick Start:"
Write-Host "    .\start.ps1                        -- Launch API + Frontend (PowerShell)"
Write-Host "    .\start.bat                        -- Launch API + Frontend (CMD)"
Write-Host "    .venv\Scripts\Activate.ps1         -- Activate venv manually"
Write-Host "    python -m foundry serve            -- API only (port 8420)"
Write-Host "    cd frontend; npx vite              -- Frontend only (port 5173)"
Write-Host ""
Write-Host "  Verify:"
Write-Host "    python -m foundry check-env        -- Check GPU/CUDA status"
Write-Host "    curl http://localhost:8420/api/health"
Write-Host ""
Write-Host "  Install training deps (requires NVIDIA GPU):"
Write-Host '    pip install -e ".[training]"'
Write-Host ""
Write-Warn "Windows native: dataset_num_proc=1 (limited multiprocessing)."
Write-Warn "For full performance, use WSL2: wsl --install"
Write-Host ""
Read-Host "Press Enter to exit"
