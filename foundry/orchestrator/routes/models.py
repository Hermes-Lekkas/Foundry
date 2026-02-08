# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
#
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Model management routes — download, browse, and manage LLMs."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class ModelSize(str, Enum):
    """Model size categories."""
    TINY = "tiny"      # < 1B
    SMALL = "small"    # 1-3B
    MEDIUM = "medium"  # 7-8B
    LARGE = "large"    # 14B+


class ModelProvider(str, Enum):
    """Model providers/registries."""
    UNSLOTH = "unsloth"
    HUGGINGFACE = "huggingface"


class ModelInfo(BaseModel):
    """Model information."""
    id: str = Field(..., description="Model ID (e.g., unsloth/Qwen2.5-0.5B)")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Short description")
    size: ModelSize = Field(..., description="Size category")
    params: str = Field(..., description="Parameter count (e.g., '0.5B')")
    vram_required_gb: float = Field(..., description="Approximate VRAM required")
    provider: ModelProvider = Field(..., description="Model provider")
    tags: list[str] = Field(default_factory=list, description="Tags like 'instruct', 'reasoning'")
    downloads: int = Field(default=0, description="Download count (if available)")
    is_downloaded: bool = Field(default=False, description="Whether model is locally available")
    local_path: Optional[str] = Field(default=None, description="Local path if downloaded")


class DownloadRequest(BaseModel):
    """Request to download a model."""
    model_id: str = Field(..., description="Model ID to download")
    cache_dir: Optional[str] = Field(default=None, description="Custom cache directory")


class DownloadResponse(BaseModel):
    """Download response."""
    job_id: str = Field(..., description="Download job ID")
    status: str = Field(..., description="Status: queued, downloading, complete, failed")
    message: str = Field(..., description="Status message")


class BYOKConfig(BaseModel):
    """Bring Your Own Key configuration."""
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    huggingface_token: Optional[str] = Field(default=None, description="HuggingFace token")


