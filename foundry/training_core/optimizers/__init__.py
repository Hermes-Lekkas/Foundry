# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Optimizers — Muon-AdamW hybrid and standard optimizers."""


def create_hybrid_optimizer(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Lazy wrapper — defers torch import until actually called."""
    from foundry.training_core.optimizers.hybrid import create_hybrid_optimizer as _create

    return _create(*args, **kwargs)


__all__ = ["create_hybrid_optimizer"]
