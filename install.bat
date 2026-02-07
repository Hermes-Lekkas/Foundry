:: THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
:: Copyright (c) 2026 Hermes Lekkas. All rights reserved.
::
:: This software is provided under a proprietary license.
:: See the LICENSE file for details.

@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
:: ============================================================================
::  The Foundry - One-Click Installer (Windows)
:: ============================================================================

set "PYTHON_MIN_MAJOR=3"
set "PYTHON_MIN_MINOR=10"
set "NODE_MIN=18"
set "PORT_API=8420"
set "PORT_UI=5173"

:: -- Banner ------------------------------------------------------------------
echo.
echo   +======================================+
echo   ^|  T H E   F O U N D R Y              ^|
echo   ^|  Local LLM Training Ecosystem       ^|
echo   +======================================+
echo.

:: -- Find project directory --------------------------------------------------
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

echo [1/7] Detecting platform...

:: Check if running in WSL2
set "IS_WSL=0"
where wsl >nul 2>&1
if %errorlevel%==0 (
    echo   [INFO]  WSL2 is available on this system.
    echo   [WARN]  For best performance, run install.sh inside WSL2 instead.
    echo           Open WSL2: wsl -d Ubuntu
    echo.
)
echo   [OK]    Platform: Windows

:: ============================================================================
echo.
echo [2/7] Checking Python...
:: ============================================================================

set "PYTHON="
:: Try python first, then python3, then py launcher
for %%P in (python python3) do (
    where %%P >nul 2>&1
    if !errorlevel!==0 (
        for /f "tokens=*" %%V in ('%%P -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
            for /f "tokens=1,2 delims=." %%A in ("%%V") do (
                if %%A GEQ %PYTHON_MIN_MAJOR% (
                    if %%B GEQ %PYTHON_MIN_MINOR% (
                        set "PYTHON=%%P"
                        set "PYTHON_VER=%%V"
                    )
                )
            )
        )
        if defined PYTHON goto :python_found
    )
)

:: Try py launcher
where py >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=*" %%V in ('py -3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
        for /f "tokens=1,2 delims=." %%A in ("%%V") do (
            if %%A GEQ %PYTHON_MIN_MAJOR% (
                if %%B GEQ %PYTHON_MIN_MINOR% (
                    set "PYTHON=py -3"
                    set "PYTHON_VER=%%V"
                    goto :python_found
                )
            )
        )
    )
)

echo   [ERROR] Python ^>= %PYTHON_MIN_MAJOR%.%PYTHON_MIN_MINOR% not found.
echo           Download from: https://www.python.org/downloads/
echo           Make sure to check "Add Python to PATH" during install.
pause
exit /b 1

:python_found
echo   [OK]    Python %PYTHON_VER% found

:: ============================================================================
echo.
echo [3/7] Checking Node.js...
:: ============================================================================

where node >nul 2>&1
if %errorlevel% NEQ 0 (
    echo   [ERROR] Node.js not found.
    echo           Download from: https://nodejs.org/
    echo           Install the LTS version and restart this script.
    pause
    exit /b 1
)

