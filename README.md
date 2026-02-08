# <img src="frontend/public/The_Foundry.svg" width="28" align="top" /> The Foundry

### Local LLM Training Ecosystem

**Train your own AI models with Constitutional AI, verifiable tool-use trajectories, and GRPO reasoning — all on your hardware.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License: Open Core](https://img.shields.io/badge/license-Open%20Core-blue)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen)](CONTRIBUTIONS.md)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-009688)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/ui-React%2018-61DAFB)](https://react.dev)

---

## What is The Foundry?

The Foundry is a **complete local LLM training pipeline** that synthesizes the best methodologies from Claude (Constitutional AI), GPT-5 (RLVR/GRPO), and GLM (Agentic Trajectories) into a single, GPU-aware system you run on your own machine.

```
         You
          |
    [The Foundry]
     /    |    \     \
  Data  Train  Eval  UI
  Engine Core  uator Dashboard
     \    |    /
    [Your Model]
```

### Why The Foundry?

| Problem                    | The Foundry Solution |
|----------------------------|---------------------|
| Cloud training is expensive | Runs on your GPU (8GB to 48GB+) |
| Most trainers only do basic SFT | SFT + DPO + **GRPO with sandbox-verified rewards** |
| Training data is low quality | **Constitutional AI** critique-and-revise pipelines |
| Tool-use data is mocked | **Verifiable trajectories** — real sandbox execution, no fake outputs |
| VRAM OOMs crash training | **Proactive VRAM profiler** — dry pass before training, 90% ceiling |
| Windows has multiprocessing issues | **WSL2-first** — auto-detects and configures workers |

---

## Key Features

### Data Engine — Constitutional AI + Verifiable Trajectories
- **SL-CAI Pipeline**: Generate -> Critique -> Revise -> Fine-tune
- **RL-CAI Pipeline**: Generate preference pairs for DPO training
- **Trajectory Pipeline**: Teacher generates tool calls -> **Sandbox executes them** -> Real output feeds back -> Teacher generates next step. Failed trajectories with graceful error recovery are **kept** (teaches error handling). Hallucinated success is **rejected**.
- YAML-defined constitutions with weighted principles and Jinja2 templates
- Built-in constitutions: `agentic`, `coding`, `reasoning`, `general`

### Training Core — Muon-AdamW + GRPO
- **Muon-AdamW Hybrid Optimizer**: Muon (Newton-Schulz orthogonalization) for 2D matrix params, AdamW for 1D vector params
- **GRPO Trainer** with composable reward functions:
  - Hard reward: sandbox executes code -> binary 0/1
  - Soft reward: constitutional judge -> 0.0-1.0
  - Combined: `r = alpha * hard + (1-alpha) * soft`
- **Unsloth** backend (2x faster, 60% less VRAM) with Native PyTorch fallback
- QLoRA 4-bit NF4 targeting q/k/v/o/gate/up/down projections

### Evaluator — Prometheus Judge + Benchmarks
- Prometheus 2 style direct assessment (1-5) and pairwise ranking
- LLM-as-Judge with any local or API model
- Rule-based validation (regex, JSON, keywords)
- Built-in benchmarks: math reasoning, code quality, tool use
- Model leaderboard with aggregate scoring

### VRAM Management — Profile Before You Train
- **Proactive profiler**: Dry forward+backward pass with binary search for max safe batch size
- **90% ceiling**: Caps at 90% of discovered limit to handle CUDA fragmentation
- **Cache**: Results cached per model+adapter combo — skip profiling on re-runs
- **Time-sharded toggle**: Swap Teacher/Student on the same GPU

### Crystalline Material UI
- React 18 + Tailwind glassmorphism with `backdrop-blur-[50px]` and specular highlights
- **PulsePrism**: Dynamic Island-style floating telemetry pill
- Real-time WebSocket: loss curves, VRAM gauges with profiler ceiling line
- Constitution editor, dataset browser, benchmark runner
- Dark theme with dynamic accent colors

---

## Quick Start

### Prerequisites
- Python 3.10+
- NVIDIA GPU with CUDA (8GB+ VRAM recommended)
- WSL2 (Ubuntu) recommended on Windows

### Install

```bash
# Clone
git clone https://github.com/Hermes-Lekkas/Foundry.git
cd Foundry

# Install (core)
pip install -e .

# Install (with training dependencies)
pip install -e ".[training]"

# Install (everything)
pip install -e ".[all]"
```

### Verify Environment

```bash
python -m foundry check-env
```

### Start the Server

```bash
python -m foundry serve
# API at http://localhost:8420
# WebSocket at ws://localhost:8420/ws
```

### Frontend (Development)

```bash
cd frontend
npm install
npm run dev
# UI at http://localhost:5173
```

### Teacher & Student Model Selection

The Foundry uses a **Teacher-Student** architecture:

| Role | Purpose | Where Configured |
|------|---------|------------------|
| **Teacher** | Generates training data via Constitutional AI | `.env` file or `--teacher` CLI flag |
| **Student** | The model being trained | Training config YAML or `--model` CLI flag |

#### Teacher Modes

**Online (API)** — Highest quality, requires API key:
```bash
# Configure in .env
FOUNDRY_TEACHER_PROVIDER=anthropic
FOUNDRY_TEACHER_MODEL=claude-sonnet-4-5-20250929
ANTHROPIC_API_KEY=sk-ant-...
```

**Offline (Local)** — Private, runs on your GPU:
```bash
# Configure in .env
FOUNDRY_TEACHER_PROVIDER=local
FOUNDRY_TEACHER_MODEL=unsloth/Qwen2.5-1.5B-Instruct
```

**Per-run override:**
```bash
python -m foundry synth --teacher local --teacher-model unsloth/Qwen2.5-7B-Instruct ...
```

#### View/Configure Models
```bash
# Show current configuration and available models
python -m foundry config
python -m foundry models
```

### Generate Training Data

```bash
# Verifiable trajectories with the agentic constitution
python -m foundry synth --constitution constitutions/agentic.yaml --num-samples 100

# SL-CAI (critique & revise)
python -m foundry synth --constitution constitutions/coding.yaml --num-samples 50

# Use local teacher for privacy
python -m foundry synth --constitution constitutions/coding.yaml --teacher local --teacher-model unsloth/Qwen2.5-1.5B-Instruct
```

### Profile VRAM & Train

```bash
# Profile GPU capacity
python -m foundry profile --model unsloth/Qwen2.5-0.5B

# Train with SFT
python -m foundry train --config configs/sft_default.yaml

# Train with GRPO (reasoning verification)
python -m foundry train --config configs/grpo_reasoning.yaml

# Override student model at runtime
python -m foundry train --config configs/sft_default.yaml --model unsloth/Qwen2.5-1.5B
```

### Evaluate

```bash
python -m foundry eval --model ./checkpoints/run_1
```

---

## Architecture

```
Orchestrator (FastAPI + WebSocket on :8420)
    |
    |-- Data Engine
    |       |-- Constitution System (YAML + Jinja2)
    |       |-- Teacher Abstraction (API / Local)
    |       |-- SL-CAI Pipeline (critique -> revise)
    |       |-- RL-CAI Pipeline (preference pairs)
    |       |-- Trajectory Pipeline (real execution)
    |       \-- Sandbox Executor (shared)
    |
    |-- Training Core
    |       |-- Muon-AdamW Hybrid Optimizer
    |       |-- Unsloth Backend (primary)
    |       |-- Native PyTorch Backend (fallback)
    |       |-- SFT / DPO / GRPO Trainers
    |       |-- QLoRA Adapter System
    |       \-- Telemetry -> EventBus -> WebSocket
    |
    |-- Evaluator
    |       |-- Prometheus 2 Judge
    |       |-- LLM-as-Judge
    |       |-- Rule-based Judge
    |       |-- GRPO Reward Functions (sandbox-backed)
    |       \-- Benchmark Runner
    |
    \-- Frontend (React 18 + Tailwind + Vite)
            |-- Dashboard (loss curves, VRAM gauges)
            |-- Data Engine (synthesis controls)
            |-- Training (config + live metrics)
            |-- Evaluator (benchmarks + leaderboard)
            \-- Config (hardware tiers)
```

### Hardware Tiers

| VRAM | Tier | Max Params | Recommended Models |
|------|------|-----------|-------------------|
| 8 GB | `8gb` | 1B | Qwen2.5-0.5B, SmolLM2-360M |
| 12 GB | `12gb` | 3B | Qwen2.5-1.5B, Llama-3.2-1B |
| 24 GB | `24gb` | 14B | Qwen2.5-7B, Mistral-Small-24B |
| 48+ GB | `48gb_plus` | 70B | Qwen2.5-32B, Llama-3.3-70B |

### Platform Support

| Environment | Workers | Sandbox | Recommendation |
|-------------|---------|---------|----------------|
| WSL2 (Ubuntu) | `os.cpu_count()` | subprocess + seccomp | **Recommended** |
| Linux Native | `os.cpu_count()` | subprocess + seccomp | Optimal |
| macOS | `os.cpu_count()` | subprocess + seatbelt | Optimal |
| Native Windows | 1 | subprocess + CREATE_NO_WINDOW | Use WSL2 |
| Docker | `os.cpu_count()` | Container-in-container | Alternative |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | GPU info, CUDA status, WSL2 detection |
| `GET` | `/api/config/hardware` | Full hardware profile |
| `GET` | `/api/config/tiers` | Recommended configs per tier |
| `POST` | `/api/data/synthesize` | Start data synthesis job |
| `GET` | `/api/data/datasets` | List generated datasets |
| `POST` | `/api/training/start` | Start training job |
| `POST` | `/api/training/profile` | Run VRAM profiler |
| `POST` | `/api/eval/run` | Start evaluation |
| `GET` | `/api/eval/leaderboard` | Model rankings |
| `WS` | `/ws` | Real-time telemetry stream |

---

## CLI Commands

```bash
# Environment & Configuration
python -m foundry check-env              # Verify GPU, CUDA, WSL2 status
python -m foundry config                 # View current teacher/student config
python -m foundry models                 # List recommended models by tier

# Data Synthesis (Teacher generates training data)
python -m foundry synth --constitution constitutions/coding.yaml --num-samples 100
python -m foundry synth ... --teacher local --teacher-model unsloth/Qwen2.5-7B-Instruct

# Training (Student learns from generated data)
python -m foundry profile --model unsloth/Qwen2.5-0.5B
python -m foundry train --config configs/sft_default.yaml
python -m foundry train --config configs/sft_default.yaml --model unsloth/Qwen2.5-1.5B

# Evaluation
python -m foundry eval --model ./checkpoints/run_1

# Server
python -m foundry serve                  # Start API server
python -m foundry serve --port 8080      # Custom port
```

---

## Tech Stack

**Backend**: Python 3.10+, FastAPI, Pydantic Settings, aiosqlite, Typer (CLI)
**Training**: Unsloth, TRL (SFT/DPO/GRPO), PEFT, BitsAndBytes, PyTorch
**Evaluation**: Prometheus 2 (proprietary), LLM-as-Judge, sandbox-backed rewards
**Frontend**: React 18, Vite, Tailwind CSS (glassmorphism), Zustand, Framer Motion, Recharts
**Sandbox**: Open-core subprocess isolation + Proprietary multi-layer security engine
**Reflection**: SDCR (Self-Directed Counterfactual Reflection) — proprietary innovation

---

## Contributing

We welcome contributions! Whether you're fixing bugs, improving documentation, or adding features to the open-core components:

📖 **[CONTRIBUTIONS.md](CONTRIBUTIONS.md)** — Guidelines, setup instructions, and how to get started

Key areas where help is welcome:
- Windows/WSL2 improvements
- Documentation and tutorials  
- Test coverage
- UI/UX enhancements
- Performance optimizations

---

## License: Open-Core Model

The Foundry uses an **open-core** licensing model — transparent, sustainable, and community-friendly.

### What This Means

- **🔓 Open Source (MIT)**: Core infrastructure is fully open — modify, redistribute, contribute
- **👁️ Source-Available (Proprietary)**: Unique innovations are visible but protected — you can view, study, and use them, but not modify or redistribute

### Component Breakdown

| Component | License | Status |
|-----------|---------|--------|
| `foundry/orchestrator/` | **MIT** | Open for contribution |
| `foundry/config/` | **MIT** | Open for contribution |
| `foundry/training_core/` | **MIT** | Open for contribution |
| `foundry/sandbox/` | **MIT** | Open for contribution |
| `foundry/evaluator/` (basic) | **MIT** | Open for contribution |
| `foundry/data_engine/` (basic) | **MIT** | Open for contribution |
| `frontend/` | **MIT** | Open for contribution |
| `tests/` | **MIT** | Open for contribution |
| `foundry/reflection/` (SDCR) | **Proprietary** | Source-available, view-only |
| `foundry/security/` (Multi-layer) | **Proprietary** | Source-available, view-only |
| `foundry/models/dna.py` (Lineage) | **Proprietary** | Source-available, view-only |
| Advanced Constitutional AI | **Proprietary** | Source-available, view-only |
| Prometheus Judge | **Proprietary** | Source-available, view-only |

### Why This Model?

1. **🧠 Innovation Protection**: SDCR, Model DNA, and the Security Engine represent years of R&D
2. **🤝 Community**: Anyone can contribute to the open-core infrastructure
3. **🔍 Transparency**: All code is visible — audit the proprietary modules, trust through verification
4. **💼 Sustainability**: Proprietary features fund continued open-source development

### Contributing

We actively welcome contributions! See [CONTRIBUTIONS.md](CONTRIBUTIONS.md) for guidelines.

- **MIT files**: Submit PRs freely
- **Proprietary files**: View and learn, but don't modify

See [LICENSE](LICENSE) for full legal terms.
