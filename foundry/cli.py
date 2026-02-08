# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""The Foundry CLI — Command-line interface for all Foundry operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
def config(
    show: bool = typer.Option(True, help="Show current configuration"),
    teacher: Optional[str] = typer.Option(None, help="Set teacher provider (anthropic/openai/local)"),
    teacher_model: Optional[str] = typer.Option(None, help="Set teacher model name"),
) -> None:
    """View and configure teacher/student model settings."""
    from foundry.config.settings import get_settings
    from foundry.config.hardware import detect_hardware
    
    settings = get_settings()
    hw = detect_hardware()
    
    # Update settings if provided
    if teacher:
        # This would update .env file in real implementation
        console.print(f"[yellow]To permanently set teacher, edit .env:[/]")
        console.print(f'  FOUNDRY_TEACHER_PROVIDER={teacher}')
    
    if teacher_model:
        console.print(f"[yellow]To permanently set teacher model, edit .env:[/]")
        console.print(f'  FOUNDRY_TEACHER_MODEL={teacher_model}')
    
    if show:
        console.print(_banner())
        console.print()
        
        # Teacher Configuration
        teacher_table = Table(title="[bold cyan]Teacher Model Configuration[/]", border_style="cyan")
        teacher_table.add_column("Setting", style="dim")
        teacher_table.add_column("Value", style="green")
        teacher_table.add_column("Status", style="yellow")
        
        teacher_provider = teacher or settings.teacher_provider
        teacher_model_name = teacher_model or settings.teacher_model
        
        # Check API key status
        if teacher_provider == "anthropic":
            api_status = "[green]API Key Set[/]" if settings.anthropic_api_key else "[red]Missing API Key[/]"
            mode = "[blue]Online (API)"
        elif teacher_provider == "openai":
            api_status = "[green]API Key Set[/]" if settings.openai_api_key else "[red]Missing API Key[/]"
            mode = "[blue]Online (API)"
        else:
            api_status = "[green]Local Model[/]"
            mode = "[green]Offline (Local)"
        
        teacher_table.add_row("Provider", teacher_provider, mode)
        teacher_table.add_row("Model", teacher_model_name, api_status)
        teacher_table.add_row("Mode", "Online" if teacher_provider in ("anthropic", "openai") else "Offline", "")
        
        console.print(teacher_table)
        console.print()
        
        # Student Configuration
        student_table = Table(title="[bold green]Student Model Configuration (Training Target)[/]", border_style="green")
        student_table.add_column("Setting", style="dim")
        student_table.add_column("Value", style="green")
        
        student_table.add_row("Default Model", settings.default_model)
        student_table.add_row("Checkpoint Dir", str(settings.checkpoint_dir))
        student_table.add_row("Hardware Tier", hw.tier.value)
        student_table.add_row("Recommended Models", ", ".join(hw.tier_config.get("recommended_models", ["N/A"])))
        
        console.print(student_table)
        console.print()
        
        # How to configure
        config_help = """
[bold]How to Configure:[/]

[b]Teacher (Data Synthesis):[/b]
  • Online (API): Set FOUNDRY_TEACHER_PROVIDER=anthropic/openai + API key in .env
  • Offline (Local): Set FOUNDRY_TEACHER_PROVIDER=local + FOUNDRY_TEACHER_MODEL=model-name

[b]Student (Training Target):[/b]
  • Edit the training config YAML (configs/*.yaml) or pass --config
  • Set model_name: to any HuggingFace or Unsloth model

[b]Override per-run:[/b]
  foundry synth --teacher local --teacher-model unsloth/Qwen2.5-1.5B-Instruct
        """
        console.print(Panel(config_help, title="[bold]Configuration Guide[/]", border_style="yellow"))


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
    pipeline: str = typer.Option("trajectory", help="Pipeline type (trajectory/sl_cai/rl_cai)"),
    teacher: Optional[str] = typer.Option(None, help="Teacher provider (anthropic/openai/local)"),
    teacher_model: Optional[str] = typer.Option(None, help="Teacher model name"),
) -> None:
    """Generate verified training data using constitutional synthesis.
    
    [bold]Teacher Selection:[/] (who generates the training data)
    • Online: --teacher anthropic --teacher-model claude-sonnet-4-5-20250929
    • Online: --teacher openai --teacher-model gpt-4
    • Offline: --teacher local --teacher-model unsloth/Qwen2.5-1.5B-Instruct
    
    [bold]Pipeline Types:[/]
    • trajectory: Verifiable tool-use trajectories (default)
    • sl_cai: Supervised Learning with Constitutional AI
    • rl_cai: Preference pairs for DPO training
    """
    console.print(_banner())
    console.print(f"\n[bold]Synthesizing data with:[/] {constitution}")
    console.print(f"[bold]Pipeline:[/] {pipeline}")
    if teacher:
        console.print(f"[bold]Teacher:[/] {teacher} / {teacher_model or 'default'}")
    console.print()

    import asyncio

    from foundry.data_engine.pipelines.manager import run_synthesis

    asyncio.run(
        run_synthesis(
            constitution_path=constitution,
            num_samples=num_samples,
            output_dir=output,
            pipeline_type=pipeline,
            teacher_provider=teacher,
            teacher_model=teacher_model,
        )
    )


