"""路径积累值测试（文档第六节 标定 + 边界）。"""

from __future__ import annotations

import math

import pytest

from backend.engine.accumulation import (
    accumulation_mod,
    apply_accumulation_turn,
    apply_action_contribution,
    apply_natural_decay,
    success_weight,
)
from backend.models.schemas import Accumulations, ActionResultTier


class TestAccumulationCalibration:
    def test_success_weights(self) -> None:
        """文档权重：大成功 1.5 / 成功 1.0 / 部分 0.5 / 失败 0.1 / 灾难 0.0。"""
        assert success_weight(ActionResultTier.GREAT_SUCCESS) == 1.5
        assert success_weight(ActionResultTier.SUCCESS) == 1.0
        assert success_weight(ActionResultTier.PARTIAL) == 0.5
        assert success_weight(ActionResultTier.FAILURE) == 0.1
        assert success_weight(ActionResultTier.DISASTER) == 0.0

    def test_action_contribution_success(self) -> None:
        """成功行动：+0.2 × 1.0 = +0.2。"""
        acc = Accumulations(administrative=1.0)
        result = apply_action_contribution(acc, "political", ActionResultTier.SUCCESS)
        assert result.administrative == pytest.approx(1.2)

    def test_action_contribution_great_success(self) -> None:
        """大成功：+0.2 × 1.5 = +0.3。"""
        acc = Accumulations(military=0.0)
        result = apply_action_contribution(acc, "military", ActionResultTier.GREAT_SUCCESS)
        assert result.military == pytest.approx(0.3)

    def test_natural_decay_rate(self) -> None:
        """每轮 ×0.95。"""
        acc = Accumulations(academic=1.0, military=2.0)
        result = apply_natural_decay(acc)
        assert result.academic == pytest.approx(0.95)
        assert result.military == pytest.approx(1.9)

    def test_academy_partial_offset(self) -> None:
        """academic：先 ×0.95 再 ×1.03 → 1.0 × 0.95 × 1.03 = 0.9785。"""
        acc = Accumulations(academic=1.0)
        result = apply_natural_decay(acc, has_academy=True)
        assert result.academic == pytest.approx(0.95 * 1.03)

    def test_admin_bureau_offset(self) -> None:
        """administrative + bureau>0.5：×0.95 ×1.02。"""
        acc = Accumulations(administrative=1.0)
        result = apply_natural_decay(acc, bureaucratization=0.6)
        assert result.administrative == pytest.approx(0.95 * 1.02)

    def test_full_turn_political_success(self) -> None:
        """贡献 +0.2 后衰减 ×0.95 → (1.0+0.2)×0.95 = 1.14。"""
        acc = Accumulations(administrative=1.0)
        result = apply_accumulation_turn(
            acc,
            action_domain="political",
            tier=ActionResultTier.SUCCESS,
        )
        assert result.administrative == pytest.approx(1.14)

    def test_accumulation_mod_formula(self) -> None:
        """1.0 + relevant × 0.3，最高 1.3。"""
        assert accumulation_mod(0.0) == pytest.approx(1.0)
        assert accumulation_mod(1.0) == pytest.approx(1.3)
        assert accumulation_mod(2.0) == pytest.approx(1.3)  # 封顶
        assert accumulation_mod(0.5) == pytest.approx(1.15)


class TestAccumulationBoundaries:
    def test_zero_start(self) -> None:
        acc = Accumulations()
        result = apply_accumulation_turn(acc)
        for field in ("academic", "military", "commercial", "administrative", "cultural"):
            val = getattr(result, field)
            assert val >= 0.0
            assert not math.isnan(val)

    def test_disaster_no_gain_then_decay(self) -> None:
        acc = Accumulations(military=1.0)
        result = apply_accumulation_turn(
            acc, action_domain="military", tier=ActionResultTier.DISASTER
        )
        assert result.military == pytest.approx(0.95)

    def test_unknown_domain_no_crash(self) -> None:
        acc = Accumulations(academic=1.0)
        result = apply_action_contribution(acc, "unknown_domain", ActionResultTier.SUCCESS)
        assert result.academic == pytest.approx(1.0)
