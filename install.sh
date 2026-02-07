#!/usr/bin/env bash
# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

# ============================================================================
#  The Foundry — One-Click Installer (macOS / Linux / WSL2)
# ============================================================================
set -euo pipefail

PYTHON_MIN="3.10"
NODE_MIN="18"
PORT_API=8420
PORT_UI=5173

# -- Colors ------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

banner() {
    echo ""
    echo -e "${CYAN}${BOLD}+======================================+${NC}"
    echo -e "${CYAN}${BOLD}|${NC}  ${BOLD}T H E   F O U N D R Y${NC}              ${CYAN}${BOLD}|${NC}"
    echo -e "${CYAN}${BOLD}|${NC}  Local LLM Training Ecosystem       ${CYAN}${BOLD}|${NC}"
    echo -e "${CYAN}${BOLD}+======================================+${NC}"
    echo ""
}

info()    { echo -e "${CYAN}[INFO]${NC}    $1"; }
success() { echo -e "${GREEN}[OK]${NC}      $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}    $1"; }
fail()    { echo -e "${RED}[ERROR]${NC}   $1"; exit 1; }

# -- Version compare ---------------------------------------------------------
version_gte() {
    # Returns 0 if $1 >= $2
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

# -- Detect platform ---------------------------------------------------------
detect_platform() {
    local os kernel
    os="$(uname -s)"
    case "$os" in
        Linux)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                PLATFORM="wsl2"
            else
                PLATFORM="linux"
            fi
            ;;
        Darwin)
            PLATFORM="macos"
            ;;
        *)
            fail "Unsupported platform: $os"
            ;;
    esac
    success "Platform detected: ${BOLD}$PLATFORM${NC}"
}

# -- Check Python ------------------------------------------------------------
check_python() {
    local py=""
    for candidate in python3 python; do
        if command -v "$candidate" &>/dev/null; then
            local ver
            ver="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
            if version_gte "$ver" "$PYTHON_MIN"; then
                py="$candidate"
                break
            fi
        fi
    done

    if [ -z "$py" ]; then
        fail "Python >= $PYTHON_MIN not found. Please install Python first:\n  macOS:  brew install python@3.12\n  Ubuntu: sudo apt install python3.12 python3.12-venv\n  WSL2:   sudo apt install python3.12 python3.12-venv"
    fi

    PYTHON="$py"
    local full_ver
    full_ver="$($PYTHON --version 2>&1)"
    success "Python found: ${BOLD}$full_ver${NC}"
}

# -- Check Node.js -----------------------------------------------------------
check_node() {
    if ! command -v node &>/dev/null; then
        warn "Node.js not found. Attempting to install..."
        install_node
        return
    fi

    local ver
    ver="$(node -v | sed 's/v//' | cut -d. -f1)"
    if [ "$ver" -lt "$NODE_MIN" ]; then
        warn "Node.js >= $NODE_MIN required (found v$ver). Attempting to upgrade..."
        install_node
        return
    fi

    success "Node.js found: ${BOLD}$(node -v)${NC}"
}

install_node() {
    case "$PLATFORM" in
        macos)
            if command -v brew &>/dev/null; then
                info "Installing Node.js via Homebrew..."
                brew install node
            else
                fail "Please install Node.js >= $NODE_MIN: https://nodejs.org"
            fi
            ;;
        linux|wsl2)
            if command -v apt &>/dev/null; then
                info "Installing Node.js via NodeSource..."
                curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                sudo apt install -y nodejs
            else
                fail "Please install Node.js >= $NODE_MIN: https://nodejs.org"
            fi
            ;;
    esac

    if ! command -v node &>/dev/null; then
        fail "Node.js installation failed. Please install manually: https://nodejs.org"
    fi
    success "Node.js installed: ${BOLD}$(node -v)${NC}"
}

# -- Check npm ---------------------------------------------------------------
check_npm() {
    if ! command -v npm &>/dev/null; then
        fail "npm not found. It should come with Node.js. Please reinstall Node.js."
    fi
    success "npm found: ${BOLD}$(npm -v)${NC}"
}

# -- Setup Python venv -------------------------------------------------------
setup_venv() {
    local venv_dir="$PROJECT_DIR/.venv"

    if [ -d "$venv_dir" ] && [ -f "$venv_dir/bin/activate" ]; then
        info "Virtual environment already exists, reusing..."
    else
        info "Creating Python virtual environment..."
        $PYTHON -m venv "$venv_dir"
    fi

    # shellcheck disable=SC1091
    source "$venv_dir/bin/activate"
    success "Virtual environment activated"
}