# Predefined model catalog
MODEL_CATALOG: list[ModelInfo] = [
    # Tiny models (< 1B) - For testing, CPU-only
    ModelInfo(
        id="unsloth/Qwen2.5-0.5B",
        name="Qwen 2.5 0.5B",
        description="Fastest inference, good for testing and prototyping",
        size=ModelSize.TINY,
        params="0.5B",
        vram_required_gb=2.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "fast", "multilingual"],
    ),
    ModelInfo(
        id="unsloth/Qwen2.5-0.5B-Instruct",
        name="Qwen 2.5 0.5B Instruct",
        description="Instruction-tuned variant for chat/assistant tasks",
        size=ModelSize.TINY,
        params="0.5B",
        vram_required_gb=2.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "chat", "fast"],
    ),
    ModelInfo(
        id="unsloth/SmolLM2-135M",
        name="SmolLM2 135M",
        description="Ultra-small model for edge devices",
        size=ModelSize.TINY,
        params="0.135B",
        vram_required_gb=1.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "tiny", "edge"],
    ),
    ModelInfo(
        id="unsloth/SmolLM2-360M",
        name="SmolLM2 360M",
        description="Small but capable, great for learning",
        size=ModelSize.TINY,
        params="0.36B",
        vram_required_gb=1.5,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "beginner-friendly"],
    ),
    
    # Small models (1-3B) - Good balance
    ModelInfo(
        id="unsloth/Qwen2.5-1.5B",
        name="Qwen 2.5 1.5B",
        description="Excellent small model with strong reasoning",
        size=ModelSize.SMALL,
        params="1.5B",
        vram_required_gb=4.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "reasoning", "popular"],
    ),
    ModelInfo(
        id="unsloth/Qwen2.5-1.5B-Instruct",
        name="Qwen 2.5 1.5B Instruct",
        description="Instruction-tuned, great for chatbots",
        size=ModelSize.SMALL,
        params="1.5B",
        vram_required_gb=4.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "chat", "recommended"],
    ),
    ModelInfo(
        id="unsloth/Llama-3.2-1B",
        name="Llama 3.2 1B",
        description="Meta's efficient small model",
        size=ModelSize.SMALL,
        params="1B",
        vram_required_gb=3.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "meta", "efficient"],
    ),
    ModelInfo(
        id="unsloth/Llama-3.2-1B-Instruct",
        name="Llama 3.2 1B Instruct",
        description="Instruction-tuned Llama for assistants",
        size=ModelSize.SMALL,
        params="1B",
        vram_required_gb=3.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "chat", "meta"],
    ),
    ModelInfo(
        id="unsloth/Llama-3.2-3B",
        name="Llama 3.2 3B",
        description="Larger Llama variant, strong performance",
        size=ModelSize.SMALL,
        params="3B",
        vram_required_gb=6.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "meta", "balanced"],
    ),
    ModelInfo(
        id="unsloth/Llama-3.2-3B-Instruct",
        name="Llama 3.2 3B Instruct",
        description="Best Llama 3.2 for chat applications",
        size=ModelSize.SMALL,
        params="3B",
        vram_required_gb=6.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "chat", "meta", "recommended"],
    ),
    ModelInfo(
        id="unsloth/Phi-4",
        name="Phi-4",
        description="Microsoft's efficient small model with strong coding",
        size=ModelSize.SMALL,
        params="3.8B",
        vram_required_gb=7.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "coding", "microsoft"],
    ),
    
    # Medium models (7-8B) - High quality
    ModelInfo(
        id="unsloth/Qwen2.5-7B",
        name="Qwen 2.5 7B",
        description="Powerful open model with excellent reasoning",
        size=ModelSize.MEDIUM,
        params="7B",
        vram_required_gb=14.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "reasoning", "advanced"],
    ),
    ModelInfo(
        id="unsloth/Qwen2.5-7B-Instruct",
        name="Qwen 2.5 7B Instruct",
        description="Top-tier instruction model for serious applications",
        size=ModelSize.MEDIUM,
        params="7B",
        vram_required_gb=14.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "chat", "production", "recommended"],
    ),
    ModelInfo(
        id="unsloth/Qwen2.5-Coder-7B-Instruct",
        name="Qwen 2.5 Coder 7B",
        description="Specialized for code generation and programming",
        size=ModelSize.MEDIUM,
        params="7B",
        vram_required_gb=14.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "coding", "specialized"],
    ),
    ModelInfo(
        id="unsloth/Qwen2.5-Math-7B-Instruct",
        name="Qwen 2.5 Math 7B",
        description="Optimized for mathematical reasoning",
        size=ModelSize.MEDIUM,
        params="7B",
        vram_required_gb=14.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "math", "reasoning", "specialized"],
    ),
    ModelInfo(
        id="unsloth/Mistral-Small-24B-Instruct-2501",
        name="Mistral Small 24B",
        description="Mistral's efficient medium model",
        size=ModelSize.MEDIUM,
        params="24B",
        vram_required_gb=12.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "mistral", "efficient"],
    ),
    
    # Large models (14B+) - State of the art
    ModelInfo(
        id="unsloth/Qwen2.5-14B-Instruct",
        name="Qwen 2.5 14B",
        description="High-capability model for complex tasks",
        size=ModelSize.LARGE,
        params="14B",
        vram_required_gb=28.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "advanced", "powerful"],
    ),
    ModelInfo(
        id="unsloth/Qwen2.5-32B-Instruct",
        name="Qwen 2.5 32B",
        description="Near GPT-4 quality for local deployment",
        size=ModelSize.LARGE,
        params="32B",
        vram_required_gb=48.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "expert", "production"],
    ),
    ModelInfo(
        id="unsloth/Llama-3.3-70B-Instruct",
        name="Llama 3.3 70B",
        description="Meta's largest open model, state of the art",
        size=ModelSize.LARGE,
        params="70B",
        vram_required_gb=80.0,
        provider=ModelProvider.UNSLOTH,
        tags=["instruct", "sota", "enterprise"],
    ),
    ModelInfo(
        id="unsloth/DeepSeek-R1-Distill-Qwen-7B",
        name="DeepSeek R1 Distill (Qwen 7B)",
        description="Reasoning model with step-by-step thinking",
        size=ModelSize.MEDIUM,
        params="7B",
        vram_required_gb=14.0,
        provider=ModelProvider.UNSLOTH,
        tags=["reasoning", "thinking", "advanced"],
    ),
    ModelInfo(
        id="unsloth/DeepSeek-R1-Distill-Qwen-14B",
        name="DeepSeek R1 Distill (Qwen 14B)",
        description="Larger reasoning model with stronger capabilities",
        size=ModelSize.LARGE,
        params="14B",
        vram_required_gb=28.0,
        provider=ModelProvider.UNSLOTH,
        tags=["reasoning", "thinking", "expert"],
    ),
    ModelInfo(
        id="unsloth/DeepSeek-R1-Distill-Llama-8B",
        name="DeepSeek R1 Distill (Llama 8B)",
        description="Llama-based reasoning model",
        size=ModelSize.MEDIUM,
        params="8B",
        vram_required_gb=16.0,
        provider=ModelProvider.UNSLOTH,
        tags=["reasoning", "thinking", "llama"],
    ),
]


