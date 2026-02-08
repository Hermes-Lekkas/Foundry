# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Muon-AdamW Hybrid Optimizer — Novel optimizer partitioning.

Muon for 2D matrix parameters (attention projections, MLP weights):
  Uses Newton-Schulz orthogonalization for rapid convergence.

AdamW for 1D vector parameters (LayerNorm, biases, embeddings):
  Standard adaptive optimizer for non-matrix params.

Bundled standalone Muon implementation for PyTorch < 2.10.
Auto-upgrades to torch.optim.Muon when available.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import torch
from torch.optim import AdamW, Optimizer

logger = logging.getLogger(__name__)


class Muon(Optimizer):
    """Standalone Muon optimizer for PyTorch < 2.10.

    Muon uses Newton-Schulz iteration to approximate the matrix
    square root inverse for preconditioning, achieving rapid
    convergence on matrix-shaped parameters.
    """

    def __init__(
        self,
        params: Any,
        lr: float = 0.02,
        momentum: float = 0.95,
        ns_steps: int = 5,
        weight_decay: float = 0.0,
    ) -> None:
        defaults = {
            "lr": lr,
            "momentum": momentum,
            "ns_steps": ns_steps,
            "weight_decay": weight_decay,
        }
        super().__init__(params, defaults)

    @staticmethod
    def _newton_schulz_approx(G: torch.Tensor, steps: int = 5) -> torch.Tensor:
        """Approximate matrix sign via Newton-Schulz iteration.

        Computes an approximation of G @ (G^T @ G)^{-1/2}.
        """
        assert G.ndim == 2, "Newton-Schulz requires 2D matrix"
        a, b, c = (3.4445, -4.7750, 2.0315)

        # Normalize
        X = G.float()
        norm = X.norm()
        if norm < 1e-7:
            return G
        X = X / norm

        if X.shape[0] > X.shape[1]:
            X = X.T
            transposed = True
        else:
            transposed = False

        # Iterate
        for _ in range(steps):
            A = X @ X.T
            B = b * A + c * A @ A
            X = a * X + B @ X

        if transposed:
            X = X.T

        return X.to(G.dtype)

    @torch.no_grad()
    def step(self, closure: Any = None) -> torch.Tensor | None:
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            lr = group["lr"]
            momentum = group["momentum"]
            ns_steps = group["ns_steps"]
            wd = group["weight_decay"]

            for p in group["params"]:
                if p.grad is None:
                    continue
                g = p.grad

                # Weight decay (decoupled)
                if wd > 0:
                    p.mul_(1 - lr * wd)

                state = self.state[p]
                if "momentum_buffer" not in state:
                    state["momentum_buffer"] = torch.zeros_like(g)

                buf = state["momentum_buffer"]
                buf.mul_(momentum).add_(g)

                if g.ndim == 2:
                    # Apply Newton-Schulz preconditioning
                    update = self._newton_schulz_approx(buf, steps=ns_steps)
                else:
                    update = buf

                p.add_(update, alpha=-lr)

        return loss


def _get_muon_class() -> type[Optimizer]:
    """Get the best available Muon implementation."""
    try:
        from torch.optim import Muon as TorchMuon

        logger.info("Using torch.optim.Muon (PyTorch >= 2.10)")
        return TorchMuon
    except ImportError:
        logger.info("Using bundled Muon implementation")
        return Muon


def partition_params(
    model: torch.nn.Module,
) -> tuple[list[torch.nn.Parameter], list[torch.nn.Parameter]]:
    """Partition model parameters into Muon-eligible (2D) and AdamW-eligible (1D/other).

    2D matrix params: attention Q/K/V/O projections, MLP gate/up/down
    1D vector params: LayerNorm weights, biases, embeddings
    """
    muon_params: list[torch.nn.Parameter] = []
    adamw_params: list[torch.nn.Parameter] = []

    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue

        if param.ndim >= 2 and "norm" not in name.lower() and "embed" not in name.lower():
            muon_params.append(param)
        else:
            adamw_params.append(param)

    logger.info(
        "Optimizer partition: %d Muon params (2D), %d AdamW params (1D/other)",
        len(muon_params),
        len(adamw_params),
    )
    return muon_params, adamw_params


def create_hybrid_optimizer(
    model: torch.nn.Module,
    muon_lr: float = 0.02,
    adamw_lr: float = 2e-4,
    muon_momentum: float = 0.95,
    ns_steps: int = 5,
    adamw_betas: tuple[float, float] = (0.9, 0.999),
    weight_decay: float = 0.01,
) -> list[dict[str, Any]]:
    """Create Muon-AdamW hybrid optimizer parameter groups.

    Returns parameter groups compatible with HuggingFace Trainer.
    For use with custom training loops or TRL trainers.
    """
    muon_params, adamw_params = partition_params(model)

    MuonClass = _get_muon_class()

    # Build separate optimizers
    optimizers = []

    if muon_params:
        muon_opt = MuonClass(
            muon_params,
            lr=muon_lr,
            momentum=muon_momentum,
            ns_steps=ns_steps,
        )
        optimizers.append(("muon", muon_opt))

    if adamw_params:
        adamw_opt = AdamW(
            adamw_params,
            lr=adamw_lr,
            betas=adamw_betas,
            weight_decay=weight_decay,
        )
        optimizers.append(("adamw", adamw_opt))

    return optimizers


class HybridOptimizer:
    """Wrapper that steps multiple optimizers together.

    Combines Muon (for matrix params) and AdamW (for vector params)
    into a single optimizer-like interface.
    """

    def __init__(self, optimizers: list[tuple[str, Optimizer]]) -> None:
        self.optimizers = optimizers

    def zero_grad(self, set_to_none: bool = True) -> None:
        for _, opt in self.optimizers:
            opt.zero_grad(set_to_none=set_to_none)

    def step(self, closure: Any = None) -> None:
        for _, opt in self.optimizers:
            opt.step(closure)

    def state_dict(self) -> dict[str, Any]:
        return {name: opt.state_dict() for name, opt in self.optimizers}

    def load_state_dict(self, state_dict: dict[str, Any]) -> None:
        for name, opt in self.optimizers:
            if name in state_dict:
                opt.load_state_dict(state_dict[name])

    @property
    def param_groups(self) -> list[dict[str, Any]]:
        groups = []
        for _, opt in self.optimizers:
            groups.extend(opt.param_groups)
        return groups
