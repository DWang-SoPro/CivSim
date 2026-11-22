"""被动历史事件引擎：天灾、疫病、边患、兼并、藩镇与丰年。

设计原则：
1. 纯函数 + 显式随机源（固定种子可完整复现同一局史书）。
2. 前两回合为开国缓冲期（turn_after <= 2 不刷随机灾难，保证新手立国与单回合单测锚点稳定）。
3. 官仓储粮（grain_reserve）、武备底蕴（acc_military）、官僚化与知识水平真实参与抗灾折冲，
   让「修建粮仓」「操练士卒」「修筑城池」「设立学宫」拥有明确的战略避险价值。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Optional

from backend.engine.food import calculate_food_surplus_from_state
from backend.models.schemas import CivState


@dataclass(frozen=True)
class PassiveEventOutcome:
    """本回合触发的被动事件及其对状态的修正。"""

    id: str
    title: str
    summary: str
    mitigated: bool
    state_after: CivState


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def resolve_passive_event(
    state: CivState,
    turn_years: float,
    rng: Optional[random.Random] = None,
) -> Optional[PassiveEventOutcome]:
    """在回合行动结算后判定是否发生被动历史事件（每回合至多一件主事件）。"""
    # 前两回合不触发随机事件，给开局政策留出因果窗口，并保持首回合单测锚点
    if state.turn < 3:
        return None

    r = rng if rng is not None else random.Random(state.turn * 7919 + state.population)
    year_scale = _clamp(turn_years / 2.0, 0.6, 1.8)
    food = calculate_food_surplus_from_state(state)
    tension = state.class_tension if state.class_tension is not None else 0.35
    cohesion = state.elite_cohesion if state.elite_cohesion is not None else 0.50

    # 构建候选事件权重池：(event_id, weight)
    candidates: list[tuple[str, float]] = []

    # 1) 旱涝灾荒：生态肥力偏低或耕作尚浅时更易发生
    climate_risk = 0.11 * year_scale * (1.25 - 0.35 * state.biome_fertility)
    candidates.append(("natural_calamity", max(0.04, climate_risk)))

    # 2) 疫疠流行：人口稠密而知识/医药尚浅时概率上升
    if state.population >= 45000:
        plague_risk = 0.05 * year_scale * _clamp(state.population / 75000.0, 0.7, 1.6)
        if state.tech_knowledge >= 1.8:
            plague_risk *= 0.55
        candidates.append(("epidemic", plague_risk))

    # 3) 边鄙告警：边疆辽阔而武备不足时易遭侵扰
    if state.territory_frontier >= 250:
        raid_risk = 0.07 * year_scale * _clamp(state.territory_frontier / 600.0, 0.6, 1.7)
        if state.accumulations.military >= 0.6:
            raid_risk *= 0.65
        candidates.append(("frontier_raid", raid_risk))

    # 4) 豪强兼并：阶级矛盾抬头且官僚约束弱
    if tension >= 0.44 and state.bureaucratization < 0.50:
        candidates.append(("land_annexation", 0.08 * year_scale))

    # 5) 宗室/诸侯掣肘：精英离心或强枝弱干
    if cohesion < 0.45 or (
        state.territory_frontier >= state.territory_core and state.bureaucratization < 0.36
    ):
        candidates.append(("elite_friction", 0.07 * year_scale))

    # 6) 岁稔商通：政通人和且粮产充裕时的正向景气
    if state.stability >= 65.0 and food >= 1.03:
        candidates.append(("abundant_harvest", 0.09 * year_scale))

    total_prob = sum(w for _, w in candidates)
    roll = r.random()
    if roll >= min(total_prob, 0.42):
        return None

    # 在命中区间内按相对权重抽取具体事件
    cursor = 0.0
    scaled_roll = (roll / min(total_prob, 0.42)) * total_prob
    chosen = candidates[-1][0]
    for event_id, weight in candidates:
        cursor += weight
        if scaled_roll <= cursor:
            chosen = event_id
            break

    if chosen == "natural_calamity":
        kind = "连月亢旱" if r.random() < 0.55 else "秋水决堤"
        if state.grain_reserve >= 0.14:
            next_state = state.model_copy(
                update={
                    "grain_reserve": round(max(0.0, state.grain_reserve - 0.12), 4),
                    "stability": _clamp(state.stability + 0.8, 0.0, 100.0),
                    "legitimacy": state.legitimacy.model_copy(
                        update={
                            "performance": _clamp(
                                state.legitimacy.performance + 0.02, 0.0, 1.0
                            )
                        }
                    ),
                }
            )
            return PassiveEventOutcome(
                id="natural_calamity",
                title=f"{kind}（官仓平粜）",
                summary=f"境内突发{kind}，幸赖常平官仓及时发粟平粜，流民得安，未成大饥",
                mitigated=True,
                state_after=next_state,
            )
        pop_loss = max(120, int(round(state.population * 0.024)))
        next_state = state.model_copy(
            update={
                "grain_reserve": 0.0,
                "population": max(0, state.population - pop_loss),
                "stability": _clamp(state.stability - 4.5, 0.0, 100.0),
                "class_tension": _clamp(tension + 0.045, 0.0, 1.0),
            }
        )
        return PassiveEventOutcome(
            id="natural_calamity",
            title=f"{kind}成灾",
            summary=f"境内遭遇{kind}，因官仓积谷不足，乡邑乏食、流亡渐起",
            mitigated=False,
            state_after=next_state,
        )

    if chosen == "epidemic":
        if state.tech_knowledge >= 1.6 and state.bureaucratization >= 0.35:
            pop_loss = max(60, int(round(state.population * 0.008)))
            next_state = state.model_copy(
                update={
                    "population": max(0, state.population - pop_loss),
                    "stability": _clamp(state.stability - 1.2, 0.0, 100.0),
                }
            )
            return PassiveEventOutcome(
                id="epidemic",
                title="时疫受控",
                summary="都邑春夏之交偶发时疫，有司依律隔离诊治、疏浚沟渠，疫情旋即平息",
                mitigated=True,
                state_after=next_state,
            )
        pop_loss = max(150, int(round(state.population * 0.022)))
        next_state = state.model_copy(
            update={
                "population": max(0, state.population - pop_loss),
                "stability": _clamp(state.stability - 3.5, 0.0, 100.0),
                "authority": _clamp(state.authority - 1.5, 0.0, 100.0),
            }
        )
        return PassiveEventOutcome(
            id="epidemic",
            title="时疫流布",
            summary="聚落间时疫蔓延，闾里萧条，农作与征发一时受阻",
            mitigated=False,
            state_after=next_state,
        )

    if chosen == "frontier_raid":
        if state.accumulations.military >= 0.42 and state.authority >= 35.0:
            next_state = state.model_copy(
                update={
                    "authority": _clamp(state.authority + 1.8, 0.0, 100.0),
                    "legitimacy": state.legitimacy.model_copy(
                        update={
                            "performance": _clamp(
                                state.legitimacy.performance + 0.03, 0.0, 1.0
                            )
                        }
                    ),
                }
            )
            return PassiveEventOutcome(
                id="frontier_raid",
                title="边塞告捷",
                summary="外族轻骑叩边，戍卒素有操练，据险击退来敌，边鄙晏然",
                mitigated=True,
                state_after=next_state,
            )
        lost_land = min(state.territory_frontier, max(20, int(round(state.territory_frontier * 0.06))))
        next_state = state.model_copy(
            update={
                "territory_frontier": max(0, state.territory_frontier - lost_land),
                "stability": _clamp(state.stability - 3.2, 0.0, 100.0),
                "authority": _clamp(state.authority - 2.2, 0.0, 100.0),
            }
        )
        return PassiveEventOutcome(
            id="frontier_raid",
            title="边鄙告警",
            summary="边防空虚，外族乘隙掠边，部分边地失联，朝野震动",
            mitigated=False,
            state_after=next_state,
        )

    if chosen == "land_annexation":
        next_state = state.model_copy(
            update={
                "class_tension": _clamp(tension + 0.04, 0.0, 1.0),
                "authority": _clamp(state.authority - 1.8, 0.0, 100.0),
                "stability": _clamp(state.stability - 1.5, 0.0, 100.0),
            }
        )
        return PassiveEventOutcome(
            id="land_annexation",
            title="豪强兼并",
            summary="地方大姓乘隙兼并田亩、隐匿丁口，公田赋役渐见吃紧",
            mitigated=False,
            state_after=next_state,
        )

    if chosen == "elite_friction":
        next_state = state.model_copy(
            update={
                "elite_cohesion": _clamp(cohesion - 0.04, 0.0, 1.0),
                "authority": _clamp(state.authority - 2.0, 0.0, 100.0),
            }
        )
        return PassiveEventOutcome(
            id="elite_friction",
            title="贵戚掣肘",
            summary="朝中旧族与地方实力派各怀异议，政令下行多有推诿",
            mitigated=False,
            state_after=next_state,
        )

    # abundant_harvest
    pop_gain = max(80, int(round(state.population * 0.01)))
    next_state = state.model_copy(
        update={
            "population": state.population + pop_gain,
            "grain_reserve": round(_clamp(state.grain_reserve + 0.09, 0.0, 2.0), 4),
            "stability": _clamp(state.stability + 2.0, 0.0, 100.0),
        }
    )
    return PassiveEventOutcome(
        id="abundant_harvest",
        title="岁稔商通",
        summary="风调雨顺，田畴大熟，四方行旅络绎入市，官私仓廪皆有赢余",
        mitigated=True,
        state_after=next_state,
    )


def check_passive_events(
    state: CivState,
    turn_years: float,
    rng: Optional[random.Random] = None,
) -> list[dict[str, Any]]:
    """兼容旧接口：返回本回合触发的被动事件摘要字典列表。"""
    outcome = resolve_passive_event(state, turn_years, rng=rng)
    if outcome is None:
        return []
    return [
        {
            "id": outcome.id,
            "title": outcome.title,
            "summary": outcome.summary,
            "mitigated": outcome.mitigated,
        }
    ]