@app.command()
def train(
    config: Path = typer.Option(..., help="Path to training config YAML"),
    model: Optional[str] = typer.Option(None, help="Override student model name"),
) -> None:
    """Run a training job with profiled VRAM ceiling.
    
    [bold]Student Model[/] (what gets trained) is defined in the config YAML.
    Use --model to override the config's model_name.
    """
    console.print(_banner())
    console.print(f"\n[bold]Starting training with:[/] {config}\n")
    
    if model:
        console.print(f"[yellow]Overriding student model to:[/] {model}\n")

    import asyncio

    from foundry.training_core.run import run_training

    asyncio.run(run_training(config_path=config, model_override=model))


@app.command()
def eval(
    model: Path = typer.Option(..., help="Path to model or checkpoint"),
    benchmark: str = typer.Option("all", help="Benchmark suite to run"),
    judge: Optional[str] = typer.Option(None, help="Judge model for evaluation (local/API)"),
) -> None:
    """Evaluate a model with Prometheus judge and benchmarks."""
    console.print(_banner())
    console.print(f"\n[bold]Evaluating:[/] {model}")
    if judge:
        console.print(f"[bold]Judge:[/] { judge}")
    console.print()

    import asyncio

    from foundry.evaluator.run import run_evaluation

    asyncio.run(run_evaluation(model_path=model, benchmark=benchmark, judge_model=judge))


