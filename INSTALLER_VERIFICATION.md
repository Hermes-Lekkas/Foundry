# Installer Verification & Cross-Platform Support

## Overview

The Foundry includes one-click installers for all major platforms. This document verifies their functionality and provides platform-specific notes.

---

## Installer Matrix

| Platform | Script | Status | Features |
|----------|--------|--------|----------|
| **macOS** | `install.sh` | ✅ Verified | Homebrew Python detection, seatbelt support |
| **Linux** | `install.sh` | ✅ Verified | Native Python, full GPU support |
| **WSL2** | `install.sh` | ✅ Verified | WSL detection, CUDA passthrough |
| **Windows PowerShell** | `install.ps1` | ✅ Verified | WSL detection, PowerShell launcher |
| **Windows CMD** | `install.bat` | ✅ Verified | Batch launcher, WSL warning |

---

## install.sh (macOS / Linux / WSL2)

### Features
- ✅ Platform detection (Linux/macOS/WSL2)
- ✅ Python 3.10+ detection with Homebrew support on macOS
- ✅ Node.js installation (via Homebrew/apt)
- ✅ Virtual environment setup
- ✅ Dependency installation
- ✅ Test execution
- ✅ Launcher script creation (`start.sh`)
- ✅ `.env` file creation

### Platform-Specific Logic

```bash
# Platform Detection
detect_platform() {
    case "$os" in
        Linux)
            if grep -qi microsoft /proc/version; then
                PLATFORM="wsl2"
            else
                PLATFORM="linux"
            fi
            ;;
        Darwin)
            PLATFORM="macos"
            ;;
    esac
}

# macOS Python Paths
if [ "$PLATFORM" = "macos" ]; then
    candidates=(
        "/opt/homebrew/bin/python3"  # Apple Silicon
        "/usr/local/bin/python3"      # Intel Mac
        "python3"
    )
fi
```

### Usage

```bash
# Make executable and run
chmod +x install.sh
bash install.sh

# Or directly
bash install.sh
```

---

## install.ps1 (Windows PowerShell)

### Features
- ✅ WSL2 availability detection
- ✅ Python detection (python/python3/py launcher)
- ✅ Node.js version checking
- ✅ Virtual environment setup
- ✅ Dependency installation
- ✅ Test execution
- ✅ Dual launcher creation (`start.ps1` + `start.bat`)

### WSL2 Detection

```powershell
$HasWSL = $null -ne (Get-Command wsl -ErrorAction SilentlyContinue)
if ($HasWSL) {
    Write-Warn "WSL2 is available. For best performance, run install.sh inside WSL2."
}
```

### Usage

```powershell
# Run with bypass (recommended)
powershell -ExecutionPolicy Bypass -File install.ps1

# Or set policy first
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install.ps1
```

---

## install.bat (Windows CMD)

### Features
- ✅ WSL detection
- ✅ Python version checking (with py launcher support)
- ✅ Node.js version validation
- ✅ Virtual environment creation
- ✅ Frontend dependency installation
- ✅ Test execution
- ✅ Launcher script creation (`start.bat`)

### Usage

```cmd
:: Double-click or run
install.bat
```

---

## Post-Installation Launchers

### macOS/Linux/WSL2: `start.sh`
```bash
./start.sh  # Starts both API and Frontend
```

### Windows PowerShell: `start.ps1`
```powershell
.\start.ps1  # Starts both in separate windows
```

### Windows CMD: `start.bat`
```cmd
start.bat  # Starts both in separate windows
```

---

## Platform-Specific Notes

### macOS
- **Python**: Uses Homebrew Python if available (`/opt/homebrew/bin/python3` or `/usr/local/bin/python3`)
- **GPU**: No CUDA support (CPU/Metal only for training)
- **Security**: Optional Swift security tools available
- **Recommendation**: Best for development and inference

### Linux Native
- **Python**: System Python 3.10+
- **GPU**: Full CUDA support
- **Performance**: Optimal for training
- **Recommendation**: Best for production training

### WSL2
- **Python**: Ubuntu system Python
- **GPU**: CUDA passthrough from Windows host
- **Performance**: Near-native Linux performance
- **Recommendation**: Best Windows option for training

### Windows Native
- **Python**: Windows Python from python.org
- **GPU**: No CUDA support
- **Multiprocessing**: Limited (dataset_num_proc=1)
- **Recommendation**: Development only, use WSL2 for training

---

## Installation Checklist

### Prerequisites by Platform

#### macOS
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install prerequisites
brew install python@3.12 node git
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip curl git

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

#### Windows
1. Python from [python.org](https://www.python.org/downloads/) (check "Add to PATH")
2. Node.js from [nodejs.org](https://nodejs.org/)
3. Git from [git-scm.com](https://git-scm.com/download/win)

---

## Troubleshooting

### Common Issues

#### Issue: "Python not found" on macOS
**Solution**: Add Homebrew Python to PATH
```bash
# Apple Silicon
export PATH="/opt/homebrew/opt/python@3.12/bin:$PATH"

# Intel Mac
export PATH="/usr/local/opt/python@3.12/bin:$PATH"
```

#### Issue: "ExecutionPolicy" on Windows PowerShell
**Solution**: Use bypass flag
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

#### Issue: "Permission denied" on Linux/macOS
**Solution**: Make script executable
```bash
chmod +x install.sh
bash install.sh
```

#### Issue: Tests fail during installation
**Note**: This is often expected on systems without GPU. Core functionality will still work.

---

## Verification

After installation, verify everything works:

```bash
# All platforms
python -m foundry check-env
python -m foundry security status

# Test API (start server first)
curl http://localhost:8420/api/health
```

---

## Summary

| Feature | install.sh | install.ps1 | install.bat |
|---------|-----------|-------------|-------------|
| Python 3.10+ check | ✅ | ✅ | ✅ |
| Node.js 18+ check | ✅ | ✅ | ✅ |
| Virtual environment | ✅ | ✅ | ✅ |
| Dependency install | ✅ | ✅ | ✅ |
| Test execution | ✅ | ✅ | ✅ |
| Launcher creation | ✅ | ✅ | ✅ |
| Platform detection | ✅ | ✅ | ✅ |
| WSL warning | ✅ | ✅ | ✅ |
| Error handling | ✅ | ✅ | ✅ |

**All installers are verified and ready for use!**
