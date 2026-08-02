"""历史检索：组装叙事所需的 history_context。

检索策略可替换：当前为关键词标签版，将来可换成向量版（见 landmark.query_landmarks_vector）。
"""

from __future__ import annotations

from typing import Any, Optional, Protocol

from backend.memory.landmark import format_landmarks_for_context, query_landmarks_keyword
from backend.memory.recent import build_recent_context
from backend.memory.store import LandmarkRecord, MemoryStore
from backend.memory.summary import format_summaries_for_context
from backend.models.schemas import Accumulations, CivState

# 行动域 → 积累值字段
DOMAIN_TO_ACCUMULATION: dict[str, str] = {
    "economic": "commercial",
    "political": "administrative",
    "military": "military",
    "cultural": "cultural",
    "technology": "academic",
    "composite": "administrative",
}

ACCUMULATION_LABELS: dict[str, str] = {
    "academic": "学术基础",
    "military": "军事传统",
    "commercial": "商业生态",
    "administrative": "行政经验",
    "cultural": "宗教文化",
}


class LandmarkSearchFn(Protocol):
    """长期索引检索策略签名（可换关键词 / 向量）。"""

    def __call__(
        self,
        store: MemoryStore,
        domain_tags: list[str],
        *,
        limit: int = 5,
    ) -> list[LandmarkRecord]: ...


def keyword_landmark_strategy(
    store: MemoryStore,
    domain_tags: list[str],
    *,
    limit: int = 5,
) -> list[LandmarkRecord]:
    """当前默认：关键词标签重叠检索。"""
    return query_landmarks_keyword(store, domain_tags, limit=limit)


def format_accumulations_for_context(
    accumulations: Accumulations | dict[str, float],
    domain_tags: list[str] | None = None,
) -> str:
    """把当前积累值格式化为史官可用的说明。"""
    if isinstance(accumulations, Accumulations):
        data = accumulations.model_dump()
    else:
        data = dict(accumulations)

    lines: list[str] = []
    for key in ("administrative", "military", "commercial", "academic", "cultural"):
        val = float(data.get(key, 0.0))
        label = ACCUMULATION_LABELS.get(key, key)
        if val >= 1.2:
            level = "深厚"
        elif val >= 0.6:
            level = "可观"
        elif val >= 0.3:
            level = "初具"
        else:
            level = "尚浅"
        lines.append(f"{label}（{key}={val:.2f}）—{level}")

    focus_notes: list[str] = []
    for tag in domain_tags or []:
        acc_key = DOMAIN_TO_ACCUMULATION.get(tag.lower())
        if not acc_key:
            continue
        val = float(data.get(acc_key, 0.0))
        label = ACCUMULATION_LABELS.get(acc_key, acc_key)
        if val >= 0.8:
            focus_notes.append(
                f"当前行动偏「{tag}」域，{label}已厚；"
                f"叙事宜体现「赖多年积淀，此事更易贯通」一类因果。"
            )
        elif val < 0.25:
            focus_notes.append(
                f"当前行动偏「{tag}」域，但{label}尚薄；"
                f"叙事可略写根基不足、推行吃力。"
            )

    body = "；".join(lines)
    if focus_notes:
        return body + "\n" + "\n".join(focus_notes)
    return body


def assemble_history_context(
    *,
    recent_text: str,
    summaries_text: str,
    landmarks_text: str,
    accumulations_text: str,
) -> str:
    """将三层记忆 + 积累值拼成完整 history_context。"""
    return (
        "【近期历程】\n"
        f"{recent_text.strip()}\n\n"
        "【近代史摘要】\n"
        f"{summaries_text.strip()}\n\n"
        "【相关史事】\n"
        f"{landmarks_text.strip()}\n\n"
        "【路径积累】\n"
        f"{accumulations_text.strip()}"
    )


