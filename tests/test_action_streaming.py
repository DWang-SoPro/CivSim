"""action API 的 state-ready 响应、后台收尾与按局排队。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from backend.api import action
from backend.api.action import SubmitActionRequest, submit_action
from backend.api.sessions import GameSession, sessions
from backend.engine.orchestrator import (
    GameOverResult,
    GameTurnResult,
    NarrativeStreamEvent,
    TurnReadyResult,
)
from backend.memory.store import MemoryStore
from backend.templates.civilizations import load_civ_state


def _session() -> GameSession:
    game_id = str(uuid4())
    session = GameSession(
        game_id=game_id,
        state=load_civ_state("zhou"),
        store=MemoryStore(game_id=game_id),
        seed=100,
    )
    sessions.add(session)
    return session


def _core(*, skipped: bool = False) -> Any:
    return SimpleNamespace(
        settlement_skipped=skipped,
        vague_prompts=["欲兴何业？请明示。"] if skipped else [],
        overall_tier=None,
        turn_years=0.0 if skipped else 1.0,
        dimension_changes={} if skipped else {"stability": "+1"},
        events=[],
        importance=SimpleNamespace(value="normal"),
        intents=[],
        capacity=None,
    )


def test_action_returns_at_state_ready_and_next_action_waits_for_finalize(
    monkeypatch: Any,
) -> None:
    sessions.clear()
    session = _session()

    async def scenario() -> None:
        frames: list[dict[str, Any]] = []
        calls: list[int] = []
        finalized: list[int] = []
        release_first_finalize = asyncio.Event()

        async def broadcast(_game_id: str, message: dict[str, Any]) -> None:
            frames.append(message)

        async def fake_run_game_turn(
            state: Any,
            _player_input: str,
            **kwargs: Any,
        ) -> GameTurnResult:
            call_index = len(calls)
            calls.append(state.turn)
            state_after = state.model_copy(
                update={"turn": state.turn + 1, "year": state.year + 1.0}
            )
            core = _core()
            await kwargs["on_narrative_event"](
                NarrativeStreamEvent(
                    type="end",
                    turn=state_after.turn,
                    payload={"full_text": "叙事", "dimension_changes": {}},
                )
            )
            await kwargs["on_turn_ready"](
                TurnReadyResult(
                    core_result=core,
                    state=state_after,
                    narrative="叙事",
                )
            )
            if call_index == 0:
                # 模拟 ready 之后仍在进行的记忆提交。
                await release_first_finalize.wait()
            finalized.append(state_after.turn)
            return GameTurnResult(
                core_result=core,
                state=state_after,
                narrative="叙事",
                game_over=False,
                game_over_reason=None,
            )

        monkeypatch.setattr(action.ws_hub, "broadcast", broadcast)
        monkeypatch.setattr(action, "run_game_turn", fake_run_game_turn)

        client_stream_id = uuid4()
        first = await asyncio.wait_for(
            submit_action(
                UUID(session.game_id),
                SubmitActionRequest.model_validate(
                    {
                        "input": "兴修水利",
                        "stream_id": str(client_stream_id),
                    }
                ),
            ),
            timeout=1.0,
        )
        assert first.turn == 1
        assert first.ws_stream_id == str(client_stream_id)
        assert session.state.turn == 1
        assert session.lock.locked()
        assert session.background_tasks
        assert finalized == []
        assert [frame["type"] for frame in frames] == [
            "narrative_end",
            "state_update",
        ]
        assert frames[-1]["payload"]["state"]["turn"] == 1
        assert all(
            frame["stream_id"] == str(client_stream_id)
            for frame in frames
        )

        second_task = asyncio.create_task(
            submit_action(
                UUID(session.game_id),
                SubmitActionRequest(input="整顿吏治"),
            )
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert calls == [0]
        assert not second_task.done()

        release_first_finalize.set()
        second = await asyncio.wait_for(second_task, timeout=1.0)
        assert second.turn == 2
        assert calls == [0, 1]

        pending = tuple(session.background_tasks)
        if pending:
            await asyncio.gather(*pending)
        assert not session.lock.locked()
        assert finalized == [1, 2]

    try:
        asyncio.run(scenario())
    finally:
        sessions.clear()


def test_game_over_frame_follows_state_update(monkeypatch: Any) -> None:
    sessions.clear()
    session = _session()

    async def scenario() -> None:
        frames: list[dict[str, Any]] = []

        async def broadcast(_game_id: str, message: dict[str, Any]) -> None:
            frames.append(message)

        async def fake_run_game_turn(
            state: Any,
            _player_input: str,
            **kwargs: Any,
        ) -> GameTurnResult:
            state_after = state.model_copy(
                update={"turn": state.turn + 1, "population": 0}
            )
            core = _core()
            await kwargs["on_turn_ready"](
                TurnReadyResult(
                    core_result=core,
                    state=state_after,
                    narrative="文明崩溃。",
                )
            )
            await kwargs["on_game_over"](
                GameOverResult(
                    state=state_after,
                    reason="civilization_collapse",
                )
            )
            return GameTurnResult(
                core_result=core,
                state=state_after,
                narrative="文明崩溃。",
                game_over=True,
                game_over_reason="civilization_collapse",
            )

        monkeypatch.setattr(action.ws_hub, "broadcast", broadcast)
        monkeypatch.setattr(action, "run_game_turn", fake_run_game_turn)

        response = await asyncio.wait_for(
            submit_action(
                UUID(session.game_id),
                SubmitActionRequest(input="孤注一掷"),
            ),
            timeout=1.0,
        )
        pending = tuple(session.background_tasks)
        if pending:
            await asyncio.gather(*pending)

        assert response.turn == 1
        # HTTP 是 state-ready 快照；终局通知以随后的 WS 帧为准。
        assert not response.game_over
        assert session.status == "game_over"
        assert session.game_over_reason == "civilization_collapse"
        assert [frame["type"] for frame in frames] == [
            "state_update",
            "game_over",
        ]
        assert frames[1]["payload"] == {"reason": "civilization_collapse"}

    try:
        asyncio.run(scenario())
    finally:
        sessions.clear()


def test_completed_turn_falls_back_when_ready_callback_was_not_delivered(
    monkeypatch: Any,
) -> None:
    """编排器的 lifecycle 回调是旁路；丢失时 HTTP 不得永久挂起。"""
    sessions.clear()
    session = _session()

    async def scenario() -> None:
        frames: list[dict[str, Any]] = []

        async def broadcast(_game_id: str, message: dict[str, Any]) -> None:
            frames.append(message)

        async def fake_run_game_turn(
            state: Any,
            _player_input: str,
            **_kwargs: Any,
        ) -> GameTurnResult:
            state_after = state.model_copy(
                update={"turn": state.turn + 1, "year": state.year + 1.0}
            )
            # 模拟 on_turn_ready 在编排器旁路中失败且被吞掉。
            return GameTurnResult(
                core_result=_core(),
                state=state_after,
                narrative="叙事",
                game_over=False,
                game_over_reason=None,
            )

        monkeypatch.setattr(action.ws_hub, "broadcast", broadcast)
        monkeypatch.setattr(action, "run_game_turn", fake_run_game_turn)

        response = await asyncio.wait_for(
            submit_action(
                UUID(session.game_id),
                SubmitActionRequest(input="兴修水利"),
            ),
            timeout=1.0,
        )
        pending = tuple(session.background_tasks)
        if pending:
            await asyncio.gather(*pending)

        assert response.turn == 1
        assert session.state.turn == 1
        assert [frame["type"] for frame in frames] == ["state_update"]

    try:
        asyncio.run(scenario())
    finally:
        sessions.clear()


def test_request_cancel_before_ready_cancels_worker_without_ghost_turn(
    monkeypatch: Any,
) -> None:
    sessions.clear()
    session = _session()

    async def scenario() -> None:
        worker_started = asyncio.Event()
        worker_stopped = asyncio.Event()
        never_ready = asyncio.Event()

        async def fake_run_game_turn(*_args: Any, **_kwargs: Any) -> Any:
            worker_started.set()
            try:
                await never_ready.wait()
            finally:
                worker_stopped.set()

        monkeypatch.setattr(action, "run_game_turn", fake_run_game_turn)

        request_task = asyncio.create_task(
            submit_action(
                UUID(session.game_id),
                SubmitActionRequest(input="兴修水利"),
            )
        )
        await worker_started.wait()
        request_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request_task

        await worker_stopped.wait()
        await asyncio.sleep(0)
        assert session.state.turn == 0
        assert not session.lock.locked()
        assert not session.background_tasks
        assert session.finalization_error is None

    try:
        asyncio.run(scenario())
    finally:
        sessions.clear()


def test_request_cancel_after_state_commit_keeps_finalization_worker(
    monkeypatch: Any,
) -> None:
    sessions.clear()
    session = _session()

    async def scenario() -> None:
        state_update_started = asyncio.Event()
        release_state_update = asyncio.Event()
        finalize_started = asyncio.Event()
        release_finalize = asyncio.Event()
        worker_cancelled = False

        async def broadcast(_game_id: str, message: dict[str, Any]) -> None:
            if message["type"] == "state_update":
                state_update_started.set()
                await release_state_update.wait()

        async def fake_run_game_turn(
            state: Any,
            _player_input: str,
            **kwargs: Any,
        ) -> GameTurnResult:
            nonlocal worker_cancelled
            state_after = state.model_copy(update={"turn": state.turn + 1})
            core = _core()
            try:
                await kwargs["on_turn_ready"](
                    TurnReadyResult(
                        core_result=core,
                        state=state_after,
                        narrative="叙事",
                    )
                )
                finalize_started.set()
                await release_finalize.wait()
            except asyncio.CancelledError:
                worker_cancelled = True
                raise
            return GameTurnResult(
                core_result=core,
                state=state_after,
                narrative="叙事",
                game_over=False,
                game_over_reason=None,
            )

        monkeypatch.setattr(action.ws_hub, "broadcast", broadcast)
        monkeypatch.setattr(action, "run_game_turn", fake_run_game_turn)

        request_task = asyncio.create_task(
            submit_action(
                UUID(session.game_id),
                SubmitActionRequest(input="兴修水利"),
            )
        )
        await state_update_started.wait()
        assert session.state.turn == 1

        request_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request_task
        assert session.lock.locked()
        assert session.background_tasks

        release_state_update.set()
        await finalize_started.wait()
        assert not worker_cancelled
        release_finalize.set()
        pending = tuple(session.background_tasks)
        if pending:
            await asyncio.gather(*pending)

        assert not worker_cancelled
        assert not session.lock.locked()
        assert session.finalization_error is None

    try:
        asyncio.run(scenario())
    finally:
        sessions.clear()


def test_worker_cancellation_unblocks_waiting_endpoint(monkeypatch: Any) -> None:
    sessions.clear()
    session = _session()

    async def scenario() -> None:
        worker_started = asyncio.Event()
        blocker = asyncio.Event()

        async def fake_run_game_turn(*_args: Any, **_kwargs: Any) -> Any:
            worker_started.set()
            await blocker.wait()

        monkeypatch.setattr(action, "run_game_turn", fake_run_game_turn)

        request_task = asyncio.create_task(
            submit_action(
                UUID(session.game_id),
                SubmitActionRequest(input="兴修水利"),
            )
        )
        await worker_started.wait()
        worker = next(iter(session.background_tasks))
        worker.cancel()

        with pytest.raises(HTTPException) as exc_info:
            await asyncio.wait_for(request_task, timeout=1.0)
        assert exc_info.value.status_code == 503
        assert session.state.turn == 0
        assert not session.lock.locked()

    try:
        asyncio.run(scenario())
    finally:
        sessions.clear()


def test_unknown_error_after_ready_blocks_following_action(monkeypatch: Any) -> None:
    sessions.clear()
    session = _session()

    async def scenario() -> None:
        calls = 0

        async def broadcast(_game_id: str, _message: dict[str, Any]) -> None:
            return None

        async def fake_run_game_turn(
            state: Any,
            _player_input: str,
            **kwargs: Any,
        ) -> GameTurnResult:
            nonlocal calls
            calls += 1
            state_after = state.model_copy(update={"turn": state.turn + 1})
            await kwargs["on_turn_ready"](
                TurnReadyResult(
                    core_result=_core(),
                    state=state_after,
                    narrative="叙事",
                )
            )
            raise RuntimeError("记忆写入失败")

        monkeypatch.setattr(action.ws_hub, "broadcast", broadcast)
        monkeypatch.setattr(action, "run_game_turn", fake_run_game_turn)

        first = await asyncio.wait_for(
            submit_action(
                UUID(session.game_id),
                SubmitActionRequest(input="兴修水利"),
            ),
            timeout=1.0,
        )
        assert first.turn == 1

        pending = tuple(session.background_tasks)
        if pending:
            await asyncio.gather(*pending)
        assert session.finalization_error == "RuntimeError: 记忆写入失败"

        with pytest.raises(HTTPException) as exc_info:
            await submit_action(
                UUID(session.game_id),
                SubmitActionRequest(input="整顿吏治"),
            )
        assert exc_info.value.status_code == 503
        assert calls == 1

    try:
        asyncio.run(scenario())
    finally:
        # 所有 worker 已在断言前完成，清理时不遗留跨测试任务。
        sessions.clear()