for /f "tokens=1 delims=." %%V in ('node -v') do set "NODE_VER=%%V"
set "NODE_VER=%NODE_VER:v=%"
if %NODE_VER% LSS %NODE_MIN% (
    echo   [ERROR] Node.js ^>= %NODE_MIN% required ^(found v%NODE_VER%^).
    echo           Download from: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%V in ('node -v') do echo   [OK]    Node.js %%V found

where npm >nul 2>&1
if %errorlevel% NEQ 0 (
    echo   [ERROR] npm not found. Reinstall Node.js from https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%V in ('npm -v') do echo   [OK]    npm %%V found

:: ============================================================================
echo.
echo [4/7] Setting up Python environment...
:: ============================================================================

if exist "%PROJECT_DIR%\.venv\Scripts\activate.bat" (
    echo   [INFO]  Virtual environment already exists, reusing...
) else (
    echo   [INFO]  Creating virtual environment...
    %PYTHON% -m venv "%PROJECT_DIR%\.venv"
    if %errorlevel% NEQ 0 (
        echo   [ERROR] Failed to create virtual environment.
        echo           Try: %PYTHON% -m pip install virtualenv
        pause
        exit /b 1
    )
)

call "%PROJECT_DIR%\.venv\Scripts\activate.bat"
echo   [OK]    Virtual environment activated

:: ============================================================================
echo.
echo [5/7] Installing dependencies...
:: ============================================================================

echo   [INFO]  Upgrading pip...
python -m pip install --upgrade pip -q >nul 2>&1

echo   [INFO]  Installing Foundry core dependencies...
pip install -e "." -q
if %errorlevel% NEQ 0 (
    echo   [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo   [OK]    Core dependencies installed

echo.
echo   Optional dependency groups:
echo     pip install -e ".[training]"  -- PyTorch, Unsloth, TRL, QLoRA
echo     pip install -e ".[eval]"      -- Evaluation benchmarks
echo     pip install -e ".[dev]"       -- Dev tools (pytest, ruff, mypy)
echo     pip install -e ".[all]"       -- Everything
echo.

echo   [INFO]  Installing frontend dependencies...
cd /d "%PROJECT_DIR%\frontend"
call npm install --silent >nul 2>&1
if %errorlevel% NEQ 0 (
    echo   [WARN]  npm install had warnings, retrying...
    call npm install 2>&1
)
cd /d "%PROJECT_DIR%"
echo   [OK]    Frontend dependencies installed

:: ============================================================================
echo.
echo [6/7] Running tests...
:: ============================================================================

pip install pytest pytest-asyncio pytest-cov httpx -q >nul 2>&1
python -m pytest tests/ -q --tb=line 2>&1
if %errorlevel%==0 (
    echo   [OK]    All tests passed
) else (
    echo   [WARN]  Some tests failed -- this may be expected without GPU/torch
)

:: ============================================================================
echo.
echo [7/7] Finalizing...
:: ============================================================================

:: Create .env if missing
if not exist "%PROJECT_DIR%\.env" (
    if exist "%PROJECT_DIR%\.env.example" (
        copy "%PROJECT_DIR%\.env.example" "%PROJECT_DIR%\.env" >nul
        echo   [OK]    Created .env from .env.example
    )
)

:: Create start.bat launcher
(
echo @echo off
echo setlocal
echo chcp 65001 ^>nul 2^>^&1
echo cd /d "%%~dp0"
echo call .venv\Scripts\activate.bat
echo echo.
echo echo Starting The Foundry...
echo echo   API:      http://localhost:8420
echo echo   Frontend: http://localhost:5173
echo echo.
echo echo Press Ctrl+C in either window to stop.
echo echo.
echo start "Foundry API" cmd /c "call .venv\Scripts\activate.bat && python -m foundry serve --port 8420"
echo cd frontend
echo start "Foundry UI" cmd /c "npx vite --port 5173"
echo echo.
echo echo The Foundry is running!
echo echo   API:      http://localhost:8420
echo echo   Frontend: http://localhost:5173
echo echo.
echo pause
) > "%PROJECT_DIR%\start.bat"
echo   [OK]    Launcher created: start.bat

:: ============================================================================
echo.
echo   +======================================+
echo   ^|  Installation Complete!              ^|
echo   +======================================+
echo.
echo   Quick Start:
echo     start.bat                          -- Launch API + Frontend
echo     .venv\Scripts\activate.bat         -- Activate venv manually
echo     python -m foundry serve            -- API only (port 8420)
echo     cd frontend ^&^& npx vite            -- Frontend only (port 5173)
echo.
echo   Verify:
echo     python -m foundry check-env        -- Check GPU/CUDA status
echo     curl http://localhost:8420/api/health
echo.
echo   Install training deps (requires NVIDIA GPU):
echo     pip install -e ".[training]"
echo.
echo   [WARN]  Windows native: dataset_num_proc=1 (limited multiprocessing).
echo           For full performance, use WSL2: wsl --install
echo.

pause
endlocal
