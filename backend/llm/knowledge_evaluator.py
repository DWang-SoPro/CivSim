"""知识注入评估（第一阶段占位，不写提示词内容）。"""

from __future__ import annotations

from typing import Any

from backend.models.schemas import CivState


async def evaluate_knowledge_injection(
    player_input: str,
    state: CivState,
    intent: dict[str, Any],
) -> dict[str, Any]:
    """评估知识注入三维指标。第一阶段未实现。"""
    raise NotImplementedError("知识注入评估将在后续阶段实现")
