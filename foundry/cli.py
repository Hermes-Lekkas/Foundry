# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""The Foundry CLI — Command-line interface for all Foundry operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    name="foundry",
    help="The Foundry — Local LLM Training Ecosystem",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console(force_terminal=True)


def _banner() -> str:
    return (
        "[bold cyan]+======================================+[/]\n"
        "[bold cyan]|[/]  [bold white]T H E   F O U N D R Y[/]              [bold cyan]|[/]\n"
        "[bold cyan]|[/]  [dim]Local LLM Training Ecosystem[/]       [bold cyan]|[/]\n"
        "[bold cyan]+======================================+[/]"
    )


@app.command()
def check_env() -> None:
    """Validate GPU, CUDA, WSL2 status, and sandbox capability."""
    console.print(_banner())
    console.print()

    from foundry.config.hardware import detect_hardware

    hw = detect_hardware()
    console.print(Panel(hw.summary(), title="[bold]Hardware Profile[/]", border_style="cyan"))


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind address"),
    port: int = typer.Option(8420, help="Port number"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development"),
) -> None:
    """Start the Foundry API server."""
    console.print(_banner())
    console.print(f"\n[bold green]Starting Foundry server on {host}:{port}[/]\n")

    import uvicorn

    uvicorn.run(
        "foundry.orchestrator.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@app.command()
def profile(
    model: str = typer.Option(..., help="Model name or path to profile"),
    adapter: Optional[str] = typer.Option(None, help="Adapter config name"),
) -> None:
    """Run VRAM dry pass to determine safe batch size."""
    console.print(_banner())
    console.print(f"\n[bold]Profiling VRAM for:[/] {model}\n")

    from foundry.shared.vram import VRAMProfiler

    profiler = VRAMProfiler()
    result = profiler.profile(model_name=model, adapter_name=adapter)
    console.print(
        Panel(result.summary(), title="[bold]VRAM Profile[/]", border_style="green")
    )


@app.command()
def synth(
    constitution: Path = typer.Option(..., help="Path to constitution YAML"),
    num_samples: int = typer.Option(100, help="Number of samples to generate"),
    output: Optional[Path] = typer.Option(None, help="Output directory"),
) -> None:
    """Generate verified training data using constitutional synthesis."""
    console.print(_banner())
    console.print(f"\n[bold]Synthesizing data with:[/] {constitution}\n")

    import asyncio

    from foundry.data_engine.pipelines.manager import run_synthesis

    asyncio.run(
        run_synthesis(
            constitution_path=constitution,
            num_samples=num_samples,
            output_dir=output,
        )
    )


@app.command()
def train(
    config: Path = typer.Option(..., help="Path to training config YAML"),
) -> None:
    """Run a training job with profiled VRAM ceiling."""
    console.print(_banner())
    console.print(f"\n[bold]Starting training with:[/] {config}\n")

    import asyncio

    from foundry.training_core.run import run_training

    asyncio.run(run_training(config_path=config))


@app.command()
def eval(
    model: Path = typer.Option(..., help="Path to model or checkpoint"),
    benchmark: str = typer.Option("all", help="Benchmark suite to run"),
) -> None:
    """Evaluate a model with Prometheus judge and benchmarks."""
    console.print(_banner())
    console.print(f"\n[bold]Evaluating:[/] {model}\n")

    import asyncio

    from foundry.evaluator.run import run_evaluation

    asyncio.run(run_evaluation(model_path=model, benchmark=benchmark))


if __name__ == "__main__":
    app()
