# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Constitution System — YAML-defined principles with Jinja2 templates.

A Constitution defines the principles that guide data synthesis:
critique templates, revision templates, and weighted principles.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template

logger = logging.getLogger(__name__)


@dataclass
class Principle:
    """A single constitutional principle with critique/revision templates."""

    name: str
    description: str
    weight: float = 1.0
    domain_tags: list[str] = field(default_factory=list)
    critique_template: str = ""
    revision_template: str = ""

    def render_critique(self, **kwargs: Any) -> str:
        return Template(self.critique_template).render(**kwargs)

    def render_revision(self, **kwargs: Any) -> str:
        return Template(self.revision_template).render(**kwargs)


@dataclass
class Constitution:
    """A complete constitution — a set of weighted principles."""

    name: str
    description: str = ""
    version: str = "1.0"
    principles: list[Principle] = field(default_factory=list)
    system_prompt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> Constitution:
        """Load a constitution from a YAML file."""
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        principles = []
        for p in data.get("principles", []):
            principles.append(Principle(
                name=p["name"],
                description=p.get("description", ""),
                weight=p.get("weight", 1.0),
                domain_tags=p.get("domain_tags", []),
                critique_template=p.get("critique_template", DEFAULT_CRITIQUE),
                revision_template=p.get("revision_template", DEFAULT_REVISION),
            ))
        return cls(
            name=data.get("name", path.stem),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            principles=principles,
            system_prompt=data.get("system_prompt", ""),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Constitution:
        principles = []
        for p in data.get("principles", []):
            principles.append(Principle(**p))
        return cls(
            name=data.get("name", "custom"),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            principles=principles,
            system_prompt=data.get("system_prompt", ""),
            metadata=data.get("metadata", {}),
        )

    def weighted_principles(self) -> list[Principle]:
        """Return principles sorted by weight (highest first)."""
        return sorted(self.principles, key=lambda p: p.weight, reverse=True)

    def principles_for_domain(self, domain: str) -> list[Principle]:
        """Filter principles by domain tag."""
        return [
            p for p in self.principles
            if not p.domain_tags or domain in p.domain_tags
        ]


# ── Default templates ─────────────────────────────────────────────────────────

DEFAULT_CRITIQUE = """Review the following response for adherence to the principle: "{{ principle.description }}"

Response to critique:
{{ response }}

Identify specific issues where the response violates or could better adhere to this principle. Be concrete and actionable."""

DEFAULT_REVISION = """Revise the following response to better adhere to the principle: "{{ principle.description }}"

Original response:
{{ response }}

Critique:
{{ critique }}

Provide an improved version that addresses the identified issues while maintaining helpfulness and accuracy."""
