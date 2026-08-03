"""玩家政令 API：协议校验与回合编排器适配。"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import asdict, dataclass
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.sessions import sessions
from backend.api.websocket import ws_hub
from backend.engine.action_resolver import FullTurnResult
from backend.engine.orchestrator import (
    GameOverResult,
    NarrativeStreamEvent,
    TurnReadyResult,
    run_game_turn,
)
from backend.llm.client import LLMError
from backend.llm.intent_parser import IntentResult
from backend.models.schemas import CivState

router = APIRouter(prefix="/api/game", tags=["action"])
logger = logging.getLogger(__name__)


class SubmitActionRequest(BaseModel):
    input: str
    rng_seed: Optional[int] = None
    stream_id: Optional[UUID] = None


class SubmitActionResponse(BaseModel):
    game_id: str
    turn: int
    settlement_skipped: bool
    vague_prompts: list[str]
    overall_tier: Optional[str]
    turn_years: float
    dimension_changes: dict[str, str]
    events: list[str]
    importance: str
    state: CivState
    intents: list[IntentResult]
    capacity: Optional[dict[str, Any]]
    game_over: bool
    game_over_reason: Optional[str]
    ws_stream_id: Optional[str]


@dataclass(frozen=True)
class _ActionReady:
    """HTTP 响应所需的 state-ready 快照。"""

    core_result: FullTurnResult
    state: CivState
    narrative: Optional[str]


async def _send_narrative_error(
    game_id: str,
    stream_id: str,
    turn: int,
    message: str,
) -> None:
    try:
        await ws_hub.broadcast(
            game_id,
            {
                "type": "narrative_error",
                "turn": turn,
                "stream_id": stream_id,
                "payload": {"message": message},
            },
        )
    except Exception:
        logger.warning("narrative_error 推送失败", exc_info=True)


@router.post("/{game_id}/action", response_model=SubmitActionResponse)
async def submit_action(
    game_id: UUID,
    request: SubmitActionRequest,
) -> SubmitActionResponse:
    """结算一条政令；叙事事件由编排器回调转发到本局 WebSocket。"""
    key = str(game_id)
    session = sessions.get(key)
    if session is None:
        raise HTTPException(status_code=404, detail="游戏不存在")

    player_input = request.input.strip()
    if not player_input:
        raise HTTPException(status_code=400, detail="政令不能为空")
    if session.status == "game_over" and session.finalization_error is None:
        raise HTTPException(status_code=400, detail="游戏已经结束")

    stream_id = str(request.stream_id or uuid4())
    ready_future: asyncio.Future[_ActionReady] = (
        asyncio.get_running_loop().create_future()
    )
    state_committed = False

    async def forward(event: NarrativeStreamEvent) -> None:
        await ws_hub.broadcast(
            key,
            {
                "type": f"narrative_{event.type}",
                "turn": event.turn,
                "stream_id": stream_id,
                "payload": event.payload,
            },
        )

    async def publish_ready(
        core_result: FullTurnResult,
        state: CivState,
        narrative: Optional[str],
    ) -> None:
        """提交会话状态并解除 HTTP 等待；WS 失败不能阻塞结算。"""
        nonlocal state_committed
        # resolve_full_turn 已推进 turn/year；API 只替换会话状态。
        session.state = state
        state_committed = True
        session.status = "active"
        session.game_over_reason = None
        try:
            await ws_hub.broadcast(
                key,
                {
                    "type": "state_update",
                    "turn": state.turn,
                    "stream_id": stream_id,
                    "payload": {
                        "state": state.model_dump(mode="json"),
                        "dimension_changes": core_result.dimension_changes,
                    },
                },
            )
        except Exception:
            # orchestrator 会将 lifecycle callback 当作旁路；这里同样保证
            # 传输层异常不会让 ready future 永久挂起。
            logger.warning("state_update 推送失败，HTTP 仍返回状态", exc_info=True)
        if not ready_future.done():
            ready_future.set_result(
                _ActionReady(
                    core_result=core_result,
                    state=state,
                    narrative=narrative,
                )
            )

    async def on_turn_ready(result: TurnReadyResult) -> None:
        await publish_ready(
            result.core_result,
            result.state,
            result.narrative,
        )

    async def on_game_over(result: GameOverResult) -> None:
        session.status = "game_over"
        session.game_over_reason = result.reason
        await ws_hub.broadcast(
            key,
            {
                "type": "game_over",
                "turn": result.state.turn,
                "stream_id": stream_id,
                "payload": {"reason": result.reason},
            },
        )

    async def run_in_background() -> None:
        """串行运行完整编排，ready 后继续持锁完成记忆收尾。"""
        try:
            async with session.lock:
                try:
                    # 请求可能已在锁上等待了上一回合，入锁后重新核对会话。
                    if session.finalization_error is not None:
                        if not ready_future.done():
                            ready_future.set_exception(
                                HTTPException(
                                    status_code=503,
                                    detail="上一回合收尾失败，会话已停止结算",
                                )
                            )
                        return
                    if session.status == "game_over":
                        if not ready_future.done():
                            ready_future.set_exception(
                                HTTPException(status_code=400, detail="游戏已经结束")
                            )
                        return

                    turn_seed = (
                        request.rng_seed
                        if request.rng_seed is not None
                        else session.next_rng_seed()
                    )
                    turn_result = await run_game_turn(
                        session.state,
                        player_input,
                        store=session.store,
                        rng_seed=turn_seed,
                        on_narrative_event=forward,
                        on_turn_ready=on_turn_ready,
                        on_game_over=on_game_over,
                    )

                    if not ready_future.done():
                        if turn_result.settlement_skipped:
                            # 全模糊分支不产生 state-ready 回调。
                            session.status = "awaiting_clarification"
                            ready_future.set_result(
                                _ActionReady(
                                    core_result=turn_result.core_result,
                                    state=turn_result.state,
                                    narrative=turn_result.narrative,
                                )
                            )
                        else:
                            # lifecycle callback 属于旁路，编排器会吞掉其异常。
                            # 若回调未能解除 future，用完整返回值作最终兜底。
                            await publish_ready(
                                turn_result.core_result,
                                turn_result.state,
                                turn_result.narrative,
                            )
                except LLMError as exc:
                    if state_committed:
                        session.finalization_error = f"{type(exc).__name__}: {exc}"
                    error_turn = (
                        session.state.turn
                        if state_committed
                        else session.state.turn + 1
                    )
                    await _send_narrative_error(
                        key, stream_id, error_turn, str(exc)
                    )
                    if state_committed:
                        logger.error(
                            "回合 state-ready 后 LLM 收尾失败",
                            exc_info=True,
                        )
                    elif not ready_future.done():
                        ready_future.set_exception(
                            HTTPException(status_code=503, detail=str(exc))
                        )
                except ValueError as exc:
                    if state_committed:
                        session.finalization_error = f"{type(exc).__name__}: {exc}"
                    error_turn = (
                        session.state.turn
                        if state_committed
                        else session.state.turn + 1
                    )
                    await _send_narrative_error(
                        key, stream_id, error_turn, str(exc)
                    )
                    if state_committed:
                        logger.error(
                            "回合 state-ready 后收尾失败",
                            exc_info=True,
                        )
                    elif not ready_future.done():
                        ready_future.set_exception(
                            HTTPException(status_code=400, detail=str(exc))
                        )
                except Exception as exc:
                    if state_committed:
                        session.finalization_error = f"{type(exc).__name__}: {exc}"
                    error_turn = (
                        session.state.turn
                        if state_committed
                        else session.state.turn + 1
                    )
                    await _send_narrative_error(
                        key,
                        stream_id,
                        error_turn,
                        "回合处理失败",
                    )
                    if not state_committed and not ready_future.done():
                        ready_future.set_exception(
                            HTTPException(status_code=500, detail="回合处理失败")
                        )
                    logger.exception("后台回合处理失败")
        except asyncio.CancelledError:
            # 无论任务在等锁还是 LLM I/O 处被取消，都不能留下
            # 一个永久无结果的 ready future。
            if state_committed and session.finalization_error is None:
                session.finalization_error = "CancelledError: 回合收尾任务已取消"
            if not ready_future.done():
                ready_future.cancel()
            raise

    task = asyncio.create_task(run_in_background())

    def unblock_ready_if_worker_was_cancelled(
        completed: asyncio.Task[Any],
    ) -> None:
        # Task 可能在协程获得第一次运行机会之前就被取消，
        # 此时 run_in_background 内的 CancelledError 分支不会执行。
        if completed.cancelled() and not ready_future.done():
            ready_future.cancel()

    task.add_done_callback(unblock_ready_if_worker_was_cancelled)
    session.track_background_task(task)

    # 只等到数值状态已推送；记忆与 Game Over 在后台任务继续收尾。
    try:
        ready = await asyncio.shield(ready_future)
    except asyncio.CancelledError:
        current = asyncio.current_task()
        request_was_cancelled = current is not None and current.cancelling() > 0
        if request_was_cancelled:
            if not state_committed:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
                if ready_future.done() and not ready_future.cancelled():
                    # HTTP 请求已离开，显式取出竞态中已写入的异常，
                    # 避免产生 "Future exception was never retrieved" 警告。
                    ready_future.exception()
            # state-ready 已提交时不取消 worker，让它持锁完成记忆收尾。
            raise
        # ready future 由 worker 自身取消，而非 HTTP 请求断开。
        raise HTTPException(status_code=503, detail="回合任务已取消")
    core = ready.core_result

    capacity = asdict(core.capacity) if core.capacity is not None else None
    return SubmitActionResponse(
        game_id=key,
        turn=ready.state.turn,
        settlement_skipped=core.settlement_skipped,
        vague_prompts=core.vague_prompts,
        overall_tier=(
            core.overall_tier.value if core.overall_tier is not None else None
        ),
        turn_years=core.turn_years,
        dimension_changes=core.dimension_changes,
        events=core.events,
        importance=core.importance.value,
        state=ready.state,
        intents=core.intents,
        capacity=capacity,
        # Game Over 在 state-ready 之后检查，命中时由 WS 独立通知。
        game_over=False,
        game_over_reason=None,
        ws_stream_id=None if core.settlement_skipped else stream_id,
    )
