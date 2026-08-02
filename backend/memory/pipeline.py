"""回合后记忆更新：写 turns → 检测 landmarks → 条件触发中期摘要。"""

from __future__ import annotations

from typing import Any, Optional

from backend.llm.client import LLMClient
from backend.memory.landmark import create_landmarks_from_turn
from backend.memory.retriever import record_turn_from_full_result
from backend.memory.store import LandmarkRecord, MemoryStore, SummaryRecord, TurnRecord
from backend.memory.summary import maybe_create_summary
from backend.models.schemas import CivState


async def commit_turn_memory(
    store: MemoryStore,
    *,
    turn: int,
    year_start: float,
    state_before: CivState,
    state_after: CivState,
    player_input: str,
    action_description: str,
    result_tier: str,
    dimension_changes: dict[str, str],
    narrative: str,
    domain_tags: list[str],
    events: list[str] | None = None,
    one_line_summary: str | None = None,
    civ_name: str | None = None,
    client: LLMClient | None = None,
    full_result: Any = None,
) -> tuple[TurnRecord, list[LandmarkRecord], Optional[SummaryRecord]]:
    """结算后写入三层记忆，返回 (turn, landmarks, summary|None)。"""
    if full_result is not None:
        turn_rec = record_turn_from_full_result(
            store,
            turn=turn,
            year_start=year_start,
            result=full_result,
            one_line_summary=one_line_summary,
        )
    else:
        turn_rec = store.add_turn(
            TurnRecord(
                game_id=store.game_id,
                turn=turn,
                year_start=year_start,
                year_end=float(state_after.year),
                player_input=player_input,
                action_description=action_description,
                result_tier=result_tier,
                dimension_changes=dimension_changes,
                narrative=narrative,
                summary=one_line_summary
                or f"{action_description} → {result_tier}",
                domain_tags=domain_tags,
                state_before=state_before.model_dump(),
                state_after=state_after.model_dump(),
            )
        )

    landmarks = create_landmarks_from_turn(
        store,
        turn=turn,
        year=float(state_after.year),
        state_before=state_before,
        state_after=state_after,
        domain_tags=domain_tags,
        action_description=action_description,
        result_tier=result_tier,
        events=events,
        narrative=narrative,
    )

    summary = await maybe_create_summary(
        store,
        current_turn=turn,
        civ_name=civ_name or state_after.civ_name,
        client=client,
    )
    return turn_rec, landmarks, summary
