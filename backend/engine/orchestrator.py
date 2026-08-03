"""HTTP 无关的完整回合编排层。

这一层只负责把已经存在的结算、记忆和叙事组件串起来。调用方可以通过
叙事与生命周期回调接收关键产出，再自行转换成 WebSocket、CLI 或其他输出。
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal, Optional

from backend.engine.action_resolver import FullTurnResult, resolve_full_turn
from backend.engine.gameover import check_game_over
from backend.llm.client import LLMError
from backend.llm.narrator import narrate_stream
from backend.memory.pipeline import commit_turn_memory
from backend.memory.retriever import retrieve_history_context
from backend.memory.store import MemoryStore
from backend.models.schemas import CivState

logger = logging.getLogger(__name__)


NarrativeEventKind = Literal["start", "delta", "end"]


@dataclass(frozen=True)
class NarrativeStreamEvent:
    """与传输协议无关的叙事流事件。"""

    type: NarrativeEventKind
    turn: int
    payload: dict[str, Any]


NarrativeEventCallback = Callable[
    [NarrativeStreamEvent], Awaitable[None] | None
]


@dataclass(frozen=True)
class TurnReadyResult:
    """玩家可继续操作的回合产出点。

    该回调只在非模糊回合中触发，且一定位于叙事结束之后、记忆提交
    与 Game Over 检查之前。
    """

    core_result: FullTurnResult
    state: CivState
    narrative: str


TurnReadyCallback = Callable[[TurnReadyResult], Awaitable[None] | None]


@dataclass(frozen=True)
class GameOverResult:
    """Game Over 检查命中后的传输无关通知。"""

    state: CivState
    reason: str
    payload: dict[str, Any] | None = None


GameOverCallback = Callable[[GameOverResult], Awaitable[None] | None]


@dataclass(frozen=True)
class GameTurnResult:
    """编排完成后的回合结果。"""

    core_result: FullTurnResult
    state: CivState
    narrative: Optional[str]
    game_over: bool
    game_over_reason: Optional[str]

    @property
    def settlement_skipped(self) -> bool:
        return self.core_result.settlement_skipped


async def _emit(
    callback: Callable[[Any], Awaitable[None] | None] | None,
    event: Any,
) -> None:
    if callback is None:
        return
    try:
        maybe_awaitable = callback(event)
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable
    except Exception:
        # 事件输出是旁路；传输失败不能推翻已经完成（或正在完成）的游戏回合。
        logger.warning("回合事件回调失败，游戏回合继续", exc_info=True)


def _domain_tags(result: FullTurnResult) -> list[str]:
    tags: list[str] = []
    for subtask in result.subtasks:
        if subtask.skipped_vague:
            continue
        tag = subtask.intent.action_domain.value
        if tag not in tags:
            tags.append(tag)
    return tags


async def run_game_turn(
    state: CivState,
    player_input: str,
    *,
    store: MemoryStore,
    client: Any = None,
    rng_seed: int = 42,
    on_narrative_event: NarrativeEventCallback | None = None,
    on_turn_ready: TurnReadyCallback | None = None,
    on_game_over: GameOverCallback | None = None,
    initial_population: int | None = None,
    rebellion_streak: int = 0,
    elite_collapse_streak: int = 0,
) -> GameTurnResult:
    """运行一次完整回合，不依赖 FastAPI 或任何具体传输层。

    ``retrieve_history_context`` 的相关 landmark 检索需要行动领域，而领域要到
    ``resolve_full_turn`` 完成意图解析后才可得。因此先预取通用历史传给 resolver，
    再在结算后以真实领域刷新叙事输入；核心结算只执行一次。

    全模糊输入会在结算结果返回后立即短路：状态不变，不生成叙事、不写记忆，
    也不执行 Game Over 检查。非模糊回合在叙事 ``end`` 之后调用
    ``on_turn_ready``，随后才执行 Game Over 检查和记忆提交。
    """
    history_context = retrieve_history_context(
        store,
        domain_tags=[],
        state=state,
    )
    core_result = await resolve_full_turn(
        state,
        player_input,
        client=client,
        rng_seed=rng_seed,
        generate_narrative=False,
        history_context=history_context,
    )

    if core_result.settlement_skipped:
        return GameTurnResult(
            core_result=core_result,
            state=state,
            narrative=None,
            game_over=False,
            game_over_reason=None,
        )

    state_after = core_result.state_after
    narration_input = core_result.narration_input
    if state_after is None or narration_input is None:
        raise RuntimeError("非模糊回合缺少结算后状态或叙事输入")

    domain_tags = _domain_tags(core_result)
    narration_input.history_context = retrieve_history_context(
        store,
        domain_tags=domain_tags,
        state=state,
    )

    await _emit(
        on_narrative_event,
        NarrativeStreamEvent(
            type="start",
            turn=state_after.turn,
            payload={
                "action_description": narration_input.action_description,
                "result_tier": narration_input.result_tier.value,
                "importance": narration_input.importance.value,
            },
        ),
    )

    parts: list[str] = []
    async for chunk in narrate_stream(narration_input, client=client):
        parts.append(chunk)
        await _emit(
            on_narrative_event,
            NarrativeStreamEvent(
                type="delta",
                turn=state_after.turn,
                payload={"text": chunk},
            ),
        )

    if core_result.vague_prompts:
        clarification = "\n\n" + "\n".join(core_result.vague_prompts)
        parts.append(clarification)
        await _emit(
            on_narrative_event,
            NarrativeStreamEvent(
                type="delta",
                turn=state_after.turn,
                payload={"text": clarification},
            ),
        )

    narrative = "".join(parts)
    # commit_turn_memory(full_result=...) 从 FullTurnResult.narrative 读取正文。
    core_result.narrative = narrative

    await _emit(
        on_narrative_event,
        NarrativeStreamEvent(
            type="end",
            turn=state_after.turn,
            payload={
                "full_text": narrative,
                "dimension_changes": core_result.dimension_changes,
            },
        ),
    )
    await _emit(
        on_turn_ready,
        TurnReadyResult(
            core_result=core_result,
            state=state_after,
            narrative=narrative,
        ),
    )

    game_over_reason = check_game_over(
        state_after,
        initial_population=initial_population,
        rebellion_streak=rebellion_streak,
        elite_collapse_streak=elite_collapse_streak,
    )
    if game_over_reason is not None:
        await _emit(
            on_game_over,
            GameOverResult(state=state_after, reason=game_over_reason),
        )

    try:
        await commit_turn_memory(
            store,
            turn=state_after.turn,
            year_start=core_result.state_before.year,
            state_before=core_result.state_before,
            state_after=state_after,
            player_input=core_result.player_input,
            action_description=narration_input.action_description,
            result_tier=(
                core_result.overall_tier.value
                if core_result.overall_tier is not None
                else "failure"
            ),
            dimension_changes=core_result.dimension_changes,
            narrative=narrative,
            domain_tags=domain_tags,
            events=core_result.events,
            client=client,
            full_result=core_result,
        )
    except LLMError:
        # 第 5、10… 回合的中期摘要是附加记忆；此时 turn/landmark 已写入。
        # 摘要失败应降级为缺少本期摘要，不能让会话状态与记忆回合号分叉。
        logger.warning("中期记忆摘要生成失败，本回合保留并继续", exc_info=True)

    return GameTurnResult(
        core_result=core_result,
        state=state_after,
        narrative=narrative,
        game_over=game_over_reason is not None,
        game_over_reason=game_over_reason,
    )
