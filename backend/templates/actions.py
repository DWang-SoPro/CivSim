"""行动类型定义与前置条件（第一阶段占位）。

后续阶段按文档 §4 填充完整行动表与动态菜单生成。
"""

from __future__ import annotations

from typing import Any

from backend.models.schemas import CivState


def check_prerequisites(action: dict[str, Any], state: CivState) -> bool:
    """检查行动前置条件是否满足。第一阶段默认 True。"""
    _ = (action, state)
    return True


def generate_action_menu(state: CivState) -> list[dict[str, Any]]:
    """根据当前状态动态生成可用行动菜单。第一阶段返回空列表。"""
    _ = state
    return []
