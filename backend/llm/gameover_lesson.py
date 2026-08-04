"""Game Over 终局报告：历史教训生成。"""

from __future__ import annotations

from typing import Any, Optional

from backend.engine.gameover import reason_label
from backend.llm.client import LLMClient, LLMError
from backend.models.schemas import CivState


async def generate_historical_lesson(
    state: CivState,
    *,
    reason: str,
    total_turns: int,
    year_start: float,
    year_end: float,
    achievements: list[str],
    client: LLMClient | None = None,
) -> str:
    """用 LLM 生成 2–3 句史官口吻的「历史教训」；失败时回退固定文案。"""
    reason_text = reason_label(reason)
    fallback = (
        f"{state.civ_name}历经{total_turns}回合而终，因{reason_text}而倾覆。"
        "后世当知：粮储、人心与制度三者失其一，社稷难久。"
        "读史至此，可为殷鉴。"
    )
    own_client = client is None
    try:
        llm = client or LLMClient()
        year_span = f"{_fmt_year(year_start)}至{_fmt_year(year_end)}"
        ach = "；".join(achievements[:8]) if achievements else "无显著载入史册之大事"
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位古代史官，为已覆灭的文明撰写简短历史教训。"
                    "只输出 2–3 句中文，文言白话夹杂亦可，不要标题、不要列举符号。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"文明：{state.civ_name}\n"
                    f"起止：{year_span}，共 {total_turns} 回合\n"
                    f"终结原因：{reason_text}\n"
                    f"终局人口：{state.population}，稳定：{state.stability:.0f}，"
                    f"统治力：{state.authority:.0f}\n"
                    f"重大事件：{ach}\n"
                    "请写历史教训（2–3句）。"
                ),
            },
        ]
        # 2–3 句历史教训；旧值 300 偶发截断文言长句，提高到 600
        text = await llm.call(messages, thinking=False, temperature=0.7, max_tokens=600)
        text = (text or "").strip()
        if len(text) < 12:
            return fallback
        return text
    except (LLMError, Exception):
        return fallback
    finally:
        if own_client and client is None:
            pass


def _fmt_year(year: float) -> str:
    y = int(round(year))
    if y < 0:
        return f"公元前{abs(y)}年"
    if y == 0:
        return "公元元年"
    return f"公元{y}年"


def build_game_over_payload(
    state: CivState,
    *,
    reason: str,
    year_start: float,
    peak_population: int,
    peak_territory: int,
    achievements: list[dict[str, Any]],
    historical_lesson: str,
) -> dict[str, Any]:
    """构造 WS game_over 帧 payload。"""
    return {
        "reason": reason,
        "reason_label": reason_label(reason),
        "civ_name": state.civ_name,
        "template_id": state.template_id,
        "total_turns": state.turn,
        "year_start": year_start,
        "year_end": state.year,
        "peak_population": peak_population,
        "peak_territory": peak_territory,
        "achievements": achievements,
        "historical_lesson": historical_lesson,
    }


def landmarks_as_achievements(landmarks: list[Any]) -> list[dict[str, Any]]:
    """从 landmark 记录提取成就列表。"""
    items: list[dict[str, Any]] = []
    for lm in landmarks:
        items.append(
            {
                "turn": getattr(lm, "turn", 0),
                "year": getattr(lm, "year", 0),
                "title": getattr(lm, "title", "") or "无名大事",
                "summary": getattr(lm, "summary", "") or "",
            }
        )
    return items
