# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Hardware detection — GPU, CUDA, WSL2, and platform profiling."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional


class HardwareTier(str, Enum):
    """VRAM-based hardware tiers with recommended configurations."""

    TIER_8GB = "8gb"
    TIER_12GB = "12gb"
    TIER_24GB = "24gb"
    TIER_48GB = "48gb_plus"
    CPU_ONLY = "cpu_only"


class PlatformType(str, Enum):
    """Execution platform with multiprocessing implications."""

    LINUX_NATIVE = "linux_native"
    WSL2 = "wsl2"
    WINDOWS_NATIVE = "windows_native"
    MACOS = "macos"
    DOCKER = "docker"


# ── Recommended configs per tier ──────────────────────────────────────────────

TIER_CONFIGS: dict[HardwareTier, dict] = {
    HardwareTier.TIER_8GB: {
        "max_model_params": "1B",
        "recommended_models": ["unsloth/Qwen2.5-0.5B", "unsloth/SmolLM2-360M"],
        "quantization": "4bit-nf4",
        "max_seq_len": 2048,
        "gradient_checkpointing": True,
        "batch_size_hint": 2,
    },
    HardwareTier.TIER_12GB: {
        "max_model_params": "3B",
        "recommended_models": ["unsloth/Qwen2.5-1.5B", "unsloth/Llama-3.2-1B"],
        "quantization": "4bit-nf4",
        "max_seq_len": 4096,
        "gradient_checkpointing": True,
        "batch_size_hint": 4,
    },
    HardwareTier.TIER_24GB: {
        "max_model_params": "14B",
        "recommended_models": [
            "unsloth/Qwen2.5-7B",
            "unsloth/Mistral-Small-24B-Instruct-2501",
        ],
        "quantization": "4bit-nf4",
        "max_seq_len": 8192,
        "gradient_checkpointing": True,
        "batch_size_hint": 8,
    },
    HardwareTier.TIER_48GB: {
        "max_model_params": "70B",
        "recommended_models": [
            "unsloth/Qwen2.5-32B",
            "unsloth/Llama-3.3-70B",
        ],
        "quantization": "4bit-nf4",
        "max_seq_len": 8192,
        "gradient_checkpointing": True,
        "batch_size_hint": 16,
    },
    HardwareTier.CPU_ONLY: {
        "max_model_params": "0.5B",
        "recommended_models": ["unsloth/SmolLM2-135M"],
        "quantization": "none",
        "max_seq_len": 512,
        "gradient_checkpointing": False,
        "batch_size_hint": 1,
    },
}


@dataclass
class GPUInfo:
    """Detected GPU information."""

    name: str = "None"
    vram_total_mb: int = 0
    vram_free_mb: int = 0
    cuda_version: str = "N/A"
    driver_version: str = "N/A"
    compute_capability: tuple[int, int] = (0, 0)

    @property
    def vram_total_gb(self) -> float:
        return self.vram_total_mb / 1024

    @property
    def vram_free_gb(self) -> float:
        return self.vram_free_mb / 1024


@dataclass
class HardwareProfile:
    """Complete hardware profile for The Foundry."""

    platform: PlatformType
    gpu: GPUInfo
    tier: HardwareTier
    cpu_count: int
    ram_total_gb: float
    dataset_num_proc: int
    is_wsl2: bool
    cuda_available: bool
    torch_version: str = "N/A"
    recommendations: list[str] = field(default_factory=list)

    @property
    def tier_config(self) -> dict:
        return TIER_CONFIGS[self.tier]

    def summary(self) -> str:
        lines = [
            f"[bold]Platform:[/]   {self.platform.value}",
            f"[bold]GPU:[/]        {self.gpu.name}",
            f"[bold]VRAM:[/]       {self.gpu.vram_total_gb:.1f} GB total / {self.gpu.vram_free_gb:.1f} GB free",
            f"[bold]CUDA:[/]       {self.gpu.cuda_version}  |  Driver: {self.gpu.driver_version}",
            f"[bold]PyTorch:[/]    {self.torch_version}",
            f"[bold]Tier:[/]       {self.tier.value}",
            f"[bold]CPUs:[/]       {self.cpu_count}  |  RAM: {self.ram_total_gb:.1f} GB",
            f"[bold]Data workers:[/] {self.dataset_num_proc}",
        ]
        if self.recommendations:
            lines.append("")
            lines.append("[bold yellow]Recommendations:[/]")
            for rec in self.recommendations:
                lines.append(f"  [yellow]>[/] {rec}")
        return "\n".join(lines)


