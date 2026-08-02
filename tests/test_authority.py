"""统治力模型测试（文档 §3.5 标定 + 边界）。"""

from __future__ import annotations

import math

import pytest

from backend.engine.authority import apply_authority, compute_authority_delta


class TestAuthorityCalibration:
    def test_neutral_baseline(self) -> None:
        """ec=0.5, ct≤0.6, bureau≥0.2, action=0 → delta=0。"""
        delta = compute_authority_delta(0.5, 0.6, 0.2)
        assert delta == pytest.approx(0.0)

    def test_elite_cohesion_bonus(self) -> None:
        """+3 × (ec - 0.5)：ec=0.8 → +0.9。"""
        delta = compute_authority_delta(0.8, 0.5, 0.5)
        assert delta == pytest.approx(0.9)

    def test_class_tension_penalty(self) -> None:
        """-5 × max(ct-0.6,0)：ct=0.8 → -1.0。"""
        delta = compute_authority_delta(0.5, 0.8, 0.5)
        assert delta == pytest.approx(-1.0)

    def test_low_bureaucratization_penalty(self) -> None:
        """bureaucratization < 0.2 → -2。"""
        delta = compute_authority_delta(0.5, 0.5, 0.19)
        assert delta == pytest.approx(-2.0)
        # 边界：恰好 0.2 不惩罚
        delta2 = compute_authority_delta(0.5, 0.5, 0.2)
        assert delta2 == pytest.approx(0.0)

    def test_action_delta(self) -> None:
        delta = compute_authority_delta(0.5, 0.5, 0.5, action_authority_delta=5.0)
        assert delta == pytest.approx(5.0)

    def test_combined(self) -> None:
        """ec=0.3, ct=0.7, bureau=0.1, action=+2
        = 2 + 3×(-0.2) - 5×0.1 - 2
        = 2 - 0.6 - 0.5 - 2 = -1.1
        """
        delta = compute_authority_delta(0.3, 0.7, 0.1, action_authority_delta=2.0)
        assert delta == pytest.approx(-1.1)

    def test_clamp(self) -> None:
        assert apply_authority(95.0, 20.0) == 100.0
        assert apply_authority(5.0, -20.0) == 0.0


class TestAuthorityBoundaries:
    def test_authority_zero_input(self) -> None:
        delta = compute_authority_delta(0.0, 1.0, 0.0)
        result = apply_authority(0.0, delta)
        assert 0.0 <= result <= 100.0
        assert not math.isnan(result)

    def test_nan_safety(self) -> None:
        assert apply_authority(40.0, float("nan")) == 40.0
