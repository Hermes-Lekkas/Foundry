# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Local Teacher — Uses a quantized local model via VRAMManager."""

from __future__ import annotations

import logging
from typing import Any

from foundry.data_engine.teachers.base import Message, Teacher, TeacherResponse

logger = logging.getLogger(__name__)


class LocalTeacher(Teacher):
    """Teacher backed by a locally-loaded model (via VRAMManager).

    Uses the shared VRAMManager to load/unload the teacher model,
    enabling time-sharded VRAM usage with the student model.
    """

    def __init__(self, model_name: str, max_seq_length: int = 4096) -> None:
        self.model_name = model_name
        self.max_seq_length = max_seq_length

    async def _ensure_loaded(self) -> tuple[Any, Any]:
        from foundry.shared.vram import ModelRole, VRAMManager

        manager = VRAMManager()
        return await manager.load(ModelRole.TEACHER, self.model_name)

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> TeacherResponse:
        model, tokenizer = await self._ensure_loaded()

        # Build chat template
        chat = [{"role": m.role, "content": m.content} for m in messages]

        try:
            input_text = tokenizer.apply_chat_template(
                chat, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            # Fallback for models without chat template
            input_text = "\n".join(
                f"{'### ' + m.role.title()}\n{m.content}" for m in messages
            )
            input_text += "\n### Assistant\n"

        import torch

        inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=self.max_seq_length)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=min(max_tokens, self.max_seq_length),
                temperature=temperature,
                do_sample=temperature > 0,
                top_p=0.95,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )

        # Decode only the new tokens
        input_len = inputs["input_ids"].shape[1]
        generated = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)

        return TeacherResponse(content=generated.strip())

    async def critique(self, response: str, principle: str, template: str) -> str:
        from jinja2 import Template

        prompt = Template(template).render(response=response, principle=principle)
        result = await self.generate(
            [Message(role="user", content=prompt)],
            temperature=0.3,
            max_tokens=1024,
        )
        return result.content

    async def revise(self, response: str, critique: str, template: str) -> str:
        from jinja2 import Template

        prompt = Template(template).render(response=response, critique=critique)
        result = await self.generate(
            [Message(role="user", content=prompt)],
            temperature=0.5,
            max_tokens=4096,
        )
        return result.content
