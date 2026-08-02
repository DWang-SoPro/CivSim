"""资源供需结算层：三层国力调动模型。

第一层 — 国力池 capacity（不含 authority，避免与第二层双重计算）
第二层 — 权力传导系数 transmission ∈ [0, 1]
第三层 — 资源需求 → 与可调动量比较 → dilution_factor

dilution_factor 只作用于数值效果，不作用于成功率。
所有可调参数集中在 CapacityParams。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence

from backend.engine.food import calculate_food_surplus_from_state
from backend.engine.friction import compute_resistance
from backend.engine.governance import governance_efficiency_from_state
from backend.models.schemas import CivState, DecisionStructure


class ActionScale(str, Enum):
    """与意图解析 scale 对齐的规模枚举。"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class CapacityParams:
    """国力调动可调参数（联调拧这里即可）。"""

    # ---- 第一层：国力池 ----
    BASE_CAPACITY: float = 50.0
    # capacity = BASE × food_factor × bureau_factor × gov_factor
    FOOD_FACTOR_MIN: float = 0.3
    FOOD_FACTOR_MAX: float = 2.0
    BUREAU_FACTOR_FLOOR: float = 0.4  # bureau_factor = FLOOR + (1-FLOOR)*bureau
    GOV_FACTOR_FLOOR: float = 0.4  # gov_factor = FLOOR + (1-FLOOR)*governance

    # ---- 第二层：权力传导权重（归一化前；结算时按和归一）----
    W_AUTHORITY: float = 0.30
    W_POWER_CONCENTRATION: float = 0.25
    W_ELITE_COHESION: float = 0.15
    W_GOVERNANCE: float = 0.15
    W_LEGITIMACY: float = 0.15

    # 决策结构 → 权力集中度锚点
    POWER_CONC_AUTOCRACY: float = 0.95
    POWER_CONC_COUNCIL: float = 0.35
    # bureaucracy: FLOOR + SPAN * bureaucratization
    POWER_CONC_BUREAU_FLOOR: float = 0.55
    POWER_CONC_BUREAU_SPAN: float = 0.40
    # oligarchy: FLOOR + SPAN * elite_cohesion
    POWER_CONC_OLIGARCHY_FLOOR: float = 0.40
    POWER_CONC_OLIGARCHY_SPAN: float = 0.50

    # ---- 第三层：资源需求 ----
    SCALE_COST: dict[str, float] = {
        "small": 1.0,
        "medium": 3.0,
        "large": 8.0,
    }
    # dilution_factor = max((available / total_demand) ^ DILUTION_EXPONENT, DILUTION_FLOOR)
    # 封底：严重超支时仍保留「办成半拉子」的可见痕迹，避免效果几乎归零
    DILUTION_EXPONENT: float = 1.5
    DILUTION_FLOOR: float = 0.28


@dataclass(frozen=True)
class CapacityBreakdown:
    """国力池中间量（供调试打印）。"""

    food_surplus_ratio: float
    food_factor: float
    bureau_factor: float
    gov_factor: float
    capacity: float


@dataclass(frozen=True)
class TransmissionBreakdown:
    """权力传导中间量（供调试打印）。"""

    authority_norm: float
    power_concentration: float
    elite_cohesion: float
    governance: float
    legitimacy: float
    transmission: float


@dataclass(frozen=True)
class DemandItem:
    """单个行动的资源需求。"""

    scale: str
    cognitive_gap: float
    resistance: float
    difficulty: float
    scale_cost: float
    demand: float


@dataclass(frozen=True)
class CapacitySettlement:
    """完整供需结算结果。"""

    capacity: CapacityBreakdown
    transmission: TransmissionBreakdown
    available: float
    demands: tuple[DemandItem, ...]
    total_demand: float
    base_dilution_ratio: float
    dilution_factor: float  # 作用于全部行动的统一稀释系数


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_power_concentration(
    decision_structure: DecisionStructure,
    bureaucratization: float,
    elite_cohesion: float,
    *,
    params: type[CapacityParams] = CapacityParams,
) -> float:
    """由决策结构推导权力集中度 ∈ [0, 1]。"""
    if decision_structure == DecisionStructure.AUTOCRACY:
        return params.POWER_CONC_AUTOCRACY
    if decision_structure == DecisionStructure.COUNCIL:
        return params.POWER_CONC_COUNCIL
    if decision_structure == DecisionStructure.BUREAUCRACY:
        return _clamp(
            params.POWER_CONC_BUREAU_FLOOR
            + params.POWER_CONC_BUREAU_SPAN * _clamp(bureaucratization, 0.0, 1.0),
            0.0,
            1.0,
        )
    # oligarchy：看精英凝聚力
    return _clamp(
        params.POWER_CONC_OLIGARCHY_FLOOR
        + params.POWER_CONC_OLIGARCHY_SPAN * _clamp(elite_cohesion, 0.0, 1.0),
        0.0,
        1.0,
    )


