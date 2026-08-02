"""六个文明模板：合法 CivState + 完整数值结算串联 + 开局盈余校准。"""

from __future__ import annotations

import math

import pytest

from backend.engine.action_resolver import FakeActionInput, resolve_turn
from backend.engine.food import calculate_food_surplus_from_state
from backend.engine.governance import governance_efficiency_from_state
from backend.models.schemas import ActionResultTier, CivState
from backend.templates.civilizations import (
    CIVILIZATION_TEMPLATES,
    check_extraction_prerequisites,
    list_templates,
    load_civ_state,
    validate_production_relations,
)

TEMPLATE_IDS = ["sumer", "egypt", "harappa", "babylon", "zhou", "greece"]


def _assert_finite_nonneg_state(state: CivState) -> None:
    """断言关键数值有限且在合法范围内。"""
    assert state.population >= 0
    assert 0.0 <= state.stability <= 100.0
    assert 0.0 <= state.authority <= 100.0
    assert state.tech_agriculture >= 0.0
    assert state.biome_fertility >= 0.0
    for field in ("academic", "military", "commercial", "administrative", "cultural"):
        val = getattr(state.accumulations, field)
        assert val >= 0.0
        assert not math.isnan(val)
        assert not math.isinf(val)


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
class TestCivilizationTemplates:
    def test_loads_as_valid_civ_state(self, template_id: str) -> None:
        state = load_civ_state(template_id)
        assert isinstance(state, CivState)
        assert state.template_id == template_id
        assert state.civ_name
        assert state.population > 0
        _assert_finite_nonneg_state(state)

    def test_production_relations_structurally_valid(self, template_id: str) -> None:
        state = load_civ_state(template_id)
        ok, issues = validate_production_relations(state)
        assert ok, f"{template_id} 不合法: {issues}"

    def test_full_engine_pipeline(self, template_id: str) -> None:
        """喂假行动结果，串联全部引擎，输出合法。"""
        state = load_civ_state(template_id)
        action = FakeActionInput(
            domain="political",
            cognitive_gap=1.0,
            turn_years=2.0,
            tier=ActionResultTier.SUCCESS,
            action_stability_delta=2.0,
            action_authority_delta=1.0,
            random_factor=1.0,
        )
        result = resolve_turn(state, action)

        assert isinstance(result.state_after, CivState)
        assert result.state_after.turn == state.turn + 1
        assert result.result_tier == ActionResultTier.SUCCESS
        assert 0.0 <= result.p_success <= 1.0
        assert 0.0 <= result.governance_efficiency <= 1.0
        assert result.food_surplus_ratio >= 0.0
        assert not math.isnan(result.food_surplus_ratio)
        assert not math.isnan(result.stability_delta)
        assert not math.isnan(result.authority_delta)
        _assert_finite_nonneg_state(result.state_after)

        food = calculate_food_surplus_from_state(state)
        gov = governance_efficiency_from_state(state)
        assert food == pytest.approx(result.food_surplus_ratio)
        assert gov == pytest.approx(result.governance_efficiency)


def test_all_six_templates_registered() -> None:
    assert set(list_templates()) == set(TEMPLATE_IDS)
    assert len(CIVILIZATION_TEMPLATES) == 6


def test_greece_extraction_prerequisites_pass_via_commerce() -> None:
    """希腊官僚化=0.2，但商业积累=0.6，应通过货币税/商业税 OR 分支。"""
    state = load_civ_state("greece")
    assert state.bureaucratization == pytest.approx(0.2)
    assert state.accumulations.commercial == pytest.approx(0.6)
    issues = check_extraction_prerequisites(state)
    assert issues == []
    ok, all_issues = validate_production_relations(state)
    assert ok, all_issues


def test_template_opening_food_surplus_in_reasonable_range() -> None:
    """六模板开局盈余率均在合理区间 0.9–1.6。

    西周 ≈1.2（YIELD_FACTOR 校准锚点）；希腊/苏美尔经 agricultural_modifier 校准至 ≈0.9；
    其余宜在 1.0–1.5。
    """
    ratios = {
        tid: calculate_food_surplus_from_state(load_civ_state(tid))
        for tid in TEMPLATE_IDS
    }

    assert ratios["zhou"] == pytest.approx(1.2, abs=0.01)

    for tid, r in ratios.items():
        assert 0.9 <= r <= 1.6, f"{tid}={r:.4f} 不在 [0.9, 1.6]"

    for tid in ("egypt", "harappa", "babylon", "zhou"):
        assert 1.0 <= ratios[tid] <= 1.5, f"{tid}={ratios[tid]:.4f}"

    assert ratios["greece"] == pytest.approx(0.90, abs=0.02)
    assert ratios["sumer"] == pytest.approx(0.90, abs=0.02)


# 各模板：文档原值核心领土 + 农业修正系数 + 目标开局盈余率
EXPECTED_TEMPLATE_AGRI = {
    "sumer": {"territory_core": 300, "agricultural_modifier": 0.90 / 0.7427800269905533, "food_surplus_ratio": 0.90},
    "egypt": {"territory_core": 600, "agricultural_modifier": 1.0, "food_surplus_ratio": 1.2700674763832658},
    "harappa": {"territory_core": 800, "agricultural_modifier": 1.0, "food_surplus_ratio": 1.3509614035087718},
    "babylon": {"territory_core": 800, "agricultural_modifier": 1.0, "food_surplus_ratio": 1.0769734592892488},
    "zhou": {"territory_core": 1000, "agricultural_modifier": 1.0, "food_surplus_ratio": 1.2},
    "greece": {"territory_core": 400, "agricultural_modifier": 0.90 / 0.6184587394411957, "food_surplus_ratio": 0.90},
}


def test_template_agricultural_modifier_and_surplus_locked() -> None:
    """锁定各模板 territory_core（文档原值）、agricultural_modifier 与开局盈余率。"""
    for tid, expected in EXPECTED_TEMPLATE_AGRI.items():
        state = load_civ_state(tid)
        ratio = calculate_food_surplus_from_state(state)
        assert state.territory_core == expected["territory_core"], tid
        assert state.agricultural_modifier == pytest.approx(
            expected["agricultural_modifier"], abs=1e-9
        ), tid
        assert ratio == pytest.approx(expected["food_surplus_ratio"], abs=0.01), tid
        assert 0.5 <= state.agricultural_modifier <= 2.0, tid
