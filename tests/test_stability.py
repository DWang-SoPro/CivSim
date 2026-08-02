"""稳定性模型测试（文档 §3.4 标定 + 边界）。"""

from __future__ import annotations

import math

import pytest

from backend.engine.stability import apply_stability, compute_stability_delta


class TestStabilityCalibration:
    def test_neutral_baseline(self) -> None:
        """food=1.0, leg=0.5, ct≤0.5, ec≥0.5 → delta=0。"""
        delta = compute_stability_delta(1.0, 0.5, 0.5, 0.5)
        assert delta == pytest.approx(0.0)

    def test_food_component(self) -> None:
        """+5 × (food - 1.0)：food=1.2 → +1.0。"""
        delta = compute_stability_delta(1.2, 0.5, 0.5, 0.5)
        assert delta == pytest.approx(1.0)

    def test_legitimacy_component(self) -> None:
        """+3 × (leg - 0.5)：leg=1.0 → +1.5。"""
        delta = compute_stability_delta(1.0, 1.0, 0.5, 0.5)
        assert delta == pytest.approx(1.5)

    def test_class_tension_penalty(self) -> None:
        """-10 × max(ct-0.5,0)：ct=0.8 → -3.0。"""
        delta = compute_stability_delta(1.0, 0.5, 0.8, 0.5)
        assert delta == pytest.approx(-3.0)

    def test_elite_cohesion_penalty(self) -> None:
        """-5 × max(0.5-ec,0)：ec=0.3 → -1.0。"""
        delta = compute_stability_delta(1.0, 0.5, 0.5, 0.3)
        assert delta == pytest.approx(-1.0)

    def test_combined_document_style(self) -> None:
        """food=0.8, leg=0.4, ct=0.7, ec=0.4
        = 5×(-0.2) + 3×(-0.1) - 10×0.2 - 5×0.1
        = -1.0 - 0.3 - 2.0 - 0.5 = -3.8
        """
        delta = compute_stability_delta(0.8, 0.4, 0.7, 0.4)
        assert delta == pytest.approx(-3.8)

    def test_clamp_range(self) -> None:
        assert apply_stability(90.0, 50.0) == 100.0
        assert apply_stability(10.0, -50.0) == 0.0
        assert apply_stability(50.0, 5.0) == 55.0


class TestStabilityBoundaries:
    def test_extreme_inputs(self) -> None:
        delta = compute_stability_delta(0.0, 0.0, 1.0, 0.0)
        assert not math.isnan(delta)
        result = apply_stability(0.0, delta)
        assert 0.0 <= result <= 100.0

    def test_nan_safety(self) -> None:
        assert apply_stability(50.0, float("nan")) == 50.0
