"""社会摩擦模型测试（文档 §3.1 标定 + 边界）。"""

from __future__ import annotations

import math
import random

import pytest

from backend.engine.friction import (
    compute_a_norm,
    compute_p_base,
    compute_p_success,
    compute_resistance,
    effect_multiplier,
    result_probabilities,
    roll_result_tier,
)
from backend.models.schemas import ActionResultTier, DecisionStructure


class TestFrictionCalibration:
    """文档公式的具体数值断言。"""

    def test_a_norm_floor(self) -> None:
        """A_norm = max(统治力/20, 0.5)：统治力=0 → 0.5；统治力=20 → 1.0。"""
        assert compute_a_norm(0.0) == pytest.approx(0.5)
        assert compute_a_norm(10.0) == pytest.approx(0.5)
        assert compute_a_norm(20.0) == pytest.approx(1.0)
        assert compute_a_norm(40.0) == pytest.approx(2.0)

    def test_resistance_components(self) -> None:
        """resistance = 0.3×(1-b) + 0.3×ct + 0.2×(1-ec) + 0.2×rr。"""
        # b=1, ct=0, ec=1, rr=0 → resistance = 0
        assert compute_resistance(1.0, 0.0, 1.0, 0.0) == pytest.approx(0.0)
        # b=0, ct=1, ec=0, rr=1 → 0.3+0.3+0.2+0.2 = 1.0
        assert compute_resistance(0.0, 1.0, 0.0, 1.0) == pytest.approx(1.0)
        # b=0.5, ct=0.5, ec=0.5, rr=0 → 0.3*0.5 + 0.3*0.5 + 0.2*0.5 + 0 = 0.4
        assert compute_resistance(0.5, 0.5, 0.5, 0.0) == pytest.approx(0.4)

    def test_p_base_zero_gap(self) -> None:
        """cognitive_gap=0 → P_base = 0.8。"""
        assert compute_p_base(0.0, 1.0, 50.0) == pytest.approx(0.8)

    def test_p_base_formula_example(self) -> None:
        """已知输入：gap=1, resistance=0.4, authority=20 → A_norm=1
        P_base = 0.8 × (1 - 1×0.4/1) = 0.8 × 0.6 = 0.48。
        """
        assert compute_p_base(1.0, 0.4, 20.0) == pytest.approx(0.48)

    def test_p_success_autocracy_baseline(self) -> None:
        """gap=0, 理想结构, random=1 → P_success = 0.8 × 1.0 × 1.0 × 1.0 × 1.0 = 0.8。"""
        p = compute_p_success(
            cognitive_gap=0.0,
            bureaucratization=1.0,
            class_tension=0.0,
            elite_cohesion=1.0,
            authority=50.0,
            decision_structure=DecisionStructure.AUTOCRACY,
            infrastructure_mod=1.0,
            accumulation_mod=1.0,
            random_factor=1.0,
        )
        assert p == pytest.approx(0.8)

    def test_p_success_council_mod(self) -> None:
        """council → authority_mod=0.8：0.8 × 0.8 = 0.64。"""
        p = compute_p_success(
            cognitive_gap=0.0,
            bureaucratization=1.0,
            class_tension=0.0,
            elite_cohesion=1.0,
            authority=50.0,
            decision_structure=DecisionStructure.COUNCIL,
            random_factor=1.0,
        )
        assert p == pytest.approx(0.64)

    def test_accumulation_mod_cap(self) -> None:
        """accumulation_mod 最高 +30% → 1.3；乘积 0.8×1.3=1.04 钳制到 1.0。"""
        p = compute_p_success(
            cognitive_gap=0.0,
            bureaucratization=1.0,
            class_tension=0.0,
            elite_cohesion=1.0,
            authority=50.0,
            decision_structure=DecisionStructure.AUTOCRACY,
            accumulation_mod=1.3,
            random_factor=1.0,
        )
        assert p == pytest.approx(1.0)

        # 较低基线时 +30% 可完整体现：P_base=0.8、council=0.8 → 0.64×1.3=0.832
        p2 = compute_p_success(
            cognitive_gap=0.0,
            bureaucratization=1.0,
            class_tension=0.0,
            elite_cohesion=1.0,
            authority=50.0,
            decision_structure=DecisionStructure.COUNCIL,
            accumulation_mod=1.3,
            random_factor=1.0,
        )
        assert p2 == pytest.approx(0.64 * 1.3)

    def test_result_table_high_success(self) -> None:
        """P≥0.8 → (20%, 50%, 25%, 5%, 0%)。"""
        probs = result_probabilities(0.85)
        assert probs[ActionResultTier.GREAT_SUCCESS] == pytest.approx(0.20)
        assert probs[ActionResultTier.SUCCESS] == pytest.approx(0.50)
        assert probs[ActionResultTier.PARTIAL] == pytest.approx(0.25)
        assert probs[ActionResultTier.FAILURE] == pytest.approx(0.05)
        assert probs[ActionResultTier.DISASTER] == pytest.approx(0.00)

    def test_result_table_mid(self) -> None:
        """0.4 ≤ P < 0.6 → (5%, 20%, 35%, 30%, 10%)。"""
        probs = result_probabilities(0.5)
        assert probs[ActionResultTier.GREAT_SUCCESS] == pytest.approx(0.05)
        assert probs[ActionResultTier.SUCCESS] == pytest.approx(0.20)
        assert probs[ActionResultTier.PARTIAL] == pytest.approx(0.35)
        assert probs[ActionResultTier.FAILURE] == pytest.approx(0.30)
        assert probs[ActionResultTier.DISASTER] == pytest.approx(0.10)

    def test_result_table_very_low(self) -> None:
        """P < 0.2 → (0%, 5%, 15%, 40%, 40%)。"""
        probs = result_probabilities(0.1)
        assert probs[ActionResultTier.GREAT_SUCCESS] == pytest.approx(0.00)
        assert probs[ActionResultTier.SUCCESS] == pytest.approx(0.05)
        assert probs[ActionResultTier.PARTIAL] == pytest.approx(0.15)
        assert probs[ActionResultTier.FAILURE] == pytest.approx(0.40)
        assert probs[ActionResultTier.DISASTER] == pytest.approx(0.40)

    def test_effect_multipliers(self) -> None:
        """大成功 150%、成功 100%、部分 50%、失败 0%。"""
        assert effect_multiplier(ActionResultTier.GREAT_SUCCESS) == 1.5
        assert effect_multiplier(ActionResultTier.SUCCESS) == 1.0
        assert effect_multiplier(ActionResultTier.PARTIAL) == 0.5
        assert effect_multiplier(ActionResultTier.FAILURE) == 0.0


