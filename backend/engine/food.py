"""粮食盈余率计算。

公式：
  arable_land = territory_core × biome_fertility
  food_surplus_ratio = (
      tech_agriculture × arable_land × labor_efficiency
      × YIELD_FACTOR × agricultural_modifier
  ) / population

YIELD_FACTOR 由西周模板反推（agricultural_modifier=1.0）：令开局盈余率 = 1.2。
  西周：pop=80000, core=1000, fert=0.65, tech=1.5,
        labor_eff=0.3×1+0.4×0.85+0.2×0.75+0.1×0.65=0.855
  arable=650
  YIELD_FACTOR = 1.2 × 80000 / (1.5 × 650 × 0.855) ≈ 115.16

agricultural_modifier：模板级农业禀赋，默认 1.0；用于在不改动领土的前提下校准开局盈余。

劳动效率：自由民 1.0 / 徭役 0.85 / 农奴 0.75 / 奴隶 0.65
"""

from __future__ import annotations

import math

from backend.models.schemas import CivState, LaborDistribution

# 劳动形态效率系数（文档 §2.2）
LABOR_EFFICIENCY = {
    "free_citizens": 1.0,
    "corvee": 0.85,
    "serf": 0.75,
    "slave": 0.65,
}

# 西周开局盈余率 = 1.2 反推所得产量缩放常数（西周 agricultural_modifier = 1.0）
YIELD_FACTOR = 1.2 * 80000 / (1.5 * 650 * 0.855)


def labor_efficiency(labor: LaborDistribution) -> float:
    """按劳动形态比例加权平均劳动效率。"""
    return (
        labor.free_citizens * LABOR_EFFICIENCY["free_citizens"]
        + labor.corvee * LABOR_EFFICIENCY["corvee"]
        + labor.serf * LABOR_EFFICIENCY["serf"]
        + labor.slave * LABOR_EFFICIENCY["slave"]
    )


def arable_land(territory_core: float, biome_fertility: float) -> float:
    """耕地面积 = 核心领土 × 生态肥力（肥力只出现一次）。"""
    return max(0.0, territory_core) * max(0.0, min(1.0, biome_fertility))


# 兼容旧名
farmland_area = arable_land


def calculate_food_surplus(
    tech_agriculture: float,
    territory_core: float,
    biome_fertility: float,
    labor: LaborDistribution,
    population: int,
    agricultural_modifier: float = 1.0,
) -> float:
    """计算粮食盈余率。

    人口为 0 时返回 0.0（避免除零）；结果非负。
    """
    if population <= 0:
        return 0.0

    land = arable_land(territory_core, biome_fertility)
    eff = labor_efficiency(labor)
    mod = max(0.0, agricultural_modifier)
    numerator = (
        max(0.0, tech_agriculture) * land * max(0.0, eff) * YIELD_FACTOR * mod
    )
    ratio = numerator / population

    if math.isnan(ratio) or math.isinf(ratio):
        return 0.0
    return max(0.0, ratio)


def calculate_food_surplus_from_state(state: CivState) -> float:
    """从 CivState 计算粮食盈余率。"""
    return calculate_food_surplus(
        tech_agriculture=state.tech_agriculture,
        territory_core=float(state.territory_core),
        biome_fertility=state.biome_fertility,
        labor=state.labor_distribution,
        population=state.population,
        agricultural_modifier=state.agricultural_modifier,
    )
