"""call_json：默认关闭 thinking，空 content / 校验失败会重试。"""

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
        completion_tokens=256,
        completion_tokens_details=SimpleNamespace(reasoning_tokens=0),
    )
    return SimpleNamespace(choices=[choice], usage=usage)


def test_call_json_uses_non_thinking_by_default() -> None:
    client = LLMClient(api_key="test-key", max_retries=1)
    create = AsyncMock(
        return_value=_completion(content='{"ok": true, "name": "兴修水利"}')
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
    kwargs: dict[str, Any] = create.await_args.kwargs
    assert kwargs["extra_body"]["thinking"]["type"] == "disabled"
    assert kwargs["max_tokens"] == 4096
    assert kwargs["temperature"] == 0.2
    assert "reasoning_effort" not in kwargs


def test_call_json_retries_after_empty_content() -> None:
    client = LLMClient(api_key="test-key", max_retries=2)
    create = AsyncMock(
        side_effect=[
            _completion(content=None),
            _completion(content='{"ok": true, "name": "操练士卒"}'),
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

    assert result.name == "操练士卒"
    assert create.await_count == 2


def test_call_json_raises_after_retries_exhausted() -> None:
    client = LLMClient(api_key="test-key", max_retries=1)
    create = AsyncMock(return_value=_completion(content=""))
    client._client = MagicMock()
    client._client.chat.completions.create = create

    with pytest.raises(LLMError, match=r"call_json 在 1 次尝试后仍失败.*空 content"):
        asyncio.run(
            client.call_json(
                [{"role": "user", "content": "请返回 JSON"}],
                _TinyModel,
            )
        )

    assert create.await_count == 1
