"""人口动态模型测试（文档 §3.3 标定 + 边界）。"""

from __future__ import annotations

import math

import pytest

from backend.engine.population import apply_population_growth, base_growth_rate


class TestPopulationCalibration:
    def test_famine_max_decline(self) -> None:
        """盈余率=0 → 增长 = -0.02 × (0.8-0)/0.8 = -0.02。"""
        assert base_growth_rate(0.0) == pytest.approx(-0.02)

    def test_famine_mid(self) -> None:
        """盈余率=0.4 → -0.02 × (0.8-0.4)/0.8 = -0.01。"""
        assert base_growth_rate(0.4) == pytest.approx(-0.01)

    def test_barely_below_one(self) -> None:
        """0.8 ≤ ratio < 1.0 → -0.005。"""
        assert base_growth_rate(0.8) == pytest.approx(-0.005)
        assert base_growth_rate(0.99) == pytest.approx(-0.005)

    def test_warm_growth(self) -> None:
        """1.0 ≤ ratio < 1.2 → 0.005。"""
        assert base_growth_rate(1.0) == pytest.approx(0.005)
        assert base_growth_rate(1.19) == pytest.approx(0.005)

    def test_normal_growth(self) -> None:
        """1.2 ≤ ratio < 1.5 → 0.01。"""
        assert base_growth_rate(1.2) == pytest.approx(0.01)
        assert base_growth_rate(1.49) == pytest.approx(0.01)

    def test_fast_growth(self) -> None:
        """ratio ≥ 1.5 → 0.015。"""
        assert base_growth_rate(1.5) == pytest.approx(0.015)
        assert base_growth_rate(2.0) == pytest.approx(0.015)

    def test_apply_one_year_normal(self) -> None:
        """人口 10000，盈余 1.3，1 年 → 增长 1% → 10100。"""
        new_pop = apply_population_growth(10000, 1.3, 1.0)
        assert new_pop == 10100

    def test_apply_multi_year(self) -> None:
        """年化 0.5%，跨度 2 年 → 实际 +1%。"""
        new_pop = apply_population_growth(10000, 1.1, 2.0)
        assert new_pop == 10100

    def test_event_population_change(self) -> None:
        new_pop = apply_population_growth(10000, 1.0, 1.0, event_population_change=-500)
        # 1.0 → growth 0.005 → 10050 - 500 = 9550
        assert new_pop == 9550


class TestPopulationBoundaries:
    def test_population_zero(self) -> None:
        new_pop = apply_population_growth(0, 1.5, 1.0)
        assert new_pop == 0

    def test_negative_years_treated_as_zero(self) -> None:
        new_pop = apply_population_growth(1000, 1.5, -5.0)
        assert new_pop == 1000

    def test_never_negative_population(self) -> None:
        new_pop = apply_population_growth(100, 0.0, 10.0, event_population_change=-10000)
        assert new_pop >= 0
        assert not math.isnan(float(new_pop))

    def test_nan_food_ratio(self) -> None:
        assert base_growth_rate(float("nan")) == 0.0
