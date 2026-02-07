#!/usr/bin/env python3
"""Environment validation script for The Foundry.

Run: python scripts/check_env.py
Or:  python -m foundry check-env
"""

from __future__ import annotations

import sys


def main() -> int:
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    console.print("\n[bold cyan]⚒  The Foundry — Environment Check  ⚒[/]\n")

    from foundry.config.hardware import detect_hardware

    hw = detect_hardware()
    console.print(Panel(hw.summary(), title="Hardware Profile", border_style="cyan"))

    # Dependency checks
    console.print("\n[bold]Dependency Status:[/]")
    deps = {
        "torch": "Training (GPU acceleration)",
        "transformers": "Model loading",
        "trl": "SFT/DPO/GRPO trainers",
        "peft": "LoRA/QLoRA adapters",
        "unsloth": "Optimized training kernels",
        "datasets": "Data loading & processing",
        "pynvml": "GPU monitoring",
        "fastapi": "API server",
    }
    all_ok = True
    for pkg, purpose in deps.items():
        try:
            __import__(pkg)
            console.print(f"  [green]OK[/]  {pkg} — {purpose}")
        except ImportError:
            console.print(f"  [red]MISSING[/]  {pkg} — {purpose}")
            all_ok = False

    # Sandbox check
    console.print("\n[bold]Sandbox Status:[/]")
    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, "-c", "print('sandbox_ok')"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip() == "sandbox_ok":
            console.print("  [green]OK[/]  Subprocess sandbox functional")
        else:
            console.print("  [red]FAIL[/]  Subprocess sandbox returned unexpected output")
    except Exception as e:
        console.print(f"  [red]FAIL[/]  Subprocess sandbox: {e}")

    # Docker check
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            console.print(f"  [green]OK[/]  Docker available (v{result.stdout.strip()})")
        else:
            console.print("  [yellow]SKIP[/]  Docker not available (optional)")
    except FileNotFoundError:
        console.print("  [yellow]SKIP[/]  Docker not installed (optional)")

    console.print()
    if all_ok:
        console.print("[bold green]Environment is ready for The Foundry.[/]\n")
        return 0
    else:
        console.print("[bold yellow]Some dependencies are missing. Install with:[/]")
        console.print("  pip install -e '.[all]'\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
