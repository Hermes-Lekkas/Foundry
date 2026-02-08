# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
#
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""API Keys and BYOK (Bring Your Own Key) configuration routes."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, SecretStr

router = APIRouter()


class APIKeyStatus(BaseModel):
    """API key status (masked)."""
    provider: str = Field(..., description="Provider name")
    is_set: bool = Field(..., description="Whether key is configured")
    masked_key: Optional[str] = Field(default=None, description="Masked key preview (e.g., 'sk-...xxxx')")


class TeacherConfig(BaseModel):
    """Teacher model configuration (BYOK)."""
    provider: str = Field(..., description="Provider: anthropic, openai, local")
    model: str = Field(..., description="Model ID")
    api_key: Optional[SecretStr] = Field(default=None, description="API key (if not local)")
    base_url: Optional[str] = Field(default=None, description="Custom base URL (optional)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=4096, ge=1, le=8192, description="Max tokens per request")


class StudentConfig(BaseModel):
    """Student model configuration (BYOK)."""
    model_id: str = Field(..., description="Model ID from catalog")
    use_local: bool = Field(default=True, description="Use local model")
    api_endpoint: Optional[str] = Field(default=None, description="Custom API endpoint (if not local)")
    api_key: Optional[SecretStr] = Field(default=None, description="API key for custom endpoint")


class BYOKConfig(BaseModel):
    """Complete BYOK configuration."""
    teacher: TeacherConfig = Field(..., description="Teacher configuration")
    student: StudentConfig = Field(..., description="Student configuration")
    huggingface_token: Optional[SecretStr] = Field(default=None, description="HuggingFace access token")


class ProviderInfo(BaseModel):
    """Provider information."""
    id: str = Field(..., description="Provider ID")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Description")
    requires_api_key: bool = Field(..., description="Whether API key is required")
    models: list[dict] = Field(default_factory=list, description="Available models")
    website: str = Field(..., description="Provider website")


# Provider definitions
TEACHER_PROVIDERS: list[ProviderInfo] = [
    ProviderInfo(
        id="anthropic",
        name="Anthropic",
        description="Claude models - excellent for Constitutional AI and reasoning",
        requires_api_key=True,
        website="https://anthropic.com",
        models=[
            {"id": "claude-opus-4-5-20251101", "name": "Claude Opus", "description": "Most capable, best for complex tasks"},
            {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet", "description": "Best balance of speed and capability"},
            {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku", "description": "Fastest, good for simple tasks"},
        ],
    ),
    ProviderInfo(
        id="openai",
        name="OpenAI",
        description="GPT models - widely used, good for general tasks",
        requires_api_key=True,
        website="https://openai.com",
        models=[
            {"id": "gpt-4o", "name": "GPT-4o", "description": "Most capable GPT model"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "Faster, more affordable"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "Previous generation, still capable"},
        ],
    ),
    ProviderInfo(
        id="local",
        name="Local Model",
        description="Use a local model as teacher - private, no API costs",
        requires_api_key=False,
        website="https://huggingface.co",
        models=[
            {"id": "unsloth/Qwen2.5-7B-Instruct", "name": "Qwen 2.5 7B", "description": "Good balance of quality and speed"},
            {"id": "unsloth/Qwen2.5-14B-Instruct", "name": "Qwen 2.5 14B", "description": "Higher quality, slower"},
            {"id": "unsloth/Llama-3.3-70B-Instruct", "name": "Llama 3.3 70B", "description": "Best quality local teacher (requires powerful GPU)"},
        ],
    ),
    ProviderInfo(
        id="custom",
        name="Custom/OpenAI-Compatible",
        description="Any OpenAI-compatible API (Together, Groq, etc.)",
        requires_api_key=True,
        website="https://platform.openai.com/docs/guides/text-generation",
        models=[
            {"id": "custom", "name": "Custom Model", "description": "Specify any model ID"},
        ],
    ),
]


@router.get("/status", response_model=list[APIKeyStatus])
async def get_key_status() -> list[APIKeyStatus]:
    """Get status of configured API keys (masked)."""
    from foundry.config.settings import get_settings
    
    settings = get_settings()
    status_list = []
    
    # Anthropic
    anthropic_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    status_list.append(APIKeyStatus(
        provider="anthropic",
        is_set=bool(anthropic_key),
        masked_key=_mask_key(anthropic_key) if anthropic_key else None,
    ))
    
    # OpenAI
    openai_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    status_list.append(APIKeyStatus(
        provider="openai",
        is_set=bool(openai_key),
        masked_key=_mask_key(openai_key) if openai_key else None,
    ))
    
    # HuggingFace
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    status_list.append(APIKeyStatus(
        provider="huggingface",
        is_set=bool(hf_token),
        masked_key=_mask_key(hf_token) if hf_token else None,
    ))
    
    return status_list


@router.get("/providers", response_model=list[ProviderInfo])
async def get_teacher_providers() -> list[ProviderInfo]:
    """Get available teacher providers and their models."""
    return TEACHER_PROVIDERS


@router.get("/teacher/current", response_model=TeacherConfig)
async def get_current_teacher() -> TeacherConfig:
    """Get current teacher configuration."""
    from foundry.config.settings import get_settings
    
    settings = get_settings()
    
    return TeacherConfig(
        provider=settings.teacher_provider,
        model=settings.teacher_model,
        api_key=None,  # Don't return actual key
        temperature=0.7,
        max_tokens=4096,
    )


@router.post("/teacher/configure")
async def configure_teacher(config: TeacherConfig) -> dict:
    """Configure teacher model (BYOK)."""
    # TODO: Persist configuration to .env or database
    # For now, validate and return success
    
    valid_providers = [p.id for p in TEACHER_PROVIDERS]
    if config.provider not in valid_providers:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid provider: {config.provider}. Valid: {valid_providers}"
        )
    
    # Check if API key is required but not provided
    provider_info = next((p for p in TEACHER_PROVIDERS if p.id == config.provider), None)
    if provider_info and provider_info.requires_api_key and not config.api_key:
        raise HTTPException(
            status_code=400,
            detail=f"Provider {config.provider} requires an API key"
        )
    
    # TODO: Actually save the configuration
    # This would update .env file or database
    
    return {
        "status": "success",
        "message": f"Teacher configured: {config.provider}/{config.model}",
        "provider": config.provider,
        "model": config.model,
    }


@router.get("/student/current", response_model=StudentConfig)
async def get_current_student() -> StudentConfig:
    """Get current student (training target) configuration."""
    from foundry.config.settings import get_settings
    
    settings = get_settings()
    
    return StudentConfig(
        model_id=settings.default_model,
        use_local=True,
    )


@router.post("/student/configure")
async def configure_student(config: StudentConfig) -> dict:
    """Configure student model (BYOK)."""
    # TODO: Persist configuration
    
    return {
        "status": "success",
        "message": f"Student configured: {config.model_id}",
        "model_id": config.model_id,
        "use_local": config.use_local,
    }


@router.post("/huggingface/token")
async def set_huggingface_token(token: SecretStr) -> dict:
    """Set HuggingFace access token for gated models."""
    # TODO: Persist token securely
    
    return {
        "status": "success",
        "message": "HuggingFace token configured",
    }


def _mask_key(key: str) -> str:
    """Mask an API key for display."""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"
