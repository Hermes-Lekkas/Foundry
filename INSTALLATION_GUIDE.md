# The Foundry — Installation Guide
## One-Click Installers for All Platforms

---

## Quick Start

Choose your platform and run the installer:

| Platform | Method | Command |
|----------|--------|---------|
| **macOS** | Terminal | `bash install.sh` |
| **Linux** | Terminal | `bash install.sh` |
| **WSL2** | Terminal | `bash install.sh` |
| **Windows** | PowerShell | `powershell -ExecutionPolicy Bypass -File install.ps1` |
| **Windows** | CMD | `install.bat` |

---

## Prerequisites

### All Platforms
- **Python** 3.10 or higher
- **Node.js** 18 or higher
- **Git** (for cloning)

### Platform-Specific

#### macOS
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install prerequisites
brew install python@3.12 node
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip curl

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

#### Windows
1. Download Python from [python.org](https://www.python.org/downloads/)
   - ⚠️ Check "Add Python to PATH" during installation
2. Download Node.js from [nodejs.org](https://nodejs.org/)

---

## Detailed Installation

### macOS

```bash
# 1. Clone the repository
git clone https://github.com/Hermes-Lekkas/Foundry.git
cd Foundry

# 2. Run installer
bash install.sh

# 3. Start The Foundry
./start.sh
```

**Note for macOS:** GPU training is not available (no CUDA). Use for:
- Data synthesis
- Small model training (CPU)
- Development and testing
- Deployment to Apple Silicon

### Linux Native

```bash
# 1. Clone the repository
git clone https://github.com/Hermes-Lekkas/Foundry.git
cd Foundry

# 2. Run installer
bash install.sh

# 3. Start The Foundry
./start.sh
```

**Requirements:**
- NVIDIA GPU with CUDA (for training)
- 8GB+ VRAM recommended

### WSL2 (Windows - Recommended)

```powershell
# 1. Install WSL2 (in PowerShell as Administrator)
wsl --install -d Ubuntu

# 2. Restart, then open WSL2
wsl -d Ubuntu

# 3. Inside WSL2, install prerequisites
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip curl git

# 4. Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 5. Clone and install
git clone https://github.com/Hermes-Lekkas/Foundry.git
cd Foundry
bash install.sh

# 6. Start The Foundry
./start.sh
```

**WSL2 Benefits:**
- Full multiprocessing support
- Native Linux performance
- CUDA support (with proper drivers)

### Windows Native

#### Option A: PowerShell (Recommended)
```powershell
# 1. Clone the repository
git clone https://github.com/Hermes-Lekkas/Foundry.git
cd Foundry

# 2. Run installer
powershell -ExecutionPolicy Bypass -File install.ps1

# 3. Start The Foundry
.\start.ps1
```

#### Option B: CMD
```cmd
:: 1. Clone the repository
git clone https://github.com/Hermes-Lekkas/Foundry.git
cd Foundry

:: 2. Run installer
install.bat

:: 3. Start The Foundry
start.bat
```

**Windows Limitations:**
- Limited multiprocessing (dataset_num_proc=1)
- No CUDA on Windows native
- For full performance, use WSL2

---

## Optional: Swift Security Tools (macOS Only)

For enhanced macOS security integration:

```bash
cd macos_security
swift build -c release
sudo cp .build/release/foundry-sandbox /usr/local/bin/

# Verify installation
foundry-sandbox status
```

---

## Optional: Rust Security Engine

For enhanced performance on all platforms:

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install maturin
pip install maturin

# Build and install
cd security_engine
cargo build --release
maturin develop
```

---

## Verification

After installation, verify everything works:

```bash
# Check environment
python -m foundry check-env

# Test security
python -m foundry security status

# Test API (in another terminal)
curl http://localhost:8420/api/health

# View all commands
python -m foundry --help
```

---

## Troubleshooting

### macOS: "Python not found"
```bash
brew install python@3.12
export PATH="/opt/homebrew/opt/python@3.12/bin:$PATH"
```

### Linux: "Permission denied"
```bash
chmod +x install.sh
bash install.sh
```

### Windows: "ExecutionPolicy" error
```powershell
# Run as Administrator, then:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Or use the bypass flag:
powershell -ExecutionPolicy Bypass -File install.ps1
```

### All Platforms: "Node.js not found"
- **macOS**: `brew install node`
- **Linux**: Follow NodeSource instructions above
- **Windows**: Download from nodejs.org and restart terminal

### WSL2: "CUDA not available"
```bash
# Install NVIDIA drivers on Windows host
# Install CUDA toolkit in WSL2:
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-2
```

### Tests fail during installation
This is often expected on systems without GPU/CUDA. The core functionality will still work.

---

## Post-Installation

### Install Training Dependencies (GPU Required)
```bash
# Activate virtual environment first
source .venv/bin/activate  # Linux/macOS/WSL2
.venv\Scripts\activate.bat  # Windows

# Install training dependencies
pip install -e ".[training]"
```

### Configure Environment
```bash
# Edit .env file
cp .env.example .env
nano .env  # or your preferred editor
```

### Start Development Server
```bash
# Start both API and Frontend
./start.sh       # Linux/macOS/WSL2
.\start.ps1      # Windows PowerShell
start.bat        # Windows CMD

# Or start separately:
python -m foundry serve        # API only
cd frontend && npm run dev     # Frontend only
```

---

## Platform Comparison

| Feature | macOS | Linux | WSL2 | Windows |
|---------|-------|-------|------|---------|
| Installation | Easy | Easy | Medium | Easy |
| GPU Training | ❌ | ✅ | ✅ | ❌ |
| Multiprocessing | ✅ | ✅ | ✅ | ⚠️ Limited |
| Performance | Good | Excellent | Excellent | Good |
| Recommended for | Dev/Testing | Production | Development | Development |

---

## Getting Help

If installation fails:

1. Check prerequisites are installed
2. Run `python -m foundry check-env` for diagnostics
3. Check the [GitHub Issues](https://github.com/Hermes-Lekkas/Foundry/issues)
4. Include your OS version and error messages

---

## Next Steps

After installation:

1. **[Quick Start Guide](README.md#quick-start)** — Run your first training job
2. **[Security Setup](SECURITY_ARCHITECTURE.md)** — Configure security options
3. **[macOS Guide](MACOS_SUPPORT.md)** — macOS-specific features
4. **[API Documentation](README.md#api-endpoints)** — Integrate with the API

---

**Welcome to The Foundry! 🏭**
