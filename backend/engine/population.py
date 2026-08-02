"""人口动态模型（设计文档 §3.3）。

增长率由粮食盈余率决定（年化），再按本回合时间跨度折算。
"""

from __future__ import annotations

import math


def base_growth_rate(food_surplus_ratio: float) -> float:
    """根据粮食盈余率返回年化基础人口增长率。

    文档标定：
      < 0.8  → -0.02 × (0.8 - ratio) / 0.8  （饥荒，最多 -2%）
      < 1.0  → -0.005
      < 1.2  →  0.005
      < 1.5  →  0.01
      else   →  0.015
    """
    ratio = food_surplus_ratio
    if math.isnan(ratio) or math.isinf(ratio):
        return 0.0
    if ratio < 0.8:
        return -0.02 * (0.8 - ratio) / 0.8
    if ratio < 1.0:
        return -0.005
    if ratio < 1.2:
        return 0.005
    if ratio < 1.5:
        return 0.01
    return 0.015


def apply_population_growth(
    population: int,
    food_surplus_ratio: float,
    turn_years: float,
    event_population_change: int = 0,
) -> int:
    """结算一回合后的人口。

    population_new = population × (1 + base_growth × turn_years) + event_change
    结果钳制为非负整数。
    """
    if population < 0:
        population = 0
    if turn_years < 0:
        turn_years = 0.0

    growth = base_growth_rate(food_surplus_ratio)
    actual_growth = growth * turn_years
    new_pop = population * (1.0 + actual_growth) + event_population_change

    if math.isnan(new_pop) or math.isinf(new_pop):
        return max(0, population + event_population_change)
    return max(0, int(round(new_pop)))
