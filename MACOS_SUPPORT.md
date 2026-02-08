# macOS Support Guide

The Foundry fully supports macOS with native security tools and optimizations.

## Platform-Specific Features

### Security

#### Python Sandbox (`foundry/sandbox/`)
- Platform detection: `IS_MACOS = platform.system() == "darwin"`
- Seatbelt profile generation for optional sandbox-exec integration
- macOS-specific environment variables (`__CF_USER_TEXT_ENCODING`)
- Resource limits via `ulimit` (with macOS-compatible syntax)

#### Rust Security Engine (`security_engine/`)
- Unix platform support includes macOS
- macOS-specific memory limit handling
- Automatic Python3 detection (`python3` instead of `python`)

#### Swift Native Tools (`macos_security/`) — Optional
- Native macOS Process API for sandboxing
- Seatbelt profile generation
- Swift-based audit logging with integrity chains
- Install: `cd macos_security && swift build -c release`

### Hardware Detection

macOS hardware detection includes:
- Apple Silicon (M1/M2/M3) detection
- Metal GPU support (for inference)
- Unified memory architecture handling

```python
from foundry.config.hardware import detect_hardware

hw = detect_hardware()
# hw.platform == PlatformType.MACOS
# hw.gpu.name shows Apple GPU
```

### Installation on macOS

```bash
# 1. Install Python 3.10+
brew install python@3.11

# 2. Clone repository
git clone https://github.com/Hermes-Lekkas/Foundry.git
cd Foundry

# 3. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Install Foundry
pip install -e ".[all]"

# 5. Verify installation
python -m foundry check-env
```

### Optional: Swift Security Tools

```bash
# Install Swift (if not already installed)
xcode-select --install

# Build Swift security tools
cd macos_security
swift build -c release

# Install CLI tool
sudo cp .build/release/foundry-sandbox /usr/local/bin/

# Verify
foundry-sandbox status
```

## Usage Examples

### Basic Training

```bash
# Profile VRAM
python -m foundry profile --model unsloth/Qwen2.5-0.5B

# Train with SFT
python -m foundry train --config configs/sft_default.yaml
```

### Security Validation

```bash
# Check security status
python -m foundry security status

# Validate code
python -m foundry security validate --file script.py

# View audit log
python -m foundry security audit
```

### Using Swift Tools (if installed)

```bash
# Execute in native macOS sandbox
foundry-sandbox execute script.py --timeout 30 --memory 512

# Validate code
foundry-sandbox validate script.py

# Check status
foundry-sandbox status
```

## macOS-Specific Considerations

### 1. No CUDA on macOS
- Training uses CPU or Metal (if supported by model)
- For serious training, use external GPU or cloud

### 2. Sandbox Permissions
- Grant Terminal/IDE Full Disk Access if needed for file operations
- Sandboxed execution limits filesystem access to work directory

### 3. Code Signing
- Swift tools may need code signing for distribution
- For local use, self-signed is acceptable

### 4. Memory Management
- macOS uses unified memory (RAM + VRAM shared)
- Adjust batch sizes accordingly

## Troubleshooting

### Issue: "sandbox-exec not found"
**Solution:** Seatbelt is optional. Python sandbox works without it.

### Issue: "Python3 not found"
**Solution:** Ensure Python 3 is installed: `brew install python@3.11`

### Issue: Swift build fails
**Solution:** Update Xcode Command Line Tools: `xcode-select --install`

### Issue: Permission denied in sandbox
**Solution:** Grant Full Disk Access to Terminal in System Preferences

## Performance Notes

| Operation | macOS Performance |
|-----------|-------------------|
| Data Synthesis | Good (CPU-based) |
| Training (Small Models) | Moderate (CPU/Metal) |
| Training (Large Models) | Slow (recommend cloud GPU) |
| Inference | Good (Metal acceleration) |
| Security Validation | Excellent (native Swift tools) |

## Recommended Workflow on macOS

1. **Development**: Use macOS for development and testing
2. **Small-scale training**: Train models up to 1B parameters locally
3. **Large-scale training**: Use WSL2/Linux cloud instances
4. **Deployment**: Deploy trained models back to macOS for inference

## File Locations

```
~/Documents/foundry_security_audit.json  # Audit log (Swift tools)
./.foundry/security_audit.db             # Audit log (Python)
/tmp/foundry_sandbox_*                   # Sandbox work directories
```

## Support

For macOS-specific issues:
1. Check System Preferences → Security & Privacy permissions
2. Verify Python installation: `python3 --version`
3. Test Swift tools: `foundry-sandbox status`
4. File issue with `python -m foundry check-env` output