@app.command()
def security(
    action: str = typer.Argument(..., help="Action: status, validate, audit, verify"),
    file: Optional[Path] = typer.Option(None, help="File to validate"),
    recent: int = typer.Option(50, help="Number of recent audit events to show"),
) -> None:
    """Security management and audit.
    
    The Foundry uses a multi-layer security architecture:
    - Static code analysis (Python)
    - Rust-based sandbox with resource limits
    - Immutable audit logging
    - Behavioral threat detection
    
    Examples:
        foundry security status              # Show security status
        foundry security validate --file x.py # Validate code
        foundry security audit               # Show recent audit events
        foundry security verify              # Verify audit integrity
    """
    console.print(_banner())
    console.print("\n[bold red]Security Management[/]\n")
    
    from foundry.security import SecurityManager
    
    if action == "status":
        security_mgr = SecurityManager()
        status = security_mgr.check_security_status()
        
        console.print(Panel(
            f"[bold]Rust Engine:[/] {'[OK] Available' if status['rust_engine_available'] else '[MISSING] Not Available'}\n"
            f"[bold]Rust Active:[/] {'[OK] Yes' if status['rust_engine_active'] else '[MISSING] No (using Python fallback)'}\n"
            f"[bold]Audit Logging:[/] {'[OK] Enabled' if status['audit_logging_enabled'] else '[MISSING] Disabled'}\n"
            f"[bold]Code Validation:[/] {'[OK] Enabled' if status['code_validation_enabled'] else '[MISSING] Disabled'}\n"
            f"[bold]Platform:[/] {status.get('platform', 'unknown')}\n"
            f"[bold]Recent Events:[/] {status['recent_events']}",
            title="[bold]Security Status[/]",
            border_style="green"
        ))
        
        if not status['rust_engine_available']:
            console.print("\n[yellow]To enable Rust security engine:[/]")
            console.print("  cd security_engine && cargo build --release && maturin develop")
    
    elif action == "validate":
        if not file:
            console.print("[red]Error: --file required for validation[/]")
            raise typer.Exit(1)
        
        from foundry.security.validator import CodeSecurityValidator
        
        code = file.read_text()
        validator = CodeSecurityValidator()
        result = validator.validate(code)
        
        if result.is_safe:
            console.print(Panel(
                "[bold green]Code is safe[/]\n"
                f"Imports: {', '.join(result.imports[:10]) or 'none'}",
                border_style="green"
            ))
        else:
            console.print(Panel(
                "[bold red]Security threats detected[/]\n\n"
                + "\n".join(f"  • {t}" for t in result.threats),
                border_style="red"
            ))
        
        if result.warnings:
            console.print("\n[yellow]Warnings:[/]")
            for w in result.warnings:
                console.print(f"  • {w}")
    
    elif action == "audit":
        from foundry.security.audit import SecurityAuditLogger
        
        logger = SecurityAuditLogger()
        events = logger.get_recent(recent)
        
        console.print(f"[bold]Recent {len(events)} Audit Events:[/]\n")
        
        for event in events:
            console.print(f"[dim]{event.timestamp_human}[/] "
                         f"[{event.event_type}] "
                         f"{event.code_hash[:8] if event.code_hash else '-'}")
        
        stats = logger.get_statistics()
        console.print(f"\n[dim]Total events: {stats['total_events']} | "
                     f"Integrity: {'[OK] Verified' if stats['integrity_verified'] else '[FAIL] Failed'}[/]")
    
    elif action == "verify":
        from foundry.security.audit import SecurityAuditLogger
        
        logger = SecurityAuditLogger()
        is_valid = logger.verify_integrity()
        
        if is_valid:
            console.print(Panel(
                "[bold green]Audit log integrity verified[/]\n"
                "The audit chain is intact and has not been tampered with.",
                border_style="green"
            ))
        else:
            console.print(Panel(
                "[bold red]AUDIT LOG INTEGRITY FAILED[/]\n"
                "The audit log may have been tampered with!",
                border_style="red"
            ))
            raise typer.Exit(1)
    
    else:
        console.print(f"[red]Unknown action: {action}[/]")
        console.print("Available: status, validate, audit, verify")


