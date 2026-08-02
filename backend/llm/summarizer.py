"""中期摘要压缩 — 转发至 memory.summary（设计文档 §7.2）。"""

from __future__ import annotations

from typing import Any

from backend.memory.store import TurnRecord
from backend.memory.summary import MidSummaryResult, compress_turns


async def summarize_turns(
    turn_records: list[dict[str, Any]] | list[TurnRecord],
    *,
    civ_name: str = "未知文明",
    client: Any = None,
) -> str:
    """将最近若干轮记录压缩为中期摘要文本。"""
    turns: list[TurnRecord] = []
    for item in turn_records:
        if isinstance(item, TurnRecord):
            turns.append(item)
        else:
            turns.append(
                TurnRecord(
                    game_id=str(item.get("game_id", "")),
                    turn=int(item["turn"]),
                    year_start=float(item.get("year_start", item.get("year", 0))),
                    year_end=float(item.get("year_end", item.get("year", 0))),
                    player_input=str(item.get("player_input", "")),
                    action_description=str(item.get("action_description", "")),
                    result_tier=str(item.get("result_tier", "")),
                    dimension_changes=dict(item.get("dimension_changes") or {}),
                    narrative=str(item.get("narrative", "")),
                    summary=str(item.get("summary", "")),
                    domain_tags=list(item.get("domain_tags") or []),
                )
            )
    result: MidSummaryResult = await compress_turns(
        civ_name, turns, client=client
    )
    return result.content
