"""资源供需结算层（capacity）标定与边界测试。"""

from __future__ import annotations

import pytest

from backend.engine.capacity import (
    CapacityParams,
    compute_action_demand,
    compute_capacity,
    compute_transmission,
    settle_capacity,
    settle_from_state,
)
from backend.models.schemas import (
    AuthoritySource,
    DecisionStructure,
    Legitimacy,
    Polity,
    Succession,
)
from backend.templates.civilizations import load_civ_state


def _polity(decision: DecisionStructure) -> Polity:
    return Polity(
        authority_source=AuthoritySource.BLOODLINE,
        decision_structure=decision,
        succession=Succession.HEREDITARY,
    )


class TestCapacityPool:
    """第一层：国力池不含 authority。"""

    def test_authority_does_not_affect_capacity_layer(self) -> None:
        a = compute_capacity(1.2, 0.3, 0.2)
        b = compute_capacity(1.2, 0.3, 0.2)
        assert a.capacity == pytest.approx(b.capacity)

    def test_higher_food_and_bureau_raise_capacity(self) -> None:
        low = compute_capacity(0.8, 0.1, 0.1)
        high = compute_capacity(1.5, 0.8, 0.8)
        assert high.capacity > low.capacity


class TestTransmission:
    """第二层：开国帝王 vs 末代皇帝。"""

    def test_founding_emperor_higher_transmission_than_late(self) -> None:
        founding = compute_transmission(
            authority=90.0,
            decision_structure=DecisionStructure.AUTOCRACY,
            elite_cohesion=0.9,
            governance_efficiency=0.7,
            legitimacy_total=0.85,
            bureaucratization=0.7,
        )
        late = compute_transmission(
            authority=15.0,
            decision_structure=DecisionStructure.COUNCIL,
            elite_cohesion=0.2,
            governance_efficiency=0.05,
            legitimacy_total=0.2,
            bureaucratization=0.1,
        )
        assert founding.transmission > late.transmission
        assert founding.transmission > 0.7
        assert late.transmission < 0.35


class TestDilutionScenarios:
    """强国多小任务不稀释；弱国单大任务被稀释。"""

    def test_strong_many_small_no_dilution(self) -> None:
        """高国力 + 多个 small → dilution_factor == 1。"""
        state = load_civ_state("zhou")
        # 人为抬高统治力与官僚，模拟强国
        strong = state.model_copy(
            update={
                "authority": 90.0,
                "bureaucratization": 0.8,
                "elite_cohesion": 0.85,
                "class_tension": 0.15,
                "polity": _polity(DecisionStructure.AUTOCRACY),
                "legitimacy": Legitimacy(
                    traditional=0.8,
                    religious=0.7,
                    performance=0.9,
                    legal=0.6,
                ),
            }
        )
        # 四个 small、低认知代差
        actions = [("small", 0.0)] * 4
        settlement = settle_from_state(
            strong,
            actions,
            class_tension=0.15,
            elite_cohesion=0.85,
        )
        assert settlement.total_demand <= settlement.available
        assert settlement.dilution_factor == pytest.approx(1.0)

    def test_weak_single_large_diluted(self) -> None:
        """弱国力 + 单个 large → 被稀释，且不低于 DILUTION_FLOOR。"""
        state = load_civ_state("zhou")
        weak = state.model_copy(
            update={
                "authority": 12.0,
                "bureaucratization": 0.05,
                "elite_cohesion": 0.2,
                "class_tension": 0.7,
                "polity": _polity(DecisionStructure.COUNCIL),
                "legitimacy": Legitimacy(
                    traditional=0.2,
                    religious=0.2,
                    performance=0.1,
                    legal=0.1,
                ),
            }
        )
        settlement = settle_from_state(
            weak,
            [("large", 3.0)],
            class_tension=0.7,
            elite_cohesion=0.2,
        )
        assert settlement.total_demand > settlement.available
        assert settlement.dilution_factor < 1.0
        raw = settlement.base_dilution_ratio**CapacityParams.DILUTION_EXPONENT
        expected = max(raw, CapacityParams.DILUTION_FLOOR)
        assert settlement.dilution_factor == pytest.approx(expected)
        assert settlement.dilution_factor >= CapacityParams.DILUTION_FLOOR

    def test_founding_vs_late_same_demand_different_dilution(self) -> None:
        """同一 large 任务：高 transmission 稀释更轻（或无稀释）。"""
        base = load_civ_state("zhou")
        founding = base.model_copy(
            update={
                "authority": 95.0,
                "bureaucratization": 0.75,
                "elite_cohesion": 0.9,
                "class_tension": 0.2,
                "polity": _polity(DecisionStructure.AUTOCRACY),
                "legitimacy": Legitimacy(
                    traditional=0.85,
                    religious=0.8,
                    performance=0.9,
                    legal=0.7,
                ),
            }
        )
        late = base.model_copy(
            update={
                "authority": 18.0,
                "bureaucratization": 0.08,
                "elite_cohesion": 0.25,
                "class_tension": 0.65,
                "polity": _polity(DecisionStructure.COUNCIL),
                "legitimacy": Legitimacy(
                    traditional=0.25,
                    religious=0.2,
                    performance=0.15,
                    legal=0.1,
                ),
            }
        )
        action = [("large", 2.0)]
        s_founding = settle_from_state(
            founding, action, class_tension=0.2, elite_cohesion=0.9
        )
        s_late = settle_from_state(
            late, action, class_tension=0.65, elite_cohesion=0.25
        )
        assert s_founding.transmission.transmission > s_late.transmission.transmission
        assert s_founding.available > s_late.available
        assert s_founding.dilution_factor >= s_late.dilution_factor


