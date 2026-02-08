# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
# See LICENSE file for full terms.

"""Model DNA — Genetic fingerprinting and lineage tracking for trained models."""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class TrainingStep:
    """A single step in a model's training history."""
    
    step_type: str
    timestamp: float
    config_hash: str
    dataset_id: Optional[str] = None
    constitution_id: Optional[str] = None
    teacher_model: Optional[str] = None
    duration_seconds: float = 0.0
    final_loss: Optional[float] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "step_type": self.step_type,
            "timestamp": self.timestamp,
            "timestamp_human": datetime.fromtimestamp(self.timestamp).isoformat(),
            "config_hash": self.config_hash,
            "dataset_id": self.dataset_id,
            "constitution_id": self.constitution_id,
            "teacher_model": self.teacher_model,
            "duration_seconds": self.duration_seconds,
            "final_loss": self.final_loss,
        }


@dataclass
class ModelPhenotype:
    """Emergent characteristics of the trained model."""
    
    capabilities: list[str] = field(default_factory=list)
    specialties: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    personality_type: str = ""
    communication_style: str = ""
    benchmark_scores: dict[str, float] = field(default_factory=dict)
    elo_rating: Optional[float] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": self.capabilities,
            "specialties": self.specialties,
            "weaknesses": self.weaknesses,
            "personality_type": self.personality_type,
            "communication_style": self.communication_style,
            "benchmark_scores": self.benchmark_scores,
            "elo_rating": self.elo_rating,
        }


