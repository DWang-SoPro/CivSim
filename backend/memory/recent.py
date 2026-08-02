"""第一层 — 近期记忆：从 turns 读取最近 5 回合，格式化为叙事用文本。纯读取，无 LLM。"""

from __future__ import annotations

from backend.llm.narrator import format_year_label
from backend.memory.store import MemoryStore, TurnRecord

RECENT_TURN_LIMIT = 5


def load_recent_turns(store: MemoryStore, limit: int = RECENT_TURN_LIMIT) -> list[TurnRecord]:
    """从存储读取最近若干回合完整记录。"""
    return store.get_recent_turns(limit=limit)


def format_dimension_changes(changes: dict[str, str] | None) -> str:
    """把维度变化字典压成一句短文本。"""
    if not changes:
        return "无显著数值变化"
    parts = [f"{k}{v}" for k, v in changes.items()]
    return "、".join(parts)


def format_one_turn(record: TurnRecord) -> str:
    """单回合格式化（供近期记忆拼接）。"""
    year_label = format_year_label(record.year_end)
    changes = format_dimension_changes(record.dimension_changes)
    narrative_snip = (record.narrative or "").strip()
    if len(narrative_snip) > 80:
        narrative_snip = narrative_snip[:80] + "…"
    summary = (record.summary or "").strip() or "（无摘要）"
    tags = "、".join(record.domain_tags) if record.domain_tags else "未标注"
    return (
        f"第{record.turn}回合（{year_label}）："
        f"玩家「{record.player_input}」。"
        f"行动：{record.action_description}。"
        f"结果：{record.result_tier}。"
        f"主要变化：{changes}。"
        f"领域：{tags}。"
        f"一句话：{summary}。"
        f"叙事摘录：{narrative_snip or '（无）'}"
    )


def format_recent_history(turns: list[TurnRecord]) -> str:
    """将最近回合列表格式化为 history_context 中的「近期」段落。"""
    if not turns:
        return "（近期无记录）"
    lines = [format_one_turn(t) for t in turns]
    return "\n".join(lines)


def build_recent_context(store: MemoryStore, limit: int = RECENT_TURN_LIMIT) -> str:
    """读取并格式化近期记忆文本。"""
    return format_recent_history(load_recent_turns(store, limit=limit))