class TestDemandAndSettleMath:
    def test_demand_formula(self) -> None:
        d = compute_action_demand("medium", cognitive_gap=2.0, resistance=0.5)
        assert d.scale_cost == CapacityParams.SCALE_COST["medium"]
        assert d.difficulty == pytest.approx(1.0 + 2.0 * 0.5)
        assert d.demand == pytest.approx(d.scale_cost * d.difficulty)

    def test_no_dilution_when_under_capacity(self) -> None:
        demands = [
            compute_action_demand("small", 0.0, 0.3),
            compute_action_demand("small", 0.0, 0.3),
        ]
        total, ratio, dil = settle_capacity(10.0, demands)
        assert total < 10.0
        assert ratio == pytest.approx(1.0)
        assert dil == pytest.approx(1.0)

    def test_nonlinear_dilution_exponent(self) -> None:
        demands = [compute_action_demand("large", 2.0, 0.5)]
        total, ratio, dil = settle_capacity(5.0, demands)
        assert total > 5.0
        raw = ratio**CapacityParams.DILUTION_EXPONENT
        assert dil == pytest.approx(max(raw, CapacityParams.DILUTION_FLOOR))
        # 未触底时，指数 >1 使稀释严于线性比
        if raw > CapacityParams.DILUTION_FLOOR:
            assert dil < ratio

    def test_dilution_floor_binds_on_severe_overdraw(self) -> None:
        """严重超支时 dilution 封底，不掉到 floor 以下。"""
        demands = [
            compute_action_demand("large", 3.0, 0.5),
            compute_action_demand("large", 3.0, 0.5),
            compute_action_demand("large", 3.0, 0.5),
        ]
        _total, ratio, dil = settle_capacity(5.0, demands)
        raw = ratio**CapacityParams.DILUTION_EXPONENT
        assert raw < CapacityParams.DILUTION_FLOOR
        assert dil == pytest.approx(CapacityParams.DILUTION_FLOOR)


class TestZhouBaseline:
    """西周锚点：单 medium 通常不稀释；三 large 严重稀释但触底。"""

    def test_zhou_one_medium_usually_ok(self) -> None:
        state = load_civ_state("zhou")
        s = settle_from_state(state, [("medium", 1.0)])
        assert s.dilution_factor == pytest.approx(1.0)

    def test_zhou_three_large_heavily_diluted(self) -> None:
        state = load_civ_state("zhou")
        s = settle_from_state(
            state,
            [("large", 2.0), ("large", 2.0), ("large", 2.0)],
        )
        assert s.total_demand > s.available
        assert s.dilution_factor < 1.0
        assert s.dilution_factor >= CapacityParams.DILUTION_FLOOR
        # 西周三 large 应触底
        assert s.dilution_factor == pytest.approx(CapacityParams.DILUTION_FLOOR)
