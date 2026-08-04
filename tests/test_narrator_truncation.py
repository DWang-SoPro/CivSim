"""叙事 max_tokens 截断检测与续写兜底。"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from backend.llm.narrator import (
    Importance,
    NarrationInput,
    ResultTier,
    _MAX_TOKENS_BY_IMPORTANCE,
    narrate,
    narrate_stream,
)


class FakeStreamClient:
    """模拟 call_text_stream：首次 length 截断，续写 stop。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def call_text_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.8,
        max_tokens: int | None = None,
        finish_reason_out: list[str | None] | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        call_index = len(self.calls)
        if call_index == 1:
            pieces = ("倒是王室从中得了利——府库以新币收粮买牛，", "成色不足的旧币")
            reason = "length"
        else:
            pieces = ("则被勒令回炉改铸，市井嘈杂数月方定。",)
            reason = "stop"
        for piece in pieces:
            yield piece
        if finish_reason_out is not None:
            finish_reason_out.clear()
            finish_reason_out.append(reason)


def _major_payload() -> NarrationInput:
    return NarrationInput(
        civ_name="西周王朝",
        year=-998.0,
        action_description="推行新币并收兑旧币",
        result_tier=ResultTier.PARTIAL,
        dimension_changes={"authority": "+3", "stability": "-4"},
        events=["币制更张引发市井纠纷"],
        importance=Importance.MAJOR,
    )


def test_max_tokens_budget_covers_major_narrative() -> None:
    assert _MAX_TOKENS_BY_IMPORTANCE["normal"] >= 800
    assert _MAX_TOKENS_BY_IMPORTANCE["major"] >= 1500


def test_narrate_continues_when_finish_reason_is_length(
    caplog: Any,
) -> None:
    client = FakeStreamClient()
    with caplog.at_level(logging.WARNING):
        text = asyncio.run(narrate(_major_payload(), client=client))

    assert len(client.calls) == 2
    assert client.calls[0]["max_tokens"] == _MAX_TOKENS_BY_IMPORTANCE["major"]
    assert client.calls[1]["max_tokens"] == 800
    assert "成色不足的旧币" in text
    assert text.endswith("市井嘈杂数月方定。")
    assert "叙事被截断，尝试续写" in caplog.text


def test_narrate_stream_yields_continuation_chunks() -> None:
    client = FakeStreamClient()

    async def collect() -> list[str]:
        return [chunk async for chunk in narrate_stream(_major_payload(), client=client)]

    chunks = asyncio.run(collect())
    assert chunks == [
        "倒是王室从中得了利——府库以新币收粮买牛，",
        "成色不足的旧币",
        "则被勒令回炉改铸，市井嘈杂数月方定。",
    ]