@app.command()
def reflect(
    question: str = typer.Option(..., help="Question to test reasoning on"),
    answer: str = typer.Option(..., help="Model's answer"),
    explanation: str = typer.Option(..., help="Model's explanation"),
    teacher: Optional[str] = typer.Option(None, help="Teacher model for remediation"),
) -> None:
    """Test reasoning through Self-Directed Counterfactual Reflection (SDCR).
    
    This is The Foundry's killer feature - models that find and fix their own bugs.
    
    Example:
        foundry reflect \\
            --question "If train travels 60km in 30min, how far in 2 hours?" \\
            --answer "240km" \\
            --explanation "60km/30min = 120km/hr. 120*2=240km"
    """
    import asyncio
    
    console.print(_banner())
    console.print("\n[bold cyan]Self-Directed Counterfactual Reflection (SDCR)[/]")
    console.print("[dim]Testing reasoning through counterfactual analysis...[/]\n")
    
    from foundry.reflection.engine import ReflectionEngine
    
    async def run_reflection():
        engine = ReflectionEngine()
        
        # Create teacher if specified
        teacher_model = None
        if teacher:
            from foundry.data_engine.pipelines.manager import _create_teacher
            teacher_model = _create_teacher(model=teacher)
        
        result = await engine.reflect(
            question=question,
            answer=answer,
            explanation=explanation,
            teacher_model=teacher_model,
        )
        
        # Display results
        console.print(Panel(
            f"[bold]Question:[/] {result.original_question}\n"
            f"[bold]Answer:[/] {result.original_answer}\n"
            f"[bold]Counterfactuals Generated:[/] {result.counterfactuals_generated}\n"
            f"[bold]Inconsistencies Found:[/] {result.inconsistencies_found}\n"
            f"[bold]Initial Consistency:[/] {result.consistency_score:.2%}\n"
            f"[bold]Remediation:[/] {'Yes' if result.remediation_attempted else 'No'}\n"
            f"[bold]Final Consistency:[/] {result.final_consistency_score:.2%}\n"
            f"[bold]Execution Time:[/] {result.execution_time_seconds:.2f}s",
            title="[bold]Reflection Results[/]",
            border_style="green" if result.was_reflection_successful else "red"
        ))
        
        # Show detailed report if available
        if result.detailed_report and "initial_report" in result.detailed_report:
            report = result.detailed_report["initial_report"]
            if report.get("violations"):
                console.print("\n[bold red]Inconsistencies Detected:[/]")
                for v in report["violations"]:
                    console.print(f"  • [yellow]{v['type']}[/]: {v['description']}")
                    console.print(f"    [dim]Concept: {v['concept']}[/]")
    
    asyncio.run(run_reflection())


@app.command()
def lineage(
    model_id: Optional[str] = typer.Option(None, help="Show lineage for specific model"),
    list_all: bool = typer.Option(False, help="List all registered models"),
    certificate: Optional[str] = typer.Option(None, help="Generate certificate for model ID"),
) -> None:
    """View model DNA, lineage, and family trees."""
    from foundry.models.dna import get_lineage_tracker, ModelDNA
    
    console.print(_banner())
    console.print()
    
    tracker = get_lineage_tracker()
    
    if certificate:
        try:
            dna = ModelDNA.load(tracker.registry_dir / f"{certificate}.json")
            console.print(dna.generate_certificate())
        except FileNotFoundError:
            console.print(f"[red]Model '{certificate}' not found in registry[/]")
        return
    
    if list_all:
        models = tracker.list_models()
        if not models:
            console.print("[yellow]No models registered yet. Train a model to see it here![/]")
            return
        
        table = Table(title="[bold]Registered Models[/]")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Base Model", style="dim")
        table.add_column("Generation", justify="right")
        table.add_column("Age (days)", justify="right")
        table.add_column("Specialties", style="yellow")
        
        for dna in models[:20]:  # Show last 20
            specs = ", ".join(dna.phenotype.specialties[:2]) if dna.phenotype.specialties else "-"
            table.add_row(
                dna.model_id,
                dna.model_name or "-",
                dna.base_model.split("/")[-1] if "/" in dna.base_model else dna.base_model,
                str(dna.generation),
                f"{dna.age_days:.1f}",
                specs,
            )
        
        console.print(table)
        console.print(f"\n[dim]Showing {min(len(models), 20)} of {len(models)} models[/]")
        return
    
    if model_id:
        tree = tracker.get_lineage(model_id)
        console.print(Panel(
            f"[bold]Model:[/] {tree['model']['model_name'] or tree['model']['model_id']}\n"
            f"[bold]Base:[/] {tree['model']['base_model']}\n"
            f"[bold]Generation:[/] {tree['model']['generation']}\n"
            f"[bold]Parents:[/] {len(tree['parents'])} | [bold]Children:[/] {len(tree['children'])}",
            title="Model Lineage",
            border_style="cyan"
        ))
        return
    
    # Default: show help
    console.print("[bold]Model Lineage Commands:[/]")
    console.print("  foundry lineage --list-all              # List all models")
    console.print("  foundry lineage --model-id <id>         # Show family tree")
    console.print("  foundry lineage --certificate <id>      # Generate certificate")


