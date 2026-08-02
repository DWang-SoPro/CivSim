"""中期摘要压缩（第一阶段占位，不写提示词内容）。"""

from __future__ import annotations

from typing import Any


async def summarize_turns(turn_records: list[dict[str, Any]]) -> str:
    """将最近若干轮记录压缩为中期摘要。第一阶段未实现。"""
    raise NotImplementedError("摘要压缩将在后续阶段实现")