def compute_capacity(
    food_surplus_ratio: float,
    bureaucratization: float,
    governance_efficiency: float,
    *,
    params: type[CapacityParams] = CapacityParams,
) -> CapacityBreakdown:
    """第一层：国力池。authority 不参与。"""
    food_factor = _clamp(
        food_surplus_ratio, params.FOOD_FACTOR_MIN, params.FOOD_FACTOR_MAX
    )
    bureau_factor = params.BUREAU_FACTOR_FLOOR + (
        1.0 - params.BUREAU_FACTOR_FLOOR
    ) * _clamp(bureaucratization, 0.0, 1.0)
    gov_factor = params.GOV_FACTOR_FLOOR + (
        1.0 - params.GOV_FACTOR_FLOOR
    ) * _clamp(governance_efficiency, 0.0, 1.0)
    capacity = params.BASE_CAPACITY * food_factor * bureau_factor * gov_factor
    return CapacityBreakdown(
        food_surplus_ratio=food_surplus_ratio,
        food_factor=food_factor,
        bureau_factor=bureau_factor,
        gov_factor=gov_factor,
        capacity=capacity,
    )


def compute_transmission(
    authority: float,
    decision_structure: DecisionStructure,
    elite_cohesion: float,
    governance_efficiency: float,
    legitimacy_total: float,
    bureaucratization: float,
    *,
    params: type[CapacityParams] = CapacityParams,
) -> TransmissionBreakdown:
    """第二层：权力传导系数 ∈ [0, 1]。"""
    authority_norm = _clamp(authority / 100.0, 0.0, 1.0)
    power_conc = compute_power_concentration(
        decision_structure,
        bureaucratization,
        elite_cohesion,
        params=params,
    )
    elite = _clamp(elite_cohesion, 0.0, 1.0)
    gov = _clamp(governance_efficiency, 0.0, 1.0)
    legit = _clamp(legitimacy_total, 0.0, 1.0)

    weights = (
        params.W_AUTHORITY,
        params.W_POWER_CONCENTRATION,
        params.W_ELITE_COHESION,
        params.W_GOVERNANCE,
        params.W_LEGITIMACY,
    )
    values = (authority_norm, power_conc, elite, gov, legit)
    w_sum = sum(weights) or 1.0
    transmission = sum(w * v for w, v in zip(weights, values)) / w_sum
    transmission = _clamp(transmission, 0.0, 1.0)

    return TransmissionBreakdown(
        authority_norm=authority_norm,
        power_concentration=power_conc,
        elite_cohesion=elite,
        governance=gov,
        legitimacy=legit,
        transmission=transmission,
    )


def compute_action_demand(
    scale: str | ActionScale,
    cognitive_gap: float,
    resistance: float,
    *,
    params: type[CapacityParams] = CapacityParams,
) -> DemandItem:
    """第三层：单个行动资源需求 = 规模基数 × 难度系数。"""
    scale_key = scale.value if isinstance(scale, ActionScale) else str(scale)
    scale_cost = params.SCALE_COST.get(scale_key, params.SCALE_COST["medium"])
    difficulty = 1.0 + max(0.0, cognitive_gap) * max(0.0, resistance)
    demand = scale_cost * difficulty
    return DemandItem(
        scale=scale_key,
        cognitive_gap=float(cognitive_gap),
        resistance=float(resistance),
        difficulty=difficulty,
        scale_cost=scale_cost,
        demand=demand,
    )


def settle_capacity(
    available: float,
    demands: Sequence[DemandItem],
    *,
    params: type[CapacityParams] = CapacityParams,
) -> tuple[float, float, float]:
    """根据可调动量与总需求计算稀释。

    Returns:
        (total_demand, base_dilution_ratio, dilution_factor)
    """
    total = sum(d.demand for d in demands)
    if total <= 0.0:
        return 0.0, 1.0, 1.0
    if total <= available:
        return total, 1.0, 1.0
    base_ratio = available / total
    dilution = max(base_ratio**params.DILUTION_EXPONENT, params.DILUTION_FLOOR)
    return total, base_ratio, dilution


def settle_from_state(
    state: CivState,
    actions: Iterable[tuple[str | ActionScale, float]],
    *,
    class_tension: Optional[float] = None,
    elite_cohesion: Optional[float] = None,
    religious_resistance: float = 0.0,
    params: type[CapacityParams] = CapacityParams,
) -> CapacitySettlement:
    """从 CivState + [(scale, cognitive_gap), ...] 完成三层结算。"""
    # 默认与 action_resolver 估算对齐；调用方可传入已估算值
    ct = class_tension if class_tension is not None else (state.class_tension or 0.3)
    ec = elite_cohesion if elite_cohesion is not None else (state.elite_cohesion or 0.5)
    food = calculate_food_surplus_from_state(state)
    gov = governance_efficiency_from_state(state)

    cap = compute_capacity(
        food_surplus_ratio=food,
        bureaucratization=state.bureaucratization,
        governance_efficiency=gov,
        params=params,
    )
    trans = compute_transmission(
        authority=state.authority,
        decision_structure=state.polity.decision_structure,
        elite_cohesion=ec,
        governance_efficiency=gov,
        legitimacy_total=state.legitimacy_total(),
        bureaucratization=state.bureaucratization,
        params=params,
    )
    available = cap.capacity * trans.transmission

    resistance = compute_resistance(
        state.bureaucratization, ct, ec, religious_resistance
    )
    demand_items = tuple(
        compute_action_demand(scale, gap, resistance, params=params)
        for scale, gap in actions
    )
    total, base_ratio, dilution = settle_capacity(
        available, demand_items, params=params
    )

    return CapacitySettlement(
        capacity=cap,
        transmission=trans,
        available=available,
        demands=demand_items,
        total_demand=total,
        base_dilution_ratio=base_ratio,
        dilution_factor=dilution,
    )