# -- Install Python deps -----------------------------------------------------
install_python_deps() {
    info "Installing Foundry core dependencies..."
    pip install --upgrade pip -q
    pip install -e "." -q
    success "Core dependencies installed"

    echo ""
    echo -e "  ${YELLOW}Optional dependency groups:${NC}"
    echo -e "    ${BOLD}pip install -e '.[training]'${NC}  — PyTorch, Unsloth, TRL, QLoRA"
    echo -e "    ${BOLD}pip install -e '.[eval]'${NC}      — Evaluation benchmarks"
    echo -e "    ${BOLD}pip install -e '.[dev]'${NC}       — Dev tools (pytest, ruff, mypy)"
    echo -e "    ${BOLD}pip install -e '.[all]'${NC}       — Everything"
    echo ""
}

# -- Install frontend deps ---------------------------------------------------
install_frontend() {
    info "Installing frontend dependencies..."
    cd "$PROJECT_DIR/frontend"
    npm install --silent 2>&1 | tail -1
    cd "$PROJECT_DIR"
    success "Frontend dependencies installed"
}

# -- Run tests ---------------------------------------------------------------
run_tests() {
    info "Running test suite..."
    if pip install pytest pytest-asyncio pytest-cov httpx -q 2>/dev/null && \
       $PYTHON -m pytest tests/ -q --tb=line 2>&1; then
        success "All tests passed"
    else
        warn "Some tests failed — this may be expected without GPU/torch"
    fi
}

# -- Create launcher script ---------------------------------------------------
create_launcher() {
    local launcher="$PROJECT_DIR/start.sh"
    cat > "$launcher" << 'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/.venv/bin/activate"

echo ""
echo "Starting The Foundry..."
echo "  API:      http://localhost:8420"
echo "  Frontend: http://localhost:5173"
echo ""

# Start backend
python -m foundry serve --port 8420 &
BACKEND_PID=$!

# Start frontend
cd "$DIR/frontend"
npx vite --port 5173 &
FRONTEND_PID=$!

# Trap to kill both on exit
cleanup() {
    echo ""
    echo "Shutting down The Foundry..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT INT TERM

# Wait for either to exit
wait -n $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
LAUNCHER
    chmod +x "$launcher"
    success "Launcher created: ${BOLD}start.sh${NC}"
}

# -- Create .env if missing ---------------------------------------------------
setup_env() {
    if [ ! -f "$PROJECT_DIR/.env" ] && [ -f "$PROJECT_DIR/.env.example" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        success "Created .env from .env.example"
    fi
}

# ============================================================================
#  MAIN
# ============================================================================

banner

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

info "Installing The Foundry from: ${BOLD}$PROJECT_DIR${NC}"
echo ""

echo -e "${BOLD}[1/7] Detecting platform...${NC}"
detect_platform

echo ""
echo -e "${BOLD}[2/7] Checking Python...${NC}"
check_python

echo ""
echo -e "${BOLD}[3/7] Checking Node.js...${NC}"
check_node
check_npm

echo ""
echo -e "${BOLD}[4/7] Setting up Python environment...${NC}"
setup_venv

echo ""
echo -e "${BOLD}[5/7] Installing dependencies...${NC}"
install_python_deps
install_frontend

echo ""
echo -e "${BOLD}[6/7] Running tests...${NC}"
run_tests

echo ""
echo -e "${BOLD}[7/7] Finalizing...${NC}"
setup_env
create_launcher

echo ""
echo -e "${GREEN}${BOLD}+======================================+${NC}"
echo -e "${GREEN}${BOLD}|  Installation Complete!              |${NC}"
echo -e "${GREEN}${BOLD}+======================================+${NC}"
echo ""
echo -e "  ${BOLD}Quick Start:${NC}"
echo -e "    ./start.sh                         — Launch API + Frontend"
echo -e "    source .venv/bin/activate           — Activate venv manually"
echo -e "    python -m foundry serve             — API only (port 8420)"
echo -e "    cd frontend && npx vite             — Frontend only (port 5173)"
echo ""
echo -e "  ${BOLD}Verify:${NC}"
echo -e "    python -m foundry check-env         — Check GPU/CUDA/WSL2 status"
echo -e "    curl http://localhost:8420/api/health"
echo ""
echo -e "  ${BOLD}Install training deps (requires NVIDIA GPU):${NC}"
echo -e "    pip install -e '.[training]'"
echo ""

if [ "$PLATFORM" = "linux" ] || [ "$PLATFORM" = "wsl2" ]; then
    echo -e "  ${GREEN}Detected $PLATFORM — full multiprocessing enabled${NC}"
elif [ "$PLATFORM" = "macos" ]; then
    echo -e "  ${YELLOW}macOS detected — GPU training requires NVIDIA CUDA (not available on Mac).${NC}"
    echo -e "  ${YELLOW}CPU-only mode will be used. Consider using a Linux/WSL2 machine for training.${NC}"
fi
echo ""
