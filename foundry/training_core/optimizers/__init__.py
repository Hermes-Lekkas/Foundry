# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Optimizers — Muon-AdamW hybrid and standard optimizers."""


def create_hybrid_optimizer(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Lazy wrapper — defers torch import until actually called."""
    from foundry.training_core.optimizers.hybrid import create_hybrid_optimizer as _create

    return _create(*args, **kwargs)


__all__ = ["create_hybrid_optimizer"]
