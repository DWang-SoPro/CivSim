"""call_json：thinking 空 content 时降级关闭 thinking。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from backend.llm.client import LLMClient, LLMError


class _TinyModel(BaseModel):
    ok: bool
    name: str


def _completion(
    *,
    content: str | None,
    finish_reason: str = "stop",
    reasoning: str | None = None,
):
    message = SimpleNamespace(content=content, reasoning_content=reasoning)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(
        completion_tokens=4096,
        completion_tokens_details=SimpleNamespace(reasoning_tokens=4096),
    )
    return SimpleNamespace(choices=[choice], usage=usage)


def test_call_json_falls_back_when_thinking_returns_empty() -> None:
    client = LLMClient(api_key="test-key", max_retries=1)
    create = AsyncMock(
        side_effect=[
            _completion(content=None, reasoning="长推理……"),
            _completion(content='{"ok": true, "name": "兴修水利"}'),
        ]
    )
    client._client = MagicMock()
    client._client.chat.completions.create = create

    result = asyncio.run(
        client.call_json(
            [{"role": "user", "content": "请返回 JSON"}],
            _TinyModel,
        )
    )

    assert result.ok is True
    assert result.name == "兴修水利"
    assert create.await_count == 2

    first_kwargs: dict[str, Any] = create.await_args_list[0].kwargs
    second_kwargs: dict[str, Any] = create.await_args_list[1].kwargs
    assert first_kwargs["extra_body"]["thinking"]["type"] == "enabled"
    assert first_kwargs.get("reasoning_effort") == "low"
    assert first_kwargs["max_tokens"] == 16384
    assert second_kwargs["extra_body"]["thinking"]["type"] == "disabled"
    assert "reasoning_effort" not in second_kwargs


def test_call_json_raises_after_fallback_also_empty() -> None:
    client = LLMClient(api_key="test-key", max_retries=1)
    create = AsyncMock(
        side_effect=[
            _completion(content=""),
            _completion(content=None),
        ]
    )
    client._client = MagicMock()
    client._client.chat.completions.create = create

    with pytest.raises(LLMError, match=r"call_json 在 1 次尝试后仍失败.*空 content"):
        asyncio.run(
            client.call_json(
                [{"role": "user", "content": "请返回 JSON"}],
                _TinyModel,
            )
        )

    assert create.await_count == 2
