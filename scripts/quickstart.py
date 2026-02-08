#!/usr/bin/env python3
"""
Quickstart script - Walks through a complete training workflow.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def print_step(step_num: int, title: str):
    """Print a formatted step header."""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {title}")
    print(f"{'='*60}\n")


def check_environment():
    """Check if the environment is properly configured."""
    print_step(1, "Environment Check")
    
    from foundry.config.hardware import detect_hardware
    
    hw = detect_hardware()
    print(f"Platform: {hw.platform.value}")
    print(f"GPU: {hw.gpu.name or 'None (CPU-only mode)'}")
    print(f"VRAM: {hw.gpu.vram_total_gb:.1f} GB")
    print(f"CUDA: {hw.gpu.cuda_version or 'N/A'}")
    print(f"Tier: {hw.tier.value}")
    
    if hw.tier == "cpu_only":
        print("\nWARNING: No GPU detected. Training will be very slow.")
        print("   For actual training, use a machine with an NVIDIA GPU.")
    
    return hw


def check_api_keys():
    """Check if API keys are configured for teacher models."""
    print_step(2, "API Configuration")
    
    import os
    
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if anthropic_key:
        print("[OK] ANTHROPIC_API_KEY is set")
    else:
        print("[MISSING] ANTHROPIC_API_KEY not set")
    
    if openai_key:
        print("[OK] OPENAI_API_KEY is set")
    else:
        print("[MISSING] OPENAI_API_KEY not set")
    
    if not anthropic_key and not openai_key:
        print("\nWARNING: No API keys found. Data synthesis will use local models only.")
        print("   To use API teacher models, set the environment variables:")
        print("   export ANTHROPIC_API_KEY=sk-ant-...")
        print("   export OPENAI_API_KEY=sk-...")


def list_constitutions():
    """List available constitutions."""
    print_step(3, "Available Constitutions")
    
    from foundry.config.settings import get_settings
    from foundry.data_engine.constitution import Constitution
    
    settings = get_settings()
    const_dir = settings.constitution_dir
    
    for f in sorted(const_dir.glob("*.yaml")):
        constitution = Constitution.from_yaml(f)
        print(f"  • {f.stem}: {constitution.description}")


def list_configs():
    """List available training configs."""
    print_step(4, "Available Training Configs")
    
    import yaml
    
    config_dir = Path("configs")
    if not config_dir.exists():
        print("No configs directory found.")
        return
    
    for f in sorted(config_dir.glob("*.yaml")):
        with open(f) as fp:
            config = yaml.safe_load(fp)
        print(f"  • {f.stem}:")
        print(f"    - Model: {config.get('model_name', 'N/A')}")
        print(f"    - Trainer: {config.get('trainer_type', 'N/A')}")
        print(f"    - Epochs: {config.get('num_epochs', 'N/A')}")


def show_commands():
    """Show example commands."""
    print_step(5, "Quick Commands")
    
    print("Generate training data:")
    print("  python -m foundry synth --constitution constitutions/coding.yaml --num-samples 50")
    print("")
    print("Profile VRAM for a model:")
    print("  python -m foundry profile --model unsloth/Qwen2.5-0.5B")
    print("")
    print("Start training:")
    print("  python -m foundry train --config configs/sft_default.yaml")
    print("")
    print("Start the server (API + Frontend):")
    print("  python -m foundry serve")
    print("")
    print("Or use the start script (if on WSL/Linux):")
    print("  ./start.sh")


def main():
    """Run the quickstart wizard."""
    print("""
+==============================================================+
|                                                              |
|   T H E   F O U N D R Y  --  Quickstart Wizard               |
|                                                              |
+==============================================================+
""")
    
    # Import here to catch any import errors
    try:
        from foundry.data_engine.constitution import Constitution
    except ImportError as e:
        print(f"Error importing Foundry modules: {e}")
        print("Make sure you've installed the package: pip install -e .")
        sys.exit(1)
    
    hw = check_environment()
    check_api_keys()
    list_constitutions()
    list_configs()
    show_commands()
    
    print("\n" + "="*60)
    print("Quickstart complete! You're ready to train.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
