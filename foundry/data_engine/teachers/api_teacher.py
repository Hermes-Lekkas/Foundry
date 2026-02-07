# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""API Teacher — External API-based teacher models (Anthropic, OpenAI-compatible)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from foundry.data_engine.teachers.base import Message, Teacher, TeacherResponse

logger = logging.getLogger(__name__)


class APITeacher(Teacher):
    """Teacher backed by an external API (Anthropic Claude or OpenAI-compatible)."""

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-5-20250929",
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key or self._get_api_key(provider)
        self.base_url = base_url or self._default_base_url(provider)
        self._client = httpx.AsyncClient(timeout=120)

    @staticmethod
    def _get_api_key(provider: str) -> str:
        import os
        if provider == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY", "")
        else:
            key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise ValueError(f"API key not set for provider '{provider}'")
        return key

    @staticmethod
    def _default_base_url(provider: str) -> str:
        if provider == "anthropic":
            return "https://api.anthropic.com"
        return "https://api.openai.com"

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> TeacherResponse:
        if self.provider == "anthropic":
            return await self._generate_anthropic(messages, tools, temperature, max_tokens)
        return await self._generate_openai(messages, tools, temperature, max_tokens)

    async def _generate_anthropic(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
    ) -> TeacherResponse:
        # Separate system message
        system = ""
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                msg: dict[str, Any] = {"role": m.role, "content": m.content}
                if m.role == "tool" and m.tool_call_id:
                    msg = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id,
                                "content": m.content,
                            }
                        ],
                    }
                chat_messages.append(msg)

        body: dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("parameters", {}),
                }
                for t in tools
            ]

        resp = await self._client.post(
            f"{self.base_url}/v1/messages",
            json=body,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        # Parse response
        content_parts = data.get("content", [])
        text_parts = []
        tool_calls = []
        for part in content_parts:
            if part["type"] == "text":
                text_parts.append(part["text"])
            elif part["type"] == "tool_use":
                tool_calls.append({
                    "id": part["id"],
                    "name": part["name"],
                    "arguments": part["input"],
                })

        return TeacherResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=data.get("stop_reason", "end_turn"),
            usage=data.get("usage", {}),
        )

    async def _generate_openai(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
    ) -> TeacherResponse:
        chat_messages = []
        for m in messages:
            msg: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.name:
                msg["name"] = m.name
            chat_messages.append(msg)

        body: dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = [
                {"type": "function", "function": t} for t in tools
            ]

        resp = await self._client.post(
            f"{self.base_url}/v1/chat/completions",
            json=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        message = choice["message"]

        tool_calls = None
        if message.get("tool_calls"):
            tool_calls = [
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "arguments": json.loads(tc["function"]["arguments"]),
                }
                for tc in message["tool_calls"]
            ]

        return TeacherResponse(
            content=message.get("content", ""),
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
        )

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

    async def close(self) -> None:
        await self._client.aclose()