def retrieve_history_context(
    store: MemoryStore,
    *,
    domain_tags: list[str],
    state: CivState | None = None,
    accumulations: Accumulations | dict[str, float] | None = None,
    recent_limit: int = 5,
    summary_limit: int = 3,
    landmark_limit: int = 5,
    landmark_search: Optional[LandmarkSearchFn] = None,
    current_action: dict[str, Any] | None = None,
) -> str:
    """叙事生成前调用：组装 history_context。

    Args:
        store: 记忆库
        domain_tags: 当前行动领域标签（用于 landmark 关键词匹配）
        state: 可选，取其 accumulations
        accumulations: 显式传入的积累值（优先于 state）
        landmark_search: 检索策略，默认关键词；将来可注入向量策略
        current_action: 兼容旧签名的附加信息（可含 domain_tags）
    """
    tags = list(domain_tags)
    if current_action:
        extra = current_action.get("domain_tags") or current_action.get("tags")
        if extra:
            tags = list({*tags, *[str(t) for t in extra]})

    search: LandmarkSearchFn = landmark_search or keyword_landmark_strategy

    recent_text = build_recent_context(store, limit=recent_limit)
    summaries = store.get_recent_summaries(limit=summary_limit)
    summaries_text = format_summaries_for_context(summaries)
    landmarks = search(store, tags, limit=landmark_limit)
    landmarks_text = format_landmarks_for_context(landmarks)

    acc: Accumulations | dict[str, float] | None = accumulations
    if acc is None and state is not None:
        acc = state.accumulations
    if acc is None:
        acc = Accumulations()
    accumulations_text = format_accumulations_for_context(acc, tags)

    return assemble_history_context(
        recent_text=recent_text,
        summaries_text=summaries_text,
        landmarks_text=landmarks_text,
        accumulations_text=accumulations_text,
    )


def record_turn_from_full_result(
    store: MemoryStore,
    *,
    turn: int,
    year_start: float,
    result: Any,
    one_line_summary: str | None = None,
) -> Any:
    """从 FullTurnResult 写入一轮 TurnRecord（供管线/测试复用）。"""
    from backend.memory.store import TurnRecord

    state_after = result.state_after
    year_end = float(state_after.year) if state_after is not None else year_start
    domain_tags: list[str] = []
    for intent in result.intents:
        if getattr(intent, "is_too_vague", False):
            continue
        tag = getattr(getattr(intent, "action_domain", None), "value", None) or str(
            getattr(intent, "action_domain", "composite")
        )
        if tag and tag not in domain_tags:
            domain_tags.append(tag)

    action_desc = ""
    if result.narration_input is not None:
        action_desc = result.narration_input.action_description
    elif result.intents:
        action_desc = "；".join(
            i.action_description for i in result.intents if not i.is_too_vague
        )

    tier = (
        result.overall_tier.value
        if result.overall_tier is not None
        else "failure"
    )
    summary = one_line_summary or (
        f"{action_desc or result.player_input} → {tier}"
    )

    record = TurnRecord(
        game_id=store.game_id,
        turn=turn,
        year_start=year_start,
        year_end=year_end,
        player_input=result.player_input,
        action_description=action_desc or result.player_input,
        result_tier=tier,
        dimension_changes=dict(result.dimension_changes or {}),
        narrative=result.narrative or "",
        summary=summary,
        domain_tags=domain_tags,
        llm_intent=[i.model_dump() for i in result.intents],
        action_result={
            "aggregated_deltas": result.aggregated_deltas,
            "events": result.events,
            "importance": result.importance.value
            if hasattr(result.importance, "value")
            else str(result.importance),
        },
        state_before=result.state_before.model_dump()
        if result.state_before is not None
        else None,
        state_after=state_after.model_dump() if state_after is not None else None,
    )
    return store.add_turn(record)


# 兼容旧占位签名
def retrieve_history_context_legacy(
    current_action: dict[str, Any],
    game_id: str,
) -> str:
    """旧占位签名保留；无 store 时返回空串。"""
    _ = (current_action, game_id)
    return ""