def _detect_platform() -> tuple[PlatformType, bool]:
    """Detect execution platform and WSL2 status."""
    system = platform.system().lower()

    if system == "darwin":
        return PlatformType.MACOS, False

    # Check for Docker
    if Path("/.dockerenv").exists():
        return PlatformType.DOCKER, False

    if system == "linux":
        # Check for WSL2
        try:
            with open("/proc/version", "r") as f:
                version_str = f.read().lower()
            if "microsoft" in version_str or "wsl" in version_str:
                return PlatformType.WSL2, True
        except FileNotFoundError:
            pass
        return PlatformType.LINUX_NATIVE, False

    if system == "windows":
        return PlatformType.WINDOWS_NATIVE, False

    return PlatformType.LINUX_NATIVE, False


def _detect_gpu() -> tuple[GPUInfo, bool]:
    """Detect GPU via pynvml, fall back to torch.cuda."""
    gpu = GPUInfo()
    cuda_available = False

    # Try pynvml first
    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu.name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(gpu.name, bytes):
            gpu.name = gpu.name.decode()
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        gpu.vram_total_mb = mem_info.total // (1024 * 1024)
        gpu.vram_free_mb = mem_info.free // (1024 * 1024)
        gpu.driver_version = pynvml.nvmlSystemGetDriverVersion()
        if isinstance(gpu.driver_version, bytes):
            gpu.driver_version = gpu.driver_version.decode()
        cuda_available = True
        pynvml.nvmlShutdown()
    except Exception:
        pass

    # Try torch as fallback / supplement
    try:
        import torch

        if torch.cuda.is_available():
            cuda_available = True
            if gpu.name == "None":
                gpu.name = torch.cuda.get_device_name(0)
            if gpu.vram_total_mb == 0:
                props = torch.cuda.get_device_properties(0)
                gpu.vram_total_mb = props.total_mem // (1024 * 1024)
                gpu.vram_free_mb = gpu.vram_total_mb  # conservative estimate
            gpu.compute_capability = torch.cuda.get_device_capability(0)
            gpu.cuda_version = torch.version.cuda or "N/A"
    except Exception:
        pass

    # nvidia-smi fallback for CUDA version
    if gpu.cuda_version == "N/A":
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                gpu.driver_version = result.stdout.strip()
                cuda_available = True
        except Exception:
            pass

    return gpu, cuda_available


def _classify_tier(vram_mb: int) -> HardwareTier:
    """Classify hardware tier based on VRAM."""
    if vram_mb == 0:
        return HardwareTier.CPU_ONLY
    if vram_mb < 10 * 1024:
        return HardwareTier.TIER_8GB
    if vram_mb < 20 * 1024:
        return HardwareTier.TIER_12GB
    if vram_mb < 40 * 1024:
        return HardwareTier.TIER_24GB
    return HardwareTier.TIER_48GB


@lru_cache(maxsize=1)
def detect_hardware() -> HardwareProfile:
    """Run full hardware detection and return a HardwareProfile."""
    plat, is_wsl2 = _detect_platform()
    gpu, cuda_available = _detect_gpu()
    tier = _classify_tier(gpu.vram_total_mb)
    cpu_count = os.cpu_count() or 1

    # RAM detection
    ram_gb = 0.0
    try:
        import psutil

        ram_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        # Fallback for Linux/WSL2
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        ram_gb = int(line.split()[1]) / (1024**2)
                        break
        except Exception:
            ram_gb = 0.0

    # Multiprocessing config
    if plat == PlatformType.WINDOWS_NATIVE:
        dataset_num_proc = 1
    else:
        dataset_num_proc = max(1, cpu_count)

    # PyTorch version
    torch_version = "N/A"
    try:
        import torch

        torch_version = torch.__version__
    except ImportError:
        pass

    # Build recommendations
    recommendations: list[str] = []
    if plat == PlatformType.WINDOWS_NATIVE:
        recommendations.append(
            "Running on native Windows. STRONGLY recommend WSL2 (Ubuntu) "
            "for full multiprocessing support (dataset_num_proc=1 vs "
            f"{cpu_count} on WSL2). Install WSL2: `wsl --install`"
        )
    if not cuda_available:
        recommendations.append(
            "No CUDA GPU detected. Training will be CPU-only and very slow. "
            "Consider using a CUDA-capable NVIDIA GPU."
        )
    if tier == HardwareTier.TIER_8GB:
        recommendations.append(
            "8GB VRAM tier: stick to 0.5B-1B models with 4-bit QLoRA and "
            "gradient checkpointing. Use short sequence lengths (2048)."
        )

    return HardwareProfile(
        platform=plat,
        gpu=gpu,
        tier=tier,
        cpu_count=cpu_count,
        ram_total_gb=ram_gb,
        dataset_num_proc=dataset_num_proc,
        is_wsl2=is_wsl2,
        cuda_available=cuda_available,
        torch_version=torch_version,
        recommendations=recommendations,
    )