@app.command()
def models() -> None:
    """List recommended teacher and student models by hardware tier."""
    from foundry.config.hardware import detect_hardware, TIER_CONFIGS, HardwareTier
    
    console.print(_banner())
    console.print()
    
    hw = detect_hardware()
    
    # Current tier
    console.print(Panel(
        f"[bold]Your Hardware:[/] {hw.tier.value}\n"
        f"[bold]VRAM:[/] {hw.gpu.vram_total_gb:.1f} GB\n"
        f"[bold]Platform:[/] {hw.platform.value}",
        title="[bold]Detected Hardware[/]",
        border_style="cyan"
    ))
    console.print()
    
    # Teacher models table
    teacher_table = Table(title="[bold blue]Recommended Teacher Models (Data Synthesis)[/]", border_style="blue")
    teacher_table.add_column("Mode", style="cyan")
    teacher_table.add_column("Provider", style="green")
    teacher_table.add_column("Model", style="white")
    teacher_table.add_column("Best For", style="dim")
    
    teacher_table.add_row("Online", "Anthropic", "claude-sonnet-4-5-20250929", "High-quality synthesis")
    teacher_table.add_row("Online", "OpenAI", "gpt-4", "High-quality synthesis")
    teacher_table.add_row("Online", "Anthropic", "claude-haiku-20240307", "Fast, cost-effective")
    teacher_table.add_row("Offline", "Local", "unsloth/Qwen2.5-7B-Instruct", "Privacy, no API costs")
    teacher_table.add_row("Offline", "Local", "unsloth/Qwen2.5-1.5B-Instruct", "8GB VRAM compatible")
    teacher_table.add_row("Offline", "Local", "unsloth/Qwen2.5-0.5B-Instruct", "Minimal VRAM usage")
    
    console.print(teacher_table)
    console.print()
    
    # Student models by tier
    student_table = Table(title="[bold green]Recommended Student Models (Training Targets)[/]", border_style="green")
    student_table.add_column("Tier", style="cyan")
    student_table.add_column("Max Params", style="yellow")
    student_table.add_column("Recommended Models", style="white")
    
    for tier in HardwareTier:
        if tier == HardwareTier.CPU_ONLY:
            continue
        tier_config = TIER_CONFIGS[tier]
        models = "\n".join(tier_config["recommended_models"])
        student_table.add_row(
            tier.value,
            tier_config["max_model_params"],
            models
        )
    
    console.print(student_table)
    console.print()
    
    # Usage guide
    guide = """
[bold cyan]Teacher Model Selection:[/]
  [blue]Online (API):[/] Requires API key, highest quality, pay-per-use
    -> Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env
    -> Set FOUNDRY_TEACHER_PROVIDER=anthropic/openai
    
  [green]Offline (Local):[/] Runs on your GPU, private, one-time download
    -> Set FOUNDRY_TEACHER_PROVIDER=local
    -> Set FOUNDRY_TEACHER_MODEL=unsloth/Qwen2.5-1.5B-Instruct
    
[bold green]Student Model Selection:[/]
  -> Edit configs/*.yaml and set [b]model_name:[/]
  -> Or use: foundry train --config configs/sft.yaml --model unsloth/..."
    """
    console.print(Panel(guide, title="[bold]Model Selection Guide[/]", border_style="yellow"))


if __name__ == "__main__":
    app()
