"""数学引擎包：纯函数模块，输入状态 → 输出数值变化，无副作用。"""

from backend.engine.accumulation import apply_accumulation_turn, success_weight
from backend.engine.authority import compute_authority_delta, apply_authority
from backend.engine.food import calculate_food_surplus, labor_efficiency
from backend.engine.friction import (
    compute_p_success,
    compute_resistance,
    roll_result_tier,
)
from backend.engine.governance import governance_efficiency
from backend.engine.population import apply_population_growth, base_growth_rate
from backend.engine.stability import compute_stability_delta, apply_stability

__all__ = [
    "apply_accumulation_turn",
    "apply_authority",
    "apply_population_growth",
    "apply_stability",
    "base_growth_rate",
    "calculate_food_surplus",
    "compute_authority_delta",
    "compute_p_success",
    "compute_resistance",
    "compute_stability_delta",
    "governance_efficiency",
    "labor_efficiency",
    "roll_result_tier",
    "success_weight",
]