@dataclass
class ModelDNA:
    """Complete genetic fingerprint of a trained model."""
    
    dna_version: str = "1.0"
    model_id: str = ""
    model_name: str = ""
    created_at: float = field(default_factory=time.time)
    genesis_hash: str = ""
    base_model: str = ""
    generation: int = 0
    parent_models: list[str] = field(default_factory=list)
    child_models: list[str] = field(default_factory=list)
    training_steps: list[TrainingStep] = field(default_factory=list)
    total_training_time: float = 0.0
    datasets_used: list[str] = field(default_factory=list)
    constitutions_used: list[str] = field(default_factory=list)
    teachers_used: list[str] = field(default_factory=list)
    phenotype: ModelPhenotype = field(default_factory=ModelPhenotype)
    tags: list[str] = field(default_factory=list)
    description: str = ""
    creator: str = ""
    license: str = "Proprietary"
    
    def __post_init__(self):
        if not self.model_id:
            self.model_id = self._generate_model_id()
    
    def _generate_model_id(self) -> str:
        """Generate a unique, pronounceable model ID."""
        hash_input = f"{self.base_model}_{self.created_at}_{id(self)}"
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()
        random.seed(int.from_bytes(hash_bytes[:4], 'big'))
        
        adjectives = [
            "fierce", "gentle", "swift", "wise", "brave", "calm", "bright", "dark",
            "golden", "silver", "iron", "crystal", "quantum", "neural", "synthetic",
            "ethereal", "vivid", "cosmic", "lunar", "solar", "dynamic", "static"
        ]
        nouns = [
            "phoenix", "dragon", "wolf", "eagle", "tiger", "bear", "hawk", "owl",
            "architect", "sage", "pioneer", "voyager", "sentinel", "artisan", "scholar",
            "nexus", "core", "spark", "pulse", "vertex", "horizon", "zenith"
        ]
        
        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        num = int.from_bytes(hash_bytes[4:6], 'big') % 1000
        
        return f"{adj}-{noun}-{num:03d}"
    
    @property
    def age_days(self) -> float:
        return (time.time() - self.created_at) / 86400
    
    @property
    def lineage_depth(self) -> int:
        return self.generation + len(self.child_models)
    
    def add_training_step(
        self,
        step_type: str,
        config: dict[str, Any],
        dataset_id: Optional[str] = None,
        constitution_id: Optional[str] = None,
        teacher_model: Optional[str] = None,
        duration_seconds: float = 0.0,
        final_loss: Optional[float] = None,
    ) -> None:
        config_hash = hashlib.sha256(
            json.dumps(config, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        step = TrainingStep(
            step_type=step_type,
            timestamp=time.time(),
            config_hash=config_hash,
            dataset_id=dataset_id,
            constitution_id=constitution_id,
            teacher_model=teacher_model,
            duration_seconds=duration_seconds,
            final_loss=final_loss,
        )
        self.training_steps.append(step)
        self.generation = len(self.training_steps)
        
        if dataset_id and dataset_id not in self.datasets_used:
            self.datasets_used.append(dataset_id)
        if constitution_id and constitution_id not in self.constitutions_used:
            self.constitutions_used.append(constitution_id)
        if teacher_model and teacher_model not in self.teachers_used:
            self.teachers_used.append(teacher_model)
        
        self.total_training_time += duration_seconds
    
    def derive_child(self, child_name: str = "") -> ModelDNA:
        child = ModelDNA(
            base_model=self.model_name or self.base_model,
            parent_models=[self.model_id],
            generation=self.generation + 1,
        )
        if child_name:
            child.model_name = child_name
        self.child_models.append(child.model_id)
        return child
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "dna_version": self.dna_version,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "created_at": self.created_at,
            "created_at_human": datetime.fromtimestamp(self.created_at).isoformat(),
            "genesis_hash": self.genesis_hash,
            "base_model": self.base_model,
            "generation": self.generation,
            "parent_models": self.parent_models,
            "child_models": self.child_models,
            "lineage_depth": self.lineage_depth,
            "age_days": round(self.age_days, 2),
            "training_steps": [s.to_dict() for s in self.training_steps],
            "total_training_time": self.total_training_time,
            "datasets_used": self.datasets_used,
            "constitutions_used": self.constitutions_used,
            "teachers_used": self.teachers_used,
            "phenotype": self.phenotype.to_dict(),
            "tags": self.tags,
            "description": self.description,
            "creator": self.creator,
            "license": self.license,
        }
    
    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
    
    @classmethod
    def load(cls, path: Path) -> ModelDNA:
        data = json.loads(Path(path).read_text())
        
        steps = [
            TrainingStep(
                step_type=s["step_type"],
                timestamp=s["timestamp"],
                config_hash=s["config_hash"],
                dataset_id=s.get("dataset_id"),
                constitution_id=s.get("constitution_id"),
                teacher_model=s.get("teacher_model"),
                duration_seconds=s.get("duration_seconds", 0.0),
                final_loss=s.get("final_loss"),
            )
            for s in data.get("training_steps", [])
        ]
        
        pheno_data = data.get("phenotype", {})
        phenotype = ModelPhenotype(
            capabilities=pheno_data.get("capabilities", []),
            specialties=pheno_data.get("specialties", []),
            weaknesses=pheno_data.get("weaknesses", []),
            personality_type=pheno_data.get("personality_type", ""),
            communication_style=pheno_data.get("communication_style", ""),
            benchmark_scores=pheno_data.get("benchmark_scores", {}),
            elo_rating=pheno_data.get("elo_rating"),
        )
        
        return cls(
            dna_version=data.get("dna_version", "1.0"),
            model_id=data["model_id"],
            model_name=data.get("model_name", ""),
            created_at=data["created_at"],
            genesis_hash=data.get("genesis_hash", ""),
            base_model=data.get("base_model", ""),
            generation=data.get("generation", 0),
            parent_models=data.get("parent_models", []),
            child_models=data.get("child_models", []),
            training_steps=steps,
            total_training_time=data.get("total_training_time", 0.0),
            datasets_used=data.get("datasets_used", []),
            constitutions_used=data.get("constitutions_used", []),
            teachers_used=data.get("teachers_used", []),
            phenotype=phenotype,
            tags=data.get("tags", []),
            description=data.get("description", ""),
            creator=data.get("creator", ""),
            license=data.get("license", "Proprietary"),
        )
    
    def generate_certificate(self) -> str:
        lines = [
            "+==============================================================+",
            "|                                                              |",
            "|           T H E   F O U N D R Y                              |",
            "|           Model Birth Certificate                            |",
            "|                                                              |",
            "+==============================================================+",
            f"|  Name:        {self.model_name or self.model_id:<47} |",
            f"|  Breed:       {self.base_model:<47} |",
            f"|  Generation:  {self.generation:<47} |",
            f"|  Born:        {datetime.fromtimestamp(self.created_at).strftime('%Y-%m-%d %H:%M'):<47} |",
            "|                                                              |",
        ]
        
        if self.phenotype.specialties:
            specs = ", ".join(self.phenotype.specialties[:3])
            lines.append(f"|  Specialties: {specs:<47} |")
        
        if self.phenotype.personality_type:
            lines.append(f"|  Personality: {self.phenotype.personality_type:<47} |")
        
        lines.extend([
            "|                                                              |",
            f"|  Lineage:     {len(self.parent_models)} ancestors, {len(self.child_models)} children{'':<20} |",
            "|                                                              |",
            f"|  Model ID:    {self.model_id:<47} |",
            "|                                                              |",
            "+==============================================================+",
        ])
        
        return "\n".join(lines)


class LineageTracker:
    """Track and visualize model family trees."""
    
    def __init__(self, registry_dir: Path):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
    
    def register(self, dna: ModelDNA) -> None:
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        dna.save(self.registry_dir / f"{dna.model_id}.json")
    
    def get_lineage(self, model_id: str) -> dict[str, Any]:
        dna = ModelDNA.load(self.registry_dir / f"{model_id}.json")
        
        parents = []
        for parent_id in dna.parent_models:
            parent_path = self.registry_dir / f"{parent_id}.json"
            if parent_path.exists():
                parents.append(ModelDNA.load(parent_path).to_dict())
        
        children = []
        for child_id in dna.child_models:
            child_path = self.registry_dir / f"{child_id}.json"
            if child_path.exists():
                children.append(ModelDNA.load(child_path).to_dict())
        
        return {
            "model": dna.to_dict(),
            "parents": parents,
            "children": children,
            "siblings": [],
        }
    
    def list_models(
        self,
        creator: Optional[str] = None,
        tags: Optional[list[str]] = None,
        base_model: Optional[str] = None,
    ) -> list[ModelDNA]:
        models = []
        for path in self.registry_dir.glob("*.json"):
            try:
                dna = ModelDNA.load(path)
                
                if creator and dna.creator != creator:
                    continue
                if tags and not any(t in dna.tags for t in tags):
                    continue
                if base_model and dna.base_model != base_model:
                    continue
                
                models.append(dna)
            except Exception:
                continue
        
        models.sort(key=lambda m: m.created_at, reverse=True)
        return models


_lineage_tracker: Optional[LineageTracker] = None


def get_lineage_tracker(registry_dir: Optional[Path] = None) -> LineageTracker:
    global _lineage_tracker
    if _lineage_tracker is None:
        if registry_dir is None:
            from foundry.config.settings import get_settings
            registry_dir = get_settings().checkpoint_dir / "lineage"
        _lineage_tracker = LineageTracker(registry_dir)
    return _lineage_tracker
