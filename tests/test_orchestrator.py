"""完整回合编排器集成测试（离线 Fake LLM）。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from backend.engine import orchestrator
from backend.engine.orchestrator import (
    NarrativeStreamEvent,
    TurnReadyResult,
    run_game_turn,
)
from backend.llm.client import LLMError
from backend.llm.intent_parser import IntentResult
from backend.memory.store import MemoryStore
from backend.templates.civilizations import load_civ_state


class FakeLLMClient:
    """只实现本测试会走到的结构化意图与流式叙事接口。"""

    def __init__(self) -> None:
        self.stream_calls = 0

    async def call_json(
        self,
        messages: list[dict[str, str]],
        response_model: type[Any],
        **_: Any,
    ) -> Any:
        if response_model is not IntentResult:
            raise LLMError("fake summary failure")
        player_prompt = messages[-1]["content"]
        if "发展" in player_prompt:
            return IntentResult.model_validate(
                {
                    "is_too_vague": True,
                    "clarification_prompt": "欲发展何业？请明示具体措置。",
                }
            )
        return IntentResult.model_validate(
            {
                "action_domain": "economic",
                "action_type": "兴修水利",
                "action_description": "征发民力，修整沟渠与堤堰",
                "cognitive_gap": 0,
                "resistance_sources": ["地方贵族"],
                "beneficiaries": ["农户"],
                "prerequisites": {
                    "met": True,
                    "details": "已有基础农具与徭役组织",
                    "nearest_alternative": None,
                },
                "is_knowledge_injection": False,
                "knowledge_detail_level": None,
                "is_too_vague": False,
                "clarification_prompt": None,
                "scale": "medium",
                "time_estimate_years": 3.0,
                "time_estimate_reasoning": "沟渠施工跨越数个农时",
            }
        )

    async def call_text_stream(
        self,
        messages: list[dict[str, str]],
        **_: Any,
    ) -> AsyncIterator[str]:
        self.stream_calls += 1
        assert "沟渠" in messages[-1]["content"]
        for chunk in ("公元前的王畿内，", "沟渠渐次贯通。"):
            yield chunk


def test_run_game_turn_updates_once_writes_memory_and_checks_game_over(
    monkeypatch: Any,
) -> None:
    state = load_civ_state("zhou")
    initial_turn = state.turn
    initial_year = state.year
    initial_population = state.population
    store = MemoryStore(game_id="orchestrator-success")
    events: list[NarrativeStreamEvent] = []
    ready_results: list[TurnReadyResult] = []
    game_over_checks: list[int] = []
    timeline: list[str] = []
    original_commit = orchestrator.commit_turn_memory

    def fake_check_game_over(checked_state: Any) -> None:
        timeline.append("game_over_check")
        game_over_checks.append(checked_state.turn)
        return None

    async def tracked_commit(*args: Any, **kwargs: Any) -> Any:
        timeline.append("memory_commit")
        return await original_commit(*args, **kwargs)

    monkeypatch.setattr(orchestrator, "check_game_over", fake_check_game_over)
    monkeypatch.setattr(orchestrator, "commit_turn_memory", tracked_commit)

    async def collect(event: NarrativeStreamEvent) -> None:
        events.append(event)
        timeline.append(f"narrative_{event.type}")

    async def collect_ready(result: TurnReadyResult) -> None:
        ready_results.append(result)
        timeline.append("state_ready")

    result = asyncio.run(
        run_game_turn(
            state,
            "兴修水利",
            store=store,
            client=FakeLLMClient(),
            rng_seed=42,
            on_narrative_event=collect,
            on_turn_ready=collect_ready,
        )
    )

    assert not result.settlement_skipped
    assert state.turn == initial_turn
    assert state.year == initial_year
    assert result.state.turn == initial_turn + 1
    assert result.state.year == initial_year + 3.0
    assert result.state.population != initial_population
    assert result.core_result.state_after == result.state
    assert result.narrative == "公元前的王畿内，沟渠渐次贯通。"
    assert [event.type for event in events] == ["start", "delta", "delta", "end"]
    assert ready_results == [
        TurnReadyResult(
            core_result=result.core_result,
            state=result.state,
            narrative=result.narrative,
        )
    ]
    assert timeline == [
        "narrative_start",
        "narrative_delta",
        "narrative_delta",
        "narrative_end",
        "state_ready",
        "game_over_check",
        "memory_commit",
    ]

    turns = store.get_all_turns()
    assert len(turns) == 1
    assert turns[0].turn == initial_turn + 1
    assert turns[0].narrative == result.narrative
    assert turns[0].state_after == result.state.model_dump()
    assert game_over_checks == [initial_turn + 1]
    assert not result.game_over


def test_run_game_turn_vague_input_short_circuits_without_memory(
    monkeypatch: Any,
) -> None:
    state = load_civ_state("zhou")
    store = MemoryStore(game_id="orchestrator-vague")
    client = FakeLLMClient()
    events: list[NarrativeStreamEvent] = []
    game_over_checks: list[int] = []

    def fake_check_game_over(checked_state: Any) -> None:
        game_over_checks.append(checked_state.turn)
        return None

    monkeypatch.setattr(orchestrator, "check_game_over", fake_check_game_over)

    result = asyncio.run(
        run_game_turn(
            state,
            "发展",
            store=store,
            client=client,
            on_narrative_event=events.append,
        )
    )

    assert result.settlement_skipped
    assert result.state is state
    assert result.state.turn == 0
    assert result.core_result.state_after is None
    assert result.core_result.vague_prompts == ["欲发展何业？请明示具体措置。"]
    assert result.narrative is None
    assert store.get_all_turns() == []
    assert store.get_recent_summaries() == []
    assert store.get_all_landmarks() == []
    assert client.stream_calls == 0
    assert events == []
    assert game_over_checks == []


def test_summary_llm_failure_does_not_split_state_from_memory() -> None:
    state = load_civ_state("zhou").model_copy(update={"turn": 4})
    store = MemoryStore(game_id="orchestrator-summary-failure")
    events: list[NarrativeStreamEvent] = []

    result = asyncio.run(
        run_game_turn(
            state,
            "兴修水利",
            store=store,
            client=FakeLLMClient(),
            rng_seed=42,
            on_narrative_event=events.append,
        )
    )

    assert result.state.turn == 5
    assert [turn.turn for turn in store.get_all_turns()] == [5]
    assert store.get_recent_summaries() == []
    assert events[-1].type == "end"


def test_turn_ready_precedes_slow_summary_and_memory_finishes_in_background() -> None:
    """第 5 回合叙事结束即产出状态，不等待慢摘要。"""

    async def scenario() -> None:
        class SlowSummaryLLMClient(FakeLLMClient):
            def __init__(self) -> None:
                super().__init__()
                self.summary_started = asyncio.Event()
                self.release_summary = asyncio.Event()

            async def call_json(
                self,
                messages: list[dict[str, str]],
                response_model: type[Any],
                **kwargs: Any,
            ) -> Any:
                if response_model is IntentResult:
                    return await super().call_json(
                        messages,
                        response_model,
                        **kwargs,
                    )
                self.summary_started.set()
                await self.release_summary.wait()
                return response_model.model_validate(
                    {
                        "content": "水利建设逐步改善王畿生产，农业积累持续增长，"
                        "地方贵族与农户围绕征发形成新的协调关系。",
                        "domain_frequencies": {"economic": 1},
                    }
                )

        state = load_civ_state("zhou").model_copy(update={"turn": 4})
        store = MemoryStore(game_id="orchestrator-slow-summary")
        client = SlowSummaryLLMClient()
        timeline: list[str] = []
        ready = asyncio.Event()

        async def collect_narrative(event: NarrativeStreamEvent) -> None:
            if event.type == "end":
                timeline.append("narrative_end")

        async def collect_ready(_: TurnReadyResult) -> None:
            timeline.append("state_update")
            ready.set()

        task = asyncio.create_task(
            run_game_turn(
                state,
                "兴修水利",
                store=store,
                client=client,
                rng_seed=42,
                on_narrative_event=collect_narrative,
                on_turn_ready=collect_ready,
            )
        )

        await asyncio.wait_for(ready.wait(), timeout=1)
        await asyncio.wait_for(client.summary_started.wait(), timeout=1)

        assert timeline == ["narrative_end", "state_update"]
        assert not task.done()
        assert [turn.turn for turn in store.get_all_turns()] == [5]
        assert store.get_recent_summaries() == []

        client.release_summary.set()
        result = await asyncio.wait_for(task, timeout=1)

        assert result.state.turn == 5
        assert [turn.turn for turn in store.get_all_turns()] == [5]
        assert [summary.turn_end for summary in store.get_recent_summaries()] == [5]

    asyncio.run(scenario())
