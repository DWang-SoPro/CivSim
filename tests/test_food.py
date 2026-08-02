"""粮食盈余率测试（修正公式 + 西周校准 + 边界）。"""

from __future__ import annotations

import math

import pytest

from backend.engine.food import (
    LABOR_EFFICIENCY,
    YIELD_FACTOR,
    arable_land,
    calculate_food_surplus,
    calculate_food_surplus_from_state,
    labor_efficiency,
)
from backend.models.schemas import LaborDistribution
from backend.templates.civilizations import load_civ_state


def _labor(
    free: float = 1.0,
    corvee: float = 0.0,
    serf: float = 0.0,
    slave: float = 0.0,
) -> LaborDistribution:
    return LaborDistribution(
        free_citizens=free, corvee=corvee, serf=serf, slave=slave
    )


class TestFoodCalibration:
    def test_labor_efficiency_coefficients(self) -> None:
        """文档劳动效率：自由民 1.0 / 徭役 0.85 / 农奴 0.75 / 奴隶 0.65。"""
        assert LABOR_EFFICIENCY["free_citizens"] == 1.0
        assert LABOR_EFFICIENCY["corvee"] == 0.85
        assert LABOR_EFFICIENCY["serf"] == 0.75
        assert LABOR_EFFICIENCY["slave"] == 0.65

    def test_pure_free_citizens_efficiency(self) -> None:
        assert labor_efficiency(_labor(1.0, 0, 0, 0)) == pytest.approx(1.0)

    def test_pure_slave_efficiency(self) -> None:
        assert labor_efficiency(_labor(0, 0, 0, 1.0)) == pytest.approx(0.65)

    def test_weighted_labor_efficiency(self) -> None:
        """埃及劳动分布：0.3×1 + 0.5×0.85 + 0.1×0.75 + 0.1×0.65 = 0.865。"""
        labor = _labor(0.3, 0.5, 0.1, 0.1)
        assert labor_efficiency(labor) == pytest.approx(0.865)

    def test_zhou_labor_efficiency(self) -> None:
        """西周劳动效率 = 0.855（校准 YIELD_FACTOR 用）。"""
        labor = _labor(0.3, 0.4, 0.2, 0.1)
        assert labor_efficiency(labor) == pytest.approx(0.855)

    def test_arable_land_fertility_once(self) -> None:
        """耕地面积 = 核心领土 × 生态肥力（肥力只进入这一次）。"""
        assert arable_land(600, 0.85) == pytest.approx(510.0)
        assert arable_land(1000, 0.65) == pytest.approx(650.0)

    def test_yield_factor_from_zhou_target(self) -> None:
        """YIELD_FACTOR = 1.2 × 80000 / (1.5 × 650 × 0.855)。"""
        expected = 1.2 * 80000 / (1.5 * 650 * 0.855)
        assert YIELD_FACTOR == pytest.approx(expected)
        assert YIELD_FACTOR == pytest.approx(115.15969410706253, abs=1e-6)

    def test_food_surplus_literal_formula(self) -> None:
        """tech=1, core=100, fert=1, free, pop=100, mod=1
        arable=100; ratio = (1×100×1×YF×1)/100 = YF
        """
        ratio = calculate_food_surplus(1.0, 100, 1.0, _labor(1, 0, 0, 0), 100)
        assert ratio == pytest.approx(YIELD_FACTOR)

    def test_food_surplus_fertility_not_squared(self) -> None:
        """肥力只出现一次：tech=1, core=100, fert=0.5, free, pop=100, mod=1
        arable=50; ratio = (1×50×1×YF×1)/100 = 0.5×YF
        （旧公式会再乘一次 fert 得到 0.25×YF）
        """
        ratio = calculate_food_surplus(1.0, 100, 0.5, _labor(1, 0, 0, 0), 100)
        assert ratio == pytest.approx(0.5 * YIELD_FACTOR)

    def test_agricultural_modifier_scales_surplus(self) -> None:
        """agricultural_modifier 线性缩放盈余率。"""
        base = calculate_food_surplus(1.0, 100, 1.0, _labor(1, 0, 0, 0), 100, 1.0)
        scaled = calculate_food_surplus(1.0, 100, 1.0, _labor(1, 0, 0, 0), 100, 1.5)
        assert scaled == pytest.approx(base * 1.5)

    def test_zhou_opening_surplus_is_1_2(self) -> None:
        """西周开局盈余率校准目标 ≈ 1.2（agricultural_modifier = 1.0）。"""
        state = load_civ_state("zhou")
        assert state.agricultural_modifier == pytest.approx(1.0)
        assert calculate_food_surplus_from_state(state) == pytest.approx(1.2, abs=0.01)


class TestFoodBoundaries:
    def test_population_zero(self) -> None:
        ratio = calculate_food_surplus(1.0, 100, 1.0, _labor(), 0)
        assert ratio == 0.0
        assert not math.isnan(ratio)

    def test_zero_territory(self) -> None:
        ratio = calculate_food_surplus(1.0, 0, 1.0, _labor(), 1000)
        assert ratio == 0.0

    def test_zero_tech(self) -> None:
        ratio = calculate_food_surplus(0.0, 100, 1.0, _labor(), 100)
        assert ratio == 0.0

    def test_never_negative(self) -> None:
        ratio = calculate_food_surplus(-1.0, -10, -0.5, _labor(), 100)
        assert ratio >= 0.0
        assert not math.isnan(ratio)
