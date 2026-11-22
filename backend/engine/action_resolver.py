"""行动结果总结算。

第一阶段：`resolve_turn` + FakeActionInput（纯数学、无 LLM，供 pytest）。
第二阶段：`resolve_full_turn` 串联 TaskSplitter → IntentParser → capacity →
friction → 数值汇总 → 叙事输入组装（可选生成叙事）。
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.engine.accumulation import apply_accumulation_turn
from backend.engine.authority import apply_authority, compute_authority_delta
from backend.engine.capacity import (
    CapacityParams,
    CapacitySettlement,
    settle_from_state,
)
from backend.engine.food import calculate_food_surplus_from_state
from backend.engine.friction import (
    compute_p_success_from_state,
    compute_resistance,
    effect_multiplier,
    roll_result_tier,
)
from backend.engine.governance import governance_efficiency_from_state
from backend.engine.passive_events import resolve_passive_event
from backend.engine.population import apply_population_growth
from backend.engine.stability import apply_stability, compute_stability_delta
from backend.llm.intent_parser import ActionScale, IntentResult, parse_intent
from backend.llm.narrator import Importance, NarrationInput, ResultTier, narrate
from backend.llm.task_splitter import TaskSplitResult, split_tasks
from backend.models.schemas import (
    ActionResultTier,
    CivState,
    DecisionStructure,
    LandSystem,
    SurplusExtraction,
)

# 成功档 + medium 规模下的域级兜底变动（供自由政令使用；28 项标准政令优先走 _ACTION_EFFECTS）
_SCALE_EFFECT: dict[str, float] = {
    "small": 0.5,
    "medium": 1.0,
    "large": 2.0,
}

_BASE_EFFECTS: dict[str, dict[str, float]] = {
    "economic": {
        "stability": 2.5,
        "authority": 1.2,
        "population_pct": 0.012,
        "tech_agriculture": 0.05,
        "grain_reserve": 0.04,
        "class_tension": 0.01,
    },
    "military": {
        "stability": -1.0,
        "authority": 3.8,
        "population_pct": -0.018,
        "grain_reserve": -0.04,
        "class_tension": 0.025,
    },
    "political": {
        "stability": 2.0,
        "authority": 4.5,
        "bureaucratization": 0.025,
        "class_tension": -0.005,
        "elite_cohesion": 0.015,
    },
    "cultural": {
        "stability": 3.0,
        "authority": 1.2,
        "tech_knowledge": 0.07,
        "knowledge_institution_coverage": 0.03,
        "elite_cohesion": 0.02,
        "class_tension": -0.015,
    },
    "technology": {
        "stability": 1.0,
        "authority": 1.5,
        "tech_engineering": 0.09,
        "tech_agriculture": 0.03,
    },
    "composite": {
        "stability": 3.2,
        "authority": 2.2,
        "class_tension": -0.025,
    },
}

# 28 项标准政令的差异化效果（medium + success 基准），让每项政令名实相副
_ACTION_EFFECTS: dict[str, dict[str, float]] = {
    # ---- 经济 ----
    "开垦荒地": {
        "territory_core": 28.0,
        "population_pct": 0.012,
        "tech_agriculture": 0.03,
        "stability": 1.8,
        "authority": 1.0,
    },
    "兴修水利": {
        "agricultural_modifier": 0.025,
        "tech_agriculture": 0.06,
        "tech_engineering": 0.02,
        "stability": 2.6,
        "authority": 1.4,
        "population_pct": 0.012,
    },
    "修建粮仓": {
        "grain_reserve": 0.16,
        "stability": 2.2,
        "authority": 1.2,
        "tech_engineering": 0.03,
    },
    "开设市集": {
        "stability": 2.0,
        "authority": 1.2,
        "tech_knowledge": 0.04,
        "grain_reserve": 0.04,
        "population_pct": 0.01,
        "class_tension": 0.01,
    },
    "调整贡赋": {
        "authority": 3.2,
        "grain_reserve": 0.10,
        "bureaucratization": 0.02,
        "class_tension": 0.028,
        "stability": -0.8,
    },
    "铸造货币": {
        "bureaucratization": 0.03,
        "authority": 3.0,
        "tech_engineering": 0.05,
        "stability": 1.5,
        "legitimacy_legal": 0.04,
    },
    # ---- 政治 ----
    "任命官吏": {
        "bureaucratization": 0.035,
        "authority": 3.5,
        "elite_cohesion": 0.02,
        "stability": 1.8,
    },
    "编纂律令": {
        "legitimacy_legal": 0.07,
        "bureaucratization": 0.025,
        "stability": 2.6,
        "authority": 3.0,
        "class_tension": -0.02,
    },
    "分封诸侯": {
        "elite_cohesion": 0.06,
        "legitimacy_traditional": 0.05,
        "stability": 3.0,
        "territory_frontier": 45.0,
        "bureaucratization": -0.02,
    },
    "推行郡县": {
        "bureaucratization": 0.06,
        "authority": 6.0,
        "legitimacy_legal": 0.06,
        "frontier_to_core": 80.0,
        "elite_cohesion": -0.045,
        "stability": 1.0,
    },
    "整肃权贵": {
        "authority": 6.5,
        "class_tension": -0.05,
        "bureaucratization": 0.03,
        "grain_reserve": 0.06,
        "elite_cohesion": -0.065,
    },
    # ---- 军事 ----
    "操练士卒": {
        "authority": 2.6,
        "elite_cohesion": 0.02,
        "stability": 0.8,
        "grain_reserve": -0.02,
    },
    "修筑城池": {
        "stability": 2.6,
        "authority": 2.0,
        "tech_engineering": 0.06,
        "grain_reserve": -0.03,
        "class_tension": 0.015,
    },
    "铸造兵器": {
        "tech_engineering": 0.07,
        "authority": 2.8,
        "grain_reserve": -0.02,
        "class_tension": 0.015,
    },
    "建立常备军": {
        "authority": 5.0,
        "legitimacy_performance": 0.04,
        "grain_reserve": -0.06,
        "population_pct": -0.01,
        "class_tension": 0.02,
    },
    "征伐边疆": {
        "territory_frontier": 110.0,
        "territory_core": 25.0,
        "legitimacy_performance": 0.07,
        "authority": 4.8,
        "population_pct": -0.022,
        "grain_reserve": -0.08,
        "stability": -1.2,
        "class_tension": 0.028,
    },
    "镇压叛乱": {
        "stability": 5.8,
        "authority": 4.2,
        "class_tension": -0.035,
        "population_pct": -0.015,
        "grain_reserve": -0.04,
    },
    # ---- 文化 ----
    "设立学宫": {
        "knowledge_institution_coverage": 0.06,
        "tech_knowledge": 0.08,
        "bureaucratization": 0.015,
        "stability": 2.0,
    },
    "举行大祭": {
        "legitimacy_religious": 0.06,
        "legitimacy_traditional": 0.04,
        "elite_cohesion": 0.04,
        "stability": 3.2,
        "class_tension": -0.02,
        "grain_reserve": -0.02,
    },
    "宣扬天命": {
        "legitimacy_religious": 0.07,
        "authority": 3.0,
        "stability": 2.5,
        "class_tension": -0.015,
    },
    "修建宗庙": {
        "legitimacy_traditional": 0.07,
        "elite_cohesion": 0.05,
        "stability": 2.6,
        "authority": 1.8,
        "grain_reserve": -0.03,
    },
    "编纂典籍": {
        "tech_knowledge": 0.10,
        "knowledge_institution_coverage": 0.05,
        "legitimacy_traditional": 0.04,
        "legitimacy_legal": 0.04,
        "stability": 1.8,
    },
    # ---- 科技 ----
    "改进农具": {
        "tech_agriculture": 0.10,
        "tech_engineering": 0.03,
        "stability": 1.6,
        "population_pct": 0.008,
    },
    "钻研营造": {
        "tech_engineering": 0.12,
        "stability": 1.2,
        "authority": 1.5,
    },
    "延揽学者": {
        "tech_knowledge": 0.11,
        "knowledge_institution_coverage": 0.04,
        "bureaucratization": 0.02,
        "stability": 1.2,
    },
    "引进异域技艺": {
        "tech_engineering": 0.12,
        "tech_agriculture": 0.08,
        "tech_knowledge": 0.10,
        "stability": 1.0,
    },
    # ---- 综合 ----
    "巡狩四方": {
        "authority": 3.5,
        "stability": 3.0,
        "elite_cohesion": 0.03,
        "class_tension": -0.025,
        "frontier_to_core": 25.0,
    },
    "赈济饥民": {
        "stability": 5.5,
        "class_tension": -0.07,
        "legitimacy_performance": 0.05,
        "population_pct": 0.008,
        "grain_reserve": -0.08,
    },
}

# 判定「大幅变化」的 importance 阈值
_MAJOR_STABILITY = 8.0
_MAJOR_AUTHORITY = 8.0
_MAJOR_POP_PCT = 0.05


@dataclass(frozen=True)
class FakeActionInput:
    """假想行动输入（测试与第一阶段联调用）。"""

    domain: str = "political"
    cognitive_gap: float = 1.0
    turn_years: float = 1.0
    tier: Optional[ActionResultTier] = ActionResultTier.SUCCESS
    action_stability_delta: float = 2.0
    action_authority_delta: float = 1.0
    religious_resistance: float = 0.0
    prerequisites_met: bool = True
    random_factor: float = 1.0
    event_population_change: int = 0
    has_academy: bool = False


@dataclass(frozen=True)
class ResolveResult:
    """一回合数值结算结果（第一阶段）。"""

    state_after: CivState
    food_surplus_ratio: float
    governance_efficiency: float
    p_success: float
    result_tier: ActionResultTier
    effect_mult: float
    stability_delta: float
    authority_delta: float


@dataclass
class SubtaskResolution:
    """单个子任务的中间产物。"""

    subtask_id: str
    description: str
    intent: IntentResult
    skipped_vague: bool = False
    is_unexecutable: bool = False
    demand: float = 0.0
    dilution_factor: float = 1.0
    resistance: float = 0.0
    p_success: float = 0.0
    result_tier: Optional[ActionResultTier] = None
    effect_mult: float = 0.0
    base_deltas: dict[str, float] = field(default_factory=dict)
    diluted_deltas: dict[str, float] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)


@dataclass
class FullTurnResult:
    """完整回合结果（供叙事与状态更新）。"""

    player_input: str
    split: TaskSplitResult
    intents: list[IntentResult]
    vague_prompts: list[str]
    settlement_skipped: bool
    capacity: Optional[CapacitySettlement]
    subtasks: list[SubtaskResolution]
    aggregated_deltas: dict[str, float]
    dimension_changes: dict[str, str]
    events: list[str]
    overall_tier: Optional[ActionResultTier]
    importance: Importance
    turn_years: float
    state_before: CivState
    state_after: Optional[CivState]
    narration_input: Optional[NarrationInput]
    narrative: Optional[str]
    rng_seed: int


def estimate_class_tension(state: CivState) -> float:
    """阶级矛盾粗估（文档 §2.5 简化实现，供引擎串联）。"""
    if state.class_tension is not None:
        return state.class_tension
    labor = state.labor_distribution
    oppression = labor.serf * 0.3 + labor.slave * 0.5
    land_inequality = {
        "noble_estate": 0.7,
        "landlord_tenant": 0.8,
        "state_grant": 0.4,
        "clan_communal": 0.2,
        "yeoman_smallhold": 0.3,
    }.get(state.land_system.value, 0.4)
    extraction_pressure = 0.3
    raw = 0.3 * oppression + 0.3 * land_inequality + 0.2 * extraction_pressure
    return max(0.0, min(1.0, raw))


def estimate_elite_cohesion(state: CivState) -> float:
    """精英凝聚力：有显式值则用，否则给温和默认。"""
    if state.elite_cohesion is not None:
        return state.elite_cohesion
    return 0.5


def resolve_turn(state: CivState, action: FakeActionInput) -> ResolveResult:
    """串联全部数学引擎，返回更新后状态。纯计算，无 I/O。"""
    class_tension = estimate_class_tension(state)
    elite_cohesion = estimate_elite_cohesion(state)

    food = calculate_food_surplus_from_state(state)
    gov = governance_efficiency_from_state(state)

    infra = 1.0 if action.prerequisites_met else 0.0
    relevant_acc = getattr(state.accumulations, "administrative", 0.0)
    if action.domain == "military":
        relevant_acc = state.accumulations.military
    elif action.domain in ("technology", "cultural"):
        relevant_acc = state.accumulations.academic
    elif action.domain == "economic":
        relevant_acc = state.accumulations.commercial

    p_success = compute_p_success_from_state(
        state,
        cognitive_gap=action.cognitive_gap,
        infrastructure_mod=infra,
        relevant_accumulation=relevant_acc,
        religious_resistance=action.religious_resistance,
        random_factor=action.random_factor,
        prerequisites_met=action.prerequisites_met,
        class_tension=class_tension,
        elite_cohesion=elite_cohesion,
    )

    if action.tier is not None:
        tier = action.tier
    else:
        tier = roll_result_tier(p_success)
    mult = effect_multiplier(tier)

    new_pop = apply_population_growth(
        state.population,
        food,
        action.turn_years,
        event_population_change=action.event_population_change,
    )

    stab_delta = compute_stability_delta(
        food_surplus_ratio=food,
        legitimacy_total=state.legitimacy_total(),
        class_tension=class_tension,
        elite_cohesion=elite_cohesion,
        action_stability_delta=action.action_stability_delta * max(mult, 0.0),
    )
    new_stability = apply_stability(state.stability, stab_delta)

    auth_delta = compute_authority_delta(
        elite_cohesion=elite_cohesion,
        class_tension=class_tension,
        bureaucratization=state.bureaucratization,
        action_authority_delta=action.action_authority_delta * max(mult, 0.0),
    )
    new_authority = apply_authority(state.authority, auth_delta)

    new_acc = apply_accumulation_turn(
        state.accumulations,
        action_domain=action.domain,
        tier=tier,
        has_academy=action.has_academy,
        bureaucratization=state.bureaucratization,
    )

    state_after = state.model_copy(
        update={
            "population": new_pop,
            "stability": new_stability,
            "authority": new_authority,
            "accumulations": new_acc,
            "class_tension": class_tension,
            "elite_cohesion": elite_cohesion,
            "turn": state.turn + 1,
            "year": state.year + action.turn_years,
        }
    )

    return ResolveResult(
        state_after=state_after,
        food_surplus_ratio=food,
        governance_efficiency=gov,
        p_success=p_success,
        result_tier=tier,
        effect_mult=mult,
        stability_delta=stab_delta,
        authority_delta=auth_delta,
    )


# ---------------------------------------------------------------------------
# 第二阶段：全链路
# ---------------------------------------------------------------------------


def _relevant_accumulation(state: CivState, domain: str) -> float:
    if domain == "military":
        return state.accumulations.military
    if domain in ("technology", "cultural"):
        return state.accumulations.academic
    if domain == "economic":
        return state.accumulations.commercial
    return state.accumulations.administrative


def _is_unexecutable(intent: IntentResult) -> bool:
    """极度超前且前置不满足 → 命令下达但实质无事发生。"""
    return (not intent.prerequisites.met) and intent.cognitive_gap >= 5


def _base_deltas_for_intent(intent: IntentResult) -> dict[str, float]:
    """优先使用 28 项标准政令差异化效果；自由政令退回域基础变动，再乘规模系数。"""
    action_name = intent.action_type.strip()
    if action_name in _ACTION_EFFECTS:
        base = dict(_ACTION_EFFECTS[action_name])
    else:
        domain = intent.action_domain.value
        base = dict(_BASE_EFFECTS.get(domain, _BASE_EFFECTS["composite"]))
    scale_m = _SCALE_EFFECT.get(intent.scale.value, 1.0)
    return {k: v * scale_m for k, v in base.items()}


def _apply_tier_and_dilution(
    base: dict[str, float],
    tier: ActionResultTier,
    dilution: float,
) -> dict[str, float]:
    """区分收益项与代价项的档位缩放，彻底杜绝灾难档将军事损耗/矛盾代价反号变奖励。"""
    mult = effect_multiplier(tier)
    if mult == 0.0:
        return {k: 0.0 for k in base}

    out: dict[str, float] = {}
    for k, v in base.items():
        # class_tension 越低越好（v < 0 为缓和收益，v > 0 为施政摩擦代价）
        is_benefit = (v < 0.0) if k == "class_tension" else (v > 0.0)
        if tier == ActionResultTier.DISASTER:
            if is_benefit:
                # 原本期盼的收益反噬为 65% 的反向挫折
                out[k] = -0.65 * v * dilution
            else:
                # 原本付出的代价（如军征损耗、阶级紧绷）在惨败时加剧 1.5 倍，绝不反号变奖励
                out[k] = 1.5 * v * dilution
        else:
            if is_benefit:
                out[k] = v * mult * dilution
            else:
                # 正常成功/部分成功/大成功时，固有代价按不高于 1.0 的比例发生（大成功损耗略轻）
                cost_mult = 0.75 if tier == ActionResultTier.GREAT_SUCCESS else 1.0
                out[k] = v * cost_mult * dilution
    return out


def _format_dimension_changes(
    deltas: dict[str, float],
    state_before: CivState,
    state_after: CivState,
) -> dict[str, str]:
    """把数值变动格式化为叙事用的方向标签（不报精确引擎内部浮点时可近似）。"""
    labels: dict[str, str] = {}
    pop_pct = (state_after.population - state_before.population) / max(
        state_before.population, 1
    )
    if abs(pop_pct) >= 0.005:
        sign = "+" if pop_pct > 0 else ""
        labels["population"] = f"{sign}{pop_pct * 100:.1f}%"

    stab = state_after.stability - state_before.stability
    if abs(stab) >= 0.5:
        labels["stability"] = f"{stab:+.0f}"

    auth = state_after.authority - state_before.authority
    if abs(auth) >= 0.5:
        labels["authority"] = f"{auth:+.0f}"

    for key, label in (
        ("class_tension", "class_tension"),
        ("elite_cohesion", "elite_cohesion"),
        ("bureaucratization", "bureaucratization"),
        ("tech_agriculture", "tech_agriculture"),
        ("tech_engineering", "tech_engineering"),
        ("tech_knowledge", "tech_knowledge"),
    ):
        d = deltas.get(key, 0.0)
        if abs(d) < 1e-6:
            continue
        if abs(d) < 0.02:
            labels[label] = "+小幅" if d > 0 else "-小幅"
        elif abs(d) < 0.05:
            labels[label] = "+中幅" if d > 0 else "-中幅"
        else:
            labels[label] = "+大幅" if d > 0 else "-大幅"

    food_hint = deltas.get("population_pct", 0.0)
    if food_hint > 0.005 and "food" not in labels:
        labels["food"] = "+小幅" if food_hint < 0.02 else "+中幅"
    elif food_hint < -0.005:
        labels["food"] = "-小幅" if food_hint > -0.02 else "-中幅"

    return labels


def _pick_overall_tier(tiers: list[ActionResultTier]) -> ActionResultTier:
    """多任务总档位：取最差与最好的折中偏重最差叙事张力。"""
    if not tiers:
        return ActionResultTier.FAILURE
    order = [
        ActionResultTier.DISASTER,
        ActionResultTier.FAILURE,
        ActionResultTier.PARTIAL,
        ActionResultTier.SUCCESS,
        ActionResultTier.GREAT_SUCCESS,
    ]
    # 若有灾难优先灾难；否则取众数偏严：取最低档
    if ActionResultTier.DISASTER in tiers:
        return ActionResultTier.DISASTER
    return min(tiers, key=lambda t: order.index(t))


def judge_importance(
    intents: list[IntentResult],
    tiers: list[ActionResultTier],
    aggregated: dict[str, float],
    pop_pct: float,
) -> Importance:
    """importance：大幅变化 / 制度向 large / disaster|great_success → major。"""
    if any(i.scale == ActionScale.LARGE for i in intents):
        return Importance.MAJOR
    if any(
        t in (ActionResultTier.DISASTER, ActionResultTier.GREAT_SUCCESS) for t in tiers
    ):
        return Importance.MAJOR
    if abs(aggregated.get("stability", 0.0)) >= _MAJOR_STABILITY:
        return Importance.MAJOR
    if abs(aggregated.get("authority", 0.0)) >= _MAJOR_AUTHORITY:
        return Importance.MAJOR
    if abs(pop_pct) >= _MAJOR_POP_PCT:
        return Importance.MAJOR
    institutional_keywords = ("变法", "迁都", "土地", "田制", "改制", "革命")
    for intent in intents:
        text = intent.action_type + intent.action_description
        if any(k in text for k in institutional_keywords):
            return Importance.MAJOR
    return Importance.NORMAL


def _collect_events(sub: SubtaskResolution) -> list[str]:
    events: list[str] = []
    intent = sub.intent
    if sub.is_unexecutable:
        reason = intent.prerequisites.details or intent.time_estimate_reasoning
        events.append(f"朝野对「{intent.action_type}」茫然无措")
        if reason:
            events.append(reason)
        return events

    tier = sub.result_tier
    if tier in (ActionResultTier.FAILURE, ActionResultTier.DISASTER):
        for src in intent.resistance_sources[:2]:
            events.append(f"{src}阻挠政令")
        if not intent.prerequisites.met and intent.prerequisites.nearest_alternative:
            events.append(
                f"前置未备，或可退而求其次：{intent.prerequisites.nearest_alternative}"
            )
    elif tier in (ActionResultTier.SUCCESS, ActionResultTier.GREAT_SUCCESS):
        for b in intent.beneficiaries[:2]:
            events.append(f"{b}从中得利")
    elif tier == ActionResultTier.PARTIAL:
        if intent.resistance_sources:
            events.append(f"推行中遭遇{intent.resistance_sources[0]}的阻力")
        if intent.beneficiaries:
            events.append(f"{intent.beneficiaries[0]}略有反应")
    return events


def _evolve_institutions(
    state: CivState,
    settled_subs: list[SubtaskResolution],
) -> tuple[CivState, list[str]]:
    """根据成功施行的制度/经济/技术政令渐进演化田制、赋税、劳动结构与政体。"""
    notes: list[str] = []
    land = state.land_system
    labor = state.labor_distribution
    extractions = list(state.surplus_extraction)
    polity = state.polity

    succeeded_names = {
        sub.intent.action_type.strip()
        for sub in settled_subs
        if not sub.skipped_vague
        and not sub.is_unexecutable
        and sub.result_tier in (ActionResultTier.SUCCESS, ActionResultTier.GREAT_SUCCESS)
    }

    # 1) 推行郡县：推动氏族公田/贵族庄园向国有授田演进；官僚成熟时决策结构迈入官僚体制
    if "推行郡县" in succeeded_names:
        if land in (LandSystem.CLAN_COMMUNAL, LandSystem.NOBLE_ESTATE) and state.bureaucratization >= 0.36:
            land = LandSystem.STATE_GRANT
            notes.append("郡县守令清丈田亩，国有授田渐代旧日世袭采邑")
        if (
            state.bureaucratization >= 0.52
            and polity.decision_structure != DecisionStructure.BUREAUCRACY
        ):
            polity = polity.model_copy(
                update={"decision_structure": DecisionStructure.BUREAUCRACY}
            )
            notes.append("百官考课成制，朝廷中枢由旧贵族合议转向官僚体制")

    # 2) 分封诸侯：氏族公有可向贵族庄园过渡
    if "分封诸侯" in succeeded_names and land == LandSystem.CLAN_COMMUNAL:
        land = LandSystem.NOBLE_ESTATE
        notes.append("诸侯就国设邑，贵族采邑庄园渐成主导田制")

    # 3) 赋税体系随商业与官僚积累自然解锁
    if (
        "开设市集" in succeeded_names
        and SurplusExtraction.COMMERCIAL_TAX not in extractions
        and (state.bureaucratization >= 0.30 or state.accumulations.commercial >= 0.40)
    ):
        extractions.append(SurplusExtraction.COMMERCIAL_TAX)
        notes.append("关市之征立下章程，商税正式纳入国用")

    if (
        "铸造货币" in succeeded_names
        and SurplusExtraction.TAX_MONETARY not in extractions
        and (state.bureaucratization >= 0.40 or state.accumulations.commercial >= 0.50)
    ):
        extractions.append(SurplusExtraction.TAX_MONETARY)
        notes.append("新铸泉布通行州郡，赋役始许折钱输纳")

    if (
        "调整贡赋" in succeeded_names
        and SurplusExtraction.TAX_IN_KIND not in extractions
        and state.bureaucratization >= 0.20
    ):
        extractions.append(SurplusExtraction.TAX_IN_KIND)
        notes.append("朝廷核定亩产，实物田租渐补诸侯贡赋之不足")

    # 4) 改进农具：农耕技术提高后，依附劳力（奴隶/农奴）逐步向自耕/徭役自由民转化
    if "改进农具" in succeeded_names and state.tech_agriculture >= 1.7:
        shift = min(0.03, labor.slave + labor.serf)
        if shift >= 0.005:
            from_slave = min(labor.slave, shift * 0.6)
            from_serf = min(labor.serf, shift - from_slave)
            actual = from_slave + from_serf
            new_free = _clamp01(labor.free_citizens + actual)
            new_slave = max(0.0, labor.slave - from_slave)
            new_serf = max(0.0, labor.serf - from_serf)
            new_corvee = max(0.0, 1.0 - new_free - new_slave - new_serf)
            total = new_free + new_corvee + new_serf + new_slave
            labor = labor.model_copy(
                update={
                    "free_citizens": round(new_free / total, 6),
                    "corvee": round(new_corvee / total, 6),
                    "serf": round(new_serf / total, 6),
                    "slave": round(1.0 - round(new_free / total, 6) - round(new_corvee / total, 6) - round(new_serf / total, 6), 6),
                }
            )
            notes.append("新式农具普及乡野，个体耕作渐兴，编户自由民比重上升")

    updated = state.model_copy(
        update={
            "land_system": land,
            "labor_distribution": labor,
            "surplus_extraction": extractions,
            "polity": polity,
        }
    )
    return updated, notes


def _apply_aggregated_to_state(
    state: CivState,
    aggregated: dict[str, float],
    turn_years: float,
    settled_subs: list[SubtaskResolution],
    class_tension: float,
    elite_cohesion: float,
) -> tuple[CivState, dict[str, float], list[str]]:
    """把行动数值汇总后接入各引擎，返回新状态、最终 delta 与结构演进记事。"""
    food = calculate_food_surplus_from_state(state)

    action_stab = aggregated.get("stability", 0.0)
    action_auth = aggregated.get("authority", 0.0)
    pop_pct = aggregated.get("population_pct", 0.0)
    event_pop = int(round(state.population * pop_pct))

    new_pop = apply_population_growth(
        state.population,
        food,
        turn_years,
        event_population_change=event_pop,
    )

    ct = _clamp01(class_tension + aggregated.get("class_tension", 0.0))
    ec = _clamp01(elite_cohesion + aggregated.get("elite_cohesion", 0.0))

    leg = state.legitimacy.model_copy(
        update={
            "traditional": _clamp01(
                state.legitimacy.traditional + aggregated.get("legitimacy_traditional", 0.0)
            ),
            "religious": _clamp01(
                state.legitimacy.religious + aggregated.get("legitimacy_religious", 0.0)
            ),
            "performance": _clamp01(
                state.legitimacy.performance + aggregated.get("legitimacy_performance", 0.0)
            ),
            "legal": _clamp01(
                state.legitimacy.legal + aggregated.get("legitimacy_legal", 0.0)
            ),
        }
    )
    leg_total = (leg.traditional + leg.religious + leg.performance + leg.legal) / 4.0

    stab_delta = compute_stability_delta(
        food_surplus_ratio=food,
        legitimacy_total=leg_total,
        class_tension=ct,
        elite_cohesion=ec,
        action_stability_delta=action_stab,
    )
    new_stability = apply_stability(state.stability, stab_delta)

    auth_delta = compute_authority_delta(
        elite_cohesion=ec,
        class_tension=ct,
        bureaucratization=state.bureaucratization,
        action_authority_delta=action_auth,
    )
    new_authority = apply_authority(state.authority, auth_delta)

    bureau = _clamp01(
        state.bureaucratization + aggregated.get("bureaucratization", 0.0)
    )
    tech_agri = max(0.0, state.tech_agriculture + aggregated.get("tech_agriculture", 0.0))
    tech_eng = max(0.0, state.tech_engineering + aggregated.get("tech_engineering", 0.0))
    tech_know = max(0.0, state.tech_knowledge + aggregated.get("tech_knowledge", 0.0))

    # 领土与边疆内附（如开垦荒地、征伐边疆、推行郡县、巡狩四方）
    core = max(50, int(round(state.territory_core + aggregated.get("territory_core", 0.0))))
    frontier = max(0, int(round(state.territory_frontier + aggregated.get("territory_frontier", 0.0))))
    convert = aggregated.get("frontier_to_core", 0.0)
    if convert > 0 and frontier > 0:
        moved = min(frontier, int(round(convert)))
        core += moved
        frontier -= moved
    elif convert < 0 and core > 100:
        lost_core = min(core - 100, int(round(abs(convert))))
        core -= lost_core
        frontier += lost_core

    agri_mod = max(
        0.5,
        min(2.0, state.agricultural_modifier + aggregated.get("agricultural_modifier", 0.0)),
    )
    # 粮仓上限随工程与官僚水平增长；日常余粮亦微量自然入仓或贴补亏空
    max_reserve = min(2.0, 0.55 + 0.35 * tech_eng + 0.4 * bureau)
    natural_reserve_drift = (food - 1.0) * 0.04 * min(turn_years, 3.0)
    grain_reserve = max(
        0.0,
        min(
            max_reserve,
            state.grain_reserve + aggregated.get("grain_reserve", 0.0) + natural_reserve_drift,
        ),
    )
    know_cov = _clamp01(
        state.knowledge_institution_coverage
        + aggregated.get("knowledge_institution_coverage", 0.0)
    )

    # 积累：逐子任务应用（同回合依次叠；已设学宫时学术积累加快）
    has_academy = know_cov >= 0.58 or any(
        sub.intent.action_type.strip() == "设立学宫" for sub in settled_subs
    )
    new_acc = state.accumulations
    for sub in settled_subs:
        if sub.skipped_vague or sub.result_tier is None:
            continue
        new_acc = apply_accumulation_turn(
            new_acc,
            action_domain=sub.intent.action_domain.value,
            tier=sub.result_tier,
            has_academy=has_academy,
            bureaucratization=bureau,
        )

    state_after = state.model_copy(
        update={
            "population": new_pop,
            "stability": new_stability,
            "authority": new_authority,
            "bureaucratization": bureau,
            "legitimacy": leg,
            "territory_core": core,
            "territory_frontier": frontier,
            "agricultural_modifier": round(agri_mod, 6),
            "grain_reserve": round(grain_reserve, 4),
            "knowledge_institution_coverage": know_cov,
            "tech_agriculture": tech_agri,
            "tech_engineering": tech_eng,
            "tech_knowledge": tech_know,
            "accumulations": new_acc,
            "class_tension": ct,
            "elite_cohesion": ec,
            "turn": state.turn + 1,
            "year": state.year + turn_years,
        }
    )
    state_after, evolution_notes = _evolve_institutions(state_after, settled_subs)

    final_deltas = {
        **aggregated,
        "stability": stab_delta,
        "authority": auth_delta,
        "population_pct": (new_pop - state.population) / max(state.population, 1),
    }
    return state_after, final_deltas, evolution_notes


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _tier_to_narrator(tier: ActionResultTier) -> ResultTier:
    return ResultTier(tier.value)


async def resolve_full_turn(
    state: CivState,
    player_input: str,
    *,
    client: Any = None,
    rng_seed: int = 42,
    generate_narrative: bool = True,
    capacity_params: type[CapacityParams] = CapacityParams,
    recent_imagery: Optional[list[str]] = None,
    history_context: Optional[str] = None,
) -> FullTurnResult:
    """完整回合：拆分 → 意图 → 国力 → 摩擦掷骰 → 数值 → 叙事。

    固定 rng_seed 保证可复现。dilution 只乘数值，不改 P_success。
    history_context 由记忆检索器在叙事前注入；默认 None。
    """
    text = player_input.strip()
    if not text:
        raise ValueError("玩家输入不能为空")

    split = await split_tasks(text, client=client)

    intent_jobs: list[tuple[str, str]] = []  # id, intent_text
    for sub in split.subtasks:
        if not split.is_multi_task:
            intent_text = text
        else:
            intent_text = sub.description
            if sub.original_fragment and sub.original_fragment not in sub.description:
                intent_text = (
                    f"{sub.description}\n（原文片段：{sub.original_fragment}）"
                )
        intent_jobs.append((sub.id, intent_text))

    # 多子任务并行解析，避免串行累加到前端加载超时
    parsed = await asyncio.gather(
        *[
            parse_intent(intent_text, state, client=client)
            for _, intent_text in intent_jobs
        ]
    )
    intents: list[IntentResult] = list(parsed)
    sub_meta: list[tuple[str, str, IntentResult]] = [
        (sid, intent_text, intent)
        for (sid, intent_text), intent in zip(intent_jobs, intents, strict=True)
    ]

    return await resolve_prepared_turn(
        state, text, split, sub_meta, client=client, rng_seed=rng_seed,
        generate_narrative=generate_narrative, capacity_params=capacity_params,
        recent_imagery=recent_imagery, history_context=history_context,
    )


async def resolve_prepared_turn(
    state: CivState,
    text: str,
    split: TaskSplitResult,
    sub_meta: list[tuple[str, str, IntentResult]],
    *,
    rng_seed: int,
    generate_narrative: bool = False,
    client: Any = None,
    capacity_params: type[CapacityParams] = CapacityParams,
    recent_imagery: Optional[list[str]] = None,
    history_context: Optional[str] = None,
) -> FullTurnResult:
    """Resolve typed decrees from either the LLM parser or the local decree menu."""
    rng = random.Random(rng_seed)
    intents = [intent for _, _, intent in sub_meta]
    vague_prompts = [
        i.clarification_prompt or ""
        for i in intents
        if i.is_too_vague and i.clarification_prompt
    ]
    actionable = [(sid, desc, intent) for sid, desc, intent in sub_meta if not intent.is_too_vague]

    # 整回合仅模糊任务：返回反问，不结算
    if not actionable:
        return FullTurnResult(
            player_input=text,
            split=split,
            intents=intents,
            vague_prompts=vague_prompts,
            settlement_skipped=True,
            capacity=None,
            subtasks=[
                SubtaskResolution(
                    subtask_id=sid,
                    description=desc,
                    intent=intent,
                    skipped_vague=True,
                )
                for sid, desc, intent in sub_meta
            ],
            aggregated_deltas={},
            dimension_changes={},
            events=[],
            overall_tier=None,
            importance=Importance.NORMAL,
            turn_years=0.0,
            state_before=state,
            state_after=None,
            narration_input=None,
            narrative="; ".join(p for p in vague_prompts if p) or None,
            rng_seed=rng_seed,
        )

    class_tension = estimate_class_tension(state)
    elite_cohesion = estimate_elite_cohesion(state)
    resistance = compute_resistance(
        state.bureaucratization, class_tension, elite_cohesion
    )

    cap_actions = [
        (intent.scale.value, float(intent.cognitive_gap))
        for _, _, intent in actionable
    ]
    capacity = settle_from_state(
        state,
        cap_actions,
        class_tension=class_tension,
        elite_cohesion=elite_cohesion,
        params=capacity_params,
    )
    dilution = capacity.dilution_factor

    # 模糊任务仍记入列表但跳过
    resolutions: list[SubtaskResolution] = []
    demand_iter = iter(capacity.demands)

    for sid, desc, intent in sub_meta:
        if intent.is_too_vague:
            resolutions.append(
                SubtaskResolution(
                    subtask_id=sid,
                    description=desc,
                    intent=intent,
                    skipped_vague=True,
                )
            )
            continue

        demand_item = next(demand_iter)
        unexec = _is_unexecutable(intent)
        base = _base_deltas_for_intent(intent)

        if unexec:
            tier = ActionResultTier.FAILURE
            p_success = 0.0
            mult = 0.0
            diluted: dict[str, float] = {k: 0.0 for k in base}
            sub = SubtaskResolution(
                subtask_id=sid,
                description=desc,
                intent=intent,
                is_unexecutable=True,
                demand=demand_item.demand,
                dilution_factor=dilution,
                resistance=resistance,
                p_success=p_success,
                result_tier=tier,
                effect_mult=mult,
                base_deltas=base,
                diluted_deltas=diluted,
            )
            sub.events = _collect_events(sub)
            resolutions.append(sub)
            continue

        infra = 1.0 if intent.prerequisites.met else 0.0
        # 随机因子：用固定种子可复现，范围约 0.85–1.15
        random_factor = 0.85 + 0.30 * rng.random()
        p_success = compute_p_success_from_state(
            state,
            cognitive_gap=float(intent.cognitive_gap),
            infrastructure_mod=infra,
            relevant_accumulation=_relevant_accumulation(
                state, intent.action_domain.value
            ),
            random_factor=random_factor,
            prerequisites_met=intent.prerequisites.met,
            class_tension=class_tension,
            elite_cohesion=elite_cohesion,
        )
        tier = roll_result_tier(p_success, rng=rng)
        # 前置不满足：降级路径——不允许成功/部分成功档（P=0 表仍有小概率 success）
        if not intent.prerequisites.met and tier in (
            ActionResultTier.GREAT_SUCCESS,
            ActionResultTier.SUCCESS,
            ActionResultTier.PARTIAL,
        ):
            tier = ActionResultTier.FAILURE
        mult = effect_multiplier(tier)
        # 稀释只乘数值
        diluted = _apply_tier_and_dilution(base, tier, dilution)

        sub = SubtaskResolution(
            subtask_id=sid,
            description=desc,
            intent=intent,
            is_unexecutable=False,
            demand=demand_item.demand,
            dilution_factor=dilution,
            resistance=resistance,
            p_success=p_success,
            result_tier=tier,
            effect_mult=mult,
            base_deltas=base,
            diluted_deltas=diluted,
        )
        sub.events = _collect_events(sub)
        resolutions.append(sub)

    settled = [s for s in resolutions if not s.skipped_vague]
    aggregated: dict[str, float] = {}
    for s in settled:
        for k, v in s.diluted_deltas.items():
            aggregated[k] = aggregated.get(k, 0.0) + v

    # 并行推进：取最长耗时；前置未满足时实质无推进，年份消耗钳到 ≤2
    def _effective_years(sub: SubtaskResolution) -> float:
        y = sub.intent.time_estimate_years
        if not sub.intent.prerequisites.met or sub.is_unexecutable:
            return min(y, 2.0)
        return y

    turn_years = max((_effective_years(s) for s in settled), default=1.0)
    turn_years = max(0.1, turn_years)

    state_after, final_deltas, evolution_notes = _apply_aggregated_to_state(
        state,
        aggregated,
        turn_years,
        settled,
        class_tension,
        elite_cohesion,
    )

    passive_outcome = resolve_passive_event(state_after, turn_years, rng=rng)
    if passive_outcome is not None:
        state_after = passive_outcome.state_after
        final_deltas["stability"] = state_after.stability - state.stability
        final_deltas["authority"] = state_after.authority - state.authority
        final_deltas["population_pct"] = (
            state_after.population - state.population
        ) / max(state.population, 1)
        if state_after.class_tension is not None:
            final_deltas["class_tension"] = state_after.class_tension - class_tension

    tiers = [s.result_tier for s in settled if s.result_tier is not None]
    overall = _pick_overall_tier(tiers)
    pop_pct = final_deltas.get("population_pct", 0.0)
    importance = judge_importance(
        [s.intent for s in settled],
        tiers,
        final_deltas,
        pop_pct,
    )
    if passive_outcome is not None and not passive_outcome.mitigated:
        importance = Importance.MAJOR

    dim_changes = _format_dimension_changes(final_deltas, state, state_after)
    all_events: list[str] = []
    for s in settled:
        all_events.extend(s.events)
    all_events.extend(evolution_notes)
    if passive_outcome is not None:
        all_events.append(passive_outcome.summary)

    any_unexec = all(s.is_unexecutable for s in settled) and len(settled) > 0
    # 单一不可执行，或全部不可执行
    is_unexec_turn = any_unexec or (
        len(settled) == 1 and settled[0].is_unexecutable
    )

    action_desc = "；".join(s.intent.action_description for s in settled)
    unexec_reason = None
    if is_unexec_turn:
        parts = [
            s.intent.prerequisites.details or s.intent.time_estimate_reasoning
            for s in settled
            if s.is_unexecutable
        ]
        unexec_reason = "；".join(p for p in parts if p) or None
        dim_changes = {}

    narration_input = NarrationInput(
        civ_name=state.civ_name,
        year=state.year,
        action_description=action_desc,
        result_tier=_tier_to_narrator(
            ActionResultTier.FAILURE if is_unexec_turn else overall
        ),
        dimension_changes=dim_changes,
        events=all_events,
        is_unexecutable=is_unexec_turn,
        importance=importance,
        history_context=history_context,
        unexecutable_reason=unexec_reason,
        recent_imagery=list(recent_imagery or []),
    )

    narrative: Optional[str] = None
    if generate_narrative:
        narrative = await narrate(narration_input, client=client)

    # 若有模糊子任务，把反问附在叙事后供玩家看到
    if vague_prompts and narrative:
        narrative = narrative + "\n\n" + "\n".join(vague_prompts)
    elif vague_prompts and not narrative:
        narrative = "\n".join(vague_prompts)

    return FullTurnResult(
        player_input=text,
        split=split,
        intents=intents,
        vague_prompts=vague_prompts,
        settlement_skipped=False,
        capacity=capacity,
        subtasks=resolutions,
        aggregated_deltas=final_deltas,
        dimension_changes=dim_changes,
        events=all_events,
        overall_tier=overall if not is_unexec_turn else ActionResultTier.FAILURE,
        importance=importance,
        turn_years=turn_years,
        state_before=state,
        state_after=state_after,
        narration_input=narration_input,
        narrative=narrative,
        rng_seed=rng_seed,
    )


def full_turn_to_debug_dict(result: FullTurnResult) -> dict[str, Any]:
    """把 FullTurnResult 转成可 JSON 打印的中间产物树。"""
    cap = None
    if result.capacity is not None:
        c = result.capacity
        cap = {
            "capacity": c.capacity.capacity,
            "food_factor": c.capacity.food_factor,
            "bureau_factor": c.capacity.bureau_factor,
            "gov_factor": c.capacity.gov_factor,
            "food_surplus_ratio": c.capacity.food_surplus_ratio,
            "transmission": c.transmission.transmission,
            "authority_norm": c.transmission.authority_norm,
            "power_concentration": c.transmission.power_concentration,
            "elite_cohesion": c.transmission.elite_cohesion,
            "governance": c.transmission.governance,
            "legitimacy": c.transmission.legitimacy,
            "available": c.available,
            "total_demand": c.total_demand,
            "base_dilution_ratio": c.base_dilution_ratio,
            "dilution_factor": c.dilution_factor,
            "demands": [
                {
                    "scale": d.scale,
                    "cognitive_gap": d.cognitive_gap,
                    "resistance": d.resistance,
                    "difficulty": d.difficulty,
                    "scale_cost": d.scale_cost,
                    "demand": d.demand,
                }
                for d in c.demands
            ],
        }

    subs = []
    for s in result.subtasks:
        subs.append(
            {
                "subtask_id": s.subtask_id,
                "description": s.description,
                "skipped_vague": s.skipped_vague,
                "is_unexecutable": s.is_unexecutable,
                "intent": s.intent.model_dump(mode="json"),
                "demand": s.demand,
                "dilution_factor": s.dilution_factor,
                "resistance": s.resistance,
                "p_success": s.p_success,
                "result_tier": s.result_tier.value if s.result_tier else None,
                "effect_mult": s.effect_mult,
                "base_deltas": s.base_deltas,
                "diluted_deltas": s.diluted_deltas,
                "events": s.events,
            }
        )

    state_after = None
    if result.state_after is not None:
        sb, sa = result.state_before, result.state_after
        state_after = {
            "year": sa.year,
            "turn": sa.turn,
            "population": sa.population,
            "stability": sa.stability,
            "authority": sa.authority,
            "bureaucratization": sa.bureaucratization,
            "class_tension": sa.class_tension,
            "elite_cohesion": sa.elite_cohesion,
            "delta_population": sa.population - sb.population,
            "delta_stability": sa.stability - sb.stability,
            "delta_authority": sa.authority - sb.authority,
        }

    return {
        "player_input": result.player_input,
        "rng_seed": result.rng_seed,
        "split": result.split.model_dump(mode="json"),
        "vague_prompts": result.vague_prompts,
        "settlement_skipped": result.settlement_skipped,
        "capacity": cap,
        "subtasks": subs,
        "aggregated_deltas": result.aggregated_deltas,
        "dimension_changes": result.dimension_changes,
        "events": result.events,
        "overall_tier": result.overall_tier.value if result.overall_tier else None,
        "importance": result.importance.value,
        "turn_years": result.turn_years,
        "state_after": state_after,
        "narration_input": (
            result.narration_input.model_dump(mode="json")
            if result.narration_input
            else None
        ),
        "narrative": result.narrative,
    }
