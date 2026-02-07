# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Tests for the Muon-AdamW hybrid optimizer."""

import pytest

torch = pytest.importorskip("torch")

from foundry.training_core.optimizers.hybrid import (
    Muon,
    partition_params,
    HybridOptimizer,
)


def test_muon_instantiation():
    """Test that Muon can be instantiated (no GPU needed)."""
    import torch
    params = [torch.randn(4, 4, requires_grad=True)]
    opt = Muon(params, lr=0.02)
    assert opt is not None
    assert len(opt.param_groups) == 1


def test_muon_step():
    """Test Muon can take a step on CPU."""
    import torch
    param = torch.randn(4, 4, requires_grad=True)
    opt = Muon([param], lr=0.02, ns_steps=3)

    # Simulate gradient
    loss = (param ** 2).sum()
    loss.backward()
    opt.step()
    opt.zero_grad()


def test_newton_schulz():
    """Test Newton-Schulz approximation runs on CPU."""
    import torch
    G = torch.randn(4, 8)
    result = Muon._newton_schulz_approx(G, steps=3)
    assert result.shape == G.shape


def test_partition_params():
    """Test parameter partitioning logic."""
    import torch

    class DummyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.linear = torch.nn.Linear(8, 8)  # 2D weight + 1D bias
            self.norm = torch.nn.LayerNorm(8)      # 1D

    model = DummyModel()
    muon_params, adamw_params = partition_params(model)

    # linear.weight should be Muon (2D), linear.bias + norm params should be AdamW
    assert len(muon_params) == 1  # linear.weight
    assert len(adamw_params) == 3  # linear.bias + norm.weight + norm.bias


def test_hybrid_optimizer():
    """Test the HybridOptimizer wrapper."""
    import torch

    param1 = torch.randn(4, 4, requires_grad=True)
    param2 = torch.randn(4, requires_grad=True)

    opt1 = Muon([param1], lr=0.02)
    opt2 = torch.optim.AdamW([param2], lr=1e-3)

    hybrid = HybridOptimizer([("muon", opt1), ("adamw", opt2)])

    # Simulate step
    loss = (param1 ** 2).sum() + (param2 ** 2).sum()
    loss.backward()
    hybrid.step()
    hybrid.zero_grad()

    # State dict
    state = hybrid.state_dict()
    assert "muon" in state
    assert "adamw" in state

    # Param groups
    groups = hybrid.param_groups
    assert len(groups) == 2