class TestFrictionBoundaries:
    def test_authority_zero(self) -> None:
        """统治力=0：A_norm 下限 0.5，不崩溃。"""
        p = compute_p_success(
            cognitive_gap=5.0,
            bureaucratization=0.0,
            class_tension=1.0,
            elite_cohesion=0.0,
            authority=0.0,
            decision_structure=DecisionStructure.AUTOCRACY,
            random_factor=1.0,
        )
        assert not math.isnan(p)
        assert 0.0 <= p <= 1.0

    def test_raw_p_base_can_go_negative_but_output_clamped(self) -> None:
        """极端代差可使字面 P_base 为负，但 P_success 输出钳制到 [0,1]。"""
        raw = compute_p_base(5.0, 1.0, 0.0)  # 0.8*(1-5/0.5)=0.8*(-9)=-7.2
        assert raw < 0
        p = compute_p_success(
            cognitive_gap=5.0,
            bureaucratization=0.0,
            class_tension=1.0,
            elite_cohesion=0.0,
            authority=0.0,
            decision_structure=DecisionStructure.AUTOCRACY,
            random_factor=1.0,
        )
        assert p == 0.0

    def test_prerequisites_not_met(self) -> None:
        p = compute_p_success(
            cognitive_gap=0.0,
            bureaucratization=1.0,
            class_tension=0.0,
            elite_cohesion=1.0,
            authority=50.0,
            decision_structure=DecisionStructure.AUTOCRACY,
            prerequisites_met=False,
        )
        assert p == 0.0

    def test_roll_deterministic(self) -> None:
        tier = roll_result_tier(0.9, rng=random.Random(42))
        assert isinstance(tier, ActionResultTier)