@router.get("/catalog", response_model=list[ModelInfo])
async def get_model_catalog(
    size: Optional[ModelSize] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
) -> list[ModelInfo]:
    """Get the model catalog with optional filtering."""
    models = MODEL_CATALOG.copy()
    
    # Apply filters
    if size:
        models = [m for m in models if m.size == size]
    
    if tag:
        models = [m for m in models if tag.lower() in [t.lower() for t in m.tags]]
    
    if search:
        search_lower = search.lower()
        models = [
            m for m in models 
            if search_lower in m.name.lower() 
            or search_lower in m.description.lower()
            or search_lower in m.id.lower()
        ]
    
    return models


@router.get("/catalog/{model_id}", response_model=ModelInfo)
async def get_model_details(model_id: str) -> ModelInfo:
    """Get details for a specific model."""
    for model in MODEL_CATALOG:
        if model.id == model_id:
            return model
    raise HTTPException(status_code=404, detail=f"Model {model_id} not found")


@router.post("/download", response_model=DownloadResponse)
async def download_model(request: DownloadRequest) -> DownloadResponse:
    """Queue a model download."""
    # Verify model exists in catalog
    model = None
    for m in MODEL_CATALOG:
        if m.id == request.model_id:
            model = m
            break
    
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {request.model_id} not found in catalog")
    
    # TODO: Implement actual download logic
    # For now, return a queued status
    import uuid
    
    return DownloadResponse(
        job_id=str(uuid.uuid4()),
        status="queued",
        message=f"Download queued for {model.name}. This feature will download from HuggingFace.",
    )


@router.get("/downloaded", response_model=list[ModelInfo])
async def get_downloaded_models() -> list[ModelInfo]:
    """Get list of locally downloaded models."""
    # TODO: Implement scan of local cache directory
    # For now, return empty list
    return []


@router.get("/sizes", response_model=list[dict])
async def get_model_sizes() -> list[dict]:
    """Get available model size categories."""
    return [
        {"value": ModelSize.TINY, "label": "Tiny (< 1B)", "vram_range": "1-2 GB"},
        {"value": ModelSize.SMALL, "label": "Small (1-3B)", "vram_range": "3-7 GB"},
        {"value": ModelSize.MEDIUM, "label": "Medium (7-8B)", "vram_range": "8-16 GB"},
        {"value": ModelSize.LARGE, "label": "Large (14B+)", "vram_range": "16+ GB"},
    ]


@router.get("/tags", response_model=list[str])
async def get_model_tags() -> list[str]:
    """Get all available model tags."""
    tags = set()
    for model in MODEL_CATALOG:
        tags.update(model.tags)
    return sorted(list(tags))
