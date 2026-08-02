"""记忆系统单元测试（无 LLM）：近期格式化、landmark 触发、关键词检索、组装。"""

from __future__ import annotations

from backend.memory.landmark import create_landmarks_from_turn, detect_landmark_events, embed_text
from backend.memory.recent import build_recent_context, format_recent_history, load_recent_turns
from backend.memory.retriever import retrieve_history_context
from backend.memory.store import MemoryStore, TurnRecord
from backend.memory.summary import should_trigger_summary
from backend.models.schemas import LandSystem
from backend.templates.civilizations import load_civ_state


def _seed_turn(
    store: MemoryStore,
    turn: int,
    *,
    domain: str,
    action: str,
    tier: str = "success",
    year: float = -1046.0,
) -> TurnRecord:
    return store.add_turn(
        TurnRecord(
            game_id=store.game_id,
            turn=turn,
            year_start=year + turn - 1,
            year_end=year + turn,
            player_input=action,
            action_description=action,
            result_tier=tier,
            dimension_changes={"authority": "+3", "stability": "+1"},
            narrative=f"史官记：第{turn}回合{action}，结果{tier}。",
            summary=f"{action}→{tier}",
            domain_tags=[domain],
        )
    )


class TestRecentMemory:
    def test_loads_last_five_in_order(self) -> None:
        store = MemoryStore()
        for i in range(1, 9):
            _seed_turn(store, i, domain="economic", action=f"行动{i}")
        recent = load_recent_turns(store, limit=5)
        assert [t.turn for t in recent] == [4, 5, 6, 7, 8]
        text = format_recent_history(recent)
        assert "第4回合" in text
        assert "第8回合" in text
        assert "第3回合" not in text

    def test_build_recent_context(self) -> None:
        store = MemoryStore()
        _seed_turn(store, 1, domain="political", action="迁都")
        ctx = build_recent_context(store)
        assert "迁都" in ctx
        assert "political" in ctx or "政治" in ctx or "领域：political" in ctx


class TestSummaryTrigger:
    def test_every_fifth_turn(self) -> None:
        assert should_trigger_summary(5)
        assert should_trigger_summary(10)
        assert not should_trigger_summary(4)
        assert not should_trigger_summary(0)


class TestLandmark:
    def test_embed_text_reserved(self) -> None:
        assert embed_text("任意文本") is None

    def test_institutional_change_creates_landmark(self) -> None:
        before = load_civ_state("zhou")
        after = before.model_copy(deep=True)
        # 西周默认非 yeoman；改土地制度触发制度 landmark
        new_land = (
            LandSystem.YEOMAN_SMALLHOLD
            if before.land_system != LandSystem.YEOMAN_SMALLHOLD
            else LandSystem.NOBLE_ESTATE
        )
        after.land_system = new_land
        drafts = detect_landmark_events(
            turn=5,
            year=after.year,
            state_before=before,
            state_after=after,
            domain_tags=["political"],
            action_description="迁都并更张田制",
            result_tier="great_success",
        )
        assert any(d["trigger"] == "institutional" for d in drafts)
        assert any("political" in d["tags"] for d in drafts)

    def test_tech_breakthrough(self) -> None:
        before = load_civ_state("zhou")
        after = before.model_copy(deep=True)
        after.tech_engineering = before.tech_engineering + 0.6
        drafts = detect_landmark_events(
            turn=3,
            year=after.year,
            state_before=before,
            state_after=after,
            domain_tags=["technology"],
            action_description="推广高炉炼铁",
            result_tier="success",
        )
        assert any(d["trigger"] == "tech_breakthrough" for d in drafts)

    def test_keyword_retrieve_political_landmark(self) -> None:
        store = MemoryStore()
        before = load_civ_state("zhou")
        after = before.model_copy(deep=True)
        after.land_system = (
            LandSystem.YEOMAN_SMALLHOLD
            if before.land_system != LandSystem.YEOMAN_SMALLHOLD
            else LandSystem.NOBLE_ESTATE
        )
        created = create_landmarks_from_turn(
            store,
            turn=5,
            year=float(after.year),
            state_before=before,
            state_after=after,
            domain_tags=["political"],
            action_description="迁都洛邑",
            result_tier="great_success",
        )
        assert created
        assert all(lm.embedding is None for lm in created)

        # 再塞一条无关军事 landmark
        after2 = after.model_copy(deep=True)
        after2.territory_core = int(after.territory_core * 1.3)
        create_landmarks_from_turn(
            store,
            turn=6,
            year=float(after2.year),
            state_before=after,
            state_after=after2,
            domain_tags=["military"],
            action_description="开疆拓土",
            result_tier="success",
        )

        ctx = retrieve_history_context(
            store,
            domain_tags=["political"],
            state=after,
            landmark_limit=5,
        )
        assert "【相关史事】" in ctx
        assert "迁都" in ctx or "制度" in ctx
        assert "【路径积累】" in ctx
        # 政治检索不应被军事扩张独占
        assert "political" in ctx.lower() or "制度" in ctx


class TestRetrieverAssembly:
    def test_includes_three_layers_and_accumulations(self) -> None:
        store = MemoryStore()
        for i in range(1, 6):
            _seed_turn(store, i, domain="economic", action=f"兴修{i}")
        state = load_civ_state("zhou")
        # 抬高行政积累，检验积累段落
        state = state.model_copy(
            update={
                "accumulations": state.accumulations.model_copy(
                    update={"administrative": 1.5}
                )
            }
        )
        ctx = retrieve_history_context(
            store,
            domain_tags=["political"],
            state=state,
        )
        assert "【近期历程】" in ctx
        assert "【近代史摘要】" in ctx
        assert "【路径积累】" in ctx
        assert "行政经验" in ctx
        assert "深厚" in ctx
