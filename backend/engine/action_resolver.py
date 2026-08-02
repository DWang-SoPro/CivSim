"""行动结果总结算。

第一阶段：`resolve_turn` + FakeActionInput（纯数学、无 LLM，供 pytest）。
第二阶段：`resolve_full_turn` 串联 TaskSplitter → IntentParser → capacity →
friction → 数值汇总 → 叙事输入组装（可选生成叙事）。
"""

from __future__ import annotations

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
from backend.engine.population import apply_population_growth
from backend.engine.stability import apply_stability, compute_stability_delta
from backend.llm.intent_parser import ActionScale, IntentResult, parse_intent
from backend.llm.narrator import Importance, NarrationInput, ResultTier, narrate
from backend.llm.task_splitter import TaskSplitResult, split_tasks
from backend.models.schemas import ActionResultTier, CivState

# 成功档 + medium 规模下的基础数值变动（再乘 scale/档位/稀释）
_SCALE_EFFECT: dict[str, float] = {
    "small": 0.5,
    "medium": 1.0,
    "large": 2.0,
}

_BASE_EFFECTS: dict[str, dict[str, float]] = {
    "economic": {
        "stability": 3.0,
        "authority": 1.5,
        "population_pct": 0.015,
        "tech_agriculture": 0.06,
        "class_tension": 0.02,
    },
    "military": {
        "stability": -1.5,
        "authority": 4.0,
        "population_pct": -0.02,
        "class_tension": 0.03,
    },
    "political": {
        "stability": 2.0,
        "authority": 5.0,
        "bureaucratization": 0.02,
        "class_tension": 0.025,
        "elite_cohesion": 0.02,
    },
    "cultural": {
        "stability": 3.0,
        "authority": 1.0,
        "tech_knowledge": 0.08,
        "elite_cohesion": 0.01,
    },
    "technology": {
        "stability": 1.0,
        "authority": 1.5,
        "tech_engineering": 0.1,
        "tech_agriculture": 0.02,
    },
    "composite": {
        "stability": 2.0,
        "authority": 2.0,
        "class_tension": 0.01,
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
    """查域基础变动 × 规模系数（尚未乘档位/稀释）。"""
    domain = intent.action_domain.value
    base = dict(_BASE_EFFECTS.get(domain, _BASE_EFFECTS["composite"]))
    scale_m = _SCALE_EFFECT.get(intent.scale.value, 1.0)
    return {k: v * scale_m for k, v in base.items()}


def _apply_tier_and_dilution(
    base: dict[str, float],
    tier: ActionResultTier,
    dilution: float,
) -> dict[str, float]:
    """数值效果 = base × effect_mult(tier) × dilution；failure→0。"""
    mult = effect_multiplier(tier)
    if mult == 0.0:
        return {k: 0.0 for k in base}
    # disaster 的负倍率：正向变动变负；本就为负的（如军征人口）再反号
    out: dict[str, float] = {}
    for k, v in base.items():
        out[k] = v * mult * dilution
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


def _apply_aggregated_to_state(
    state: CivState,
    aggregated: dict[str, float],
    turn_years: float,
    settled_subs: list[SubtaskResolution],
    class_tension: float,
    elite_cohesion: float,
) -> tuple[CivState, dict[str, float]]:
    """把行动数值汇总后接入各引擎，返回新状态与含被动项的最终 delta。"""
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

    stab_delta = compute_stability_delta(
        food_surplus_ratio=food,
        legitimacy_total=state.legitimacy_total(),
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

    # 积累：逐子任务应用（同回合依次叠）
    new_acc = state.accumulations
    for sub in settled_subs:
        if sub.skipped_vague or sub.result_tier is None:
            continue
        new_acc = apply_accumulation_turn(
            new_acc,
            action_domain=sub.intent.action_domain.value,
            tier=sub.result_tier,
            has_academy=False,
            bureaucratization=bureau,
        )

    state_after = state.model_copy(
        update={
            "population": new_pop,
            "stability": new_stability,
            "authority": new_authority,
            "bureaucratization": bureau,
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

    final_deltas = {
        **aggregated,
        "stability": stab_delta,
        "authority": auth_delta,
        "population_pct": (new_pop - state.population) / max(state.population, 1),
    }
    return state_after, final_deltas


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
) -> FullTurnResult:
    """完整回合：拆分 → 意图 → 国力 → 摩擦掷骰 → 数值 → 叙事。

    固定 rng_seed 保证可复现。dilution 只乘数值，不改 P_success。
    """
    text = player_input.strip()
    if not text:
        raise ValueError("玩家输入不能为空")

    rng = random.Random(rng_seed)
    split = await split_tasks(text, client=client)

    intents: list[IntentResult] = []
    sub_meta: list[tuple[str, str, IntentResult]] = []  # id, desc, intent
    for sub in split.subtasks:
        if not split.is_multi_task:
            intent_text = text
        else:
            intent_text = sub.description
            if sub.original_fragment and sub.original_fragment not in sub.description:
                intent_text = (
                    f"{sub.description}\n（原文片段：{sub.original_fragment}）"
                )
        intent = await parse_intent(intent_text, state, client=client)
        intents.append(intent)
        sub_meta.append((sub.id, intent_text, intent))

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

    state_after, final_deltas = _apply_aggregated_to_state(
        state,
        aggregated,
        turn_years,
        settled,
        class_tension,
        elite_cohesion,
    )

    tiers = [s.result_tier for s in settled if s.result_tier is not None]
    overall = _pick_overall_tier(tiers)
    pop_pct = final_deltas.get("population_pct", 0.0)
    importance = judge_importance(
        [s.intent for s in settled],
        tiers,
        final_deltas,
        pop_pct,
    )

    dim_changes = _format_dimension_changes(final_deltas, state, state_after)
    all_events: list[str] = []
    for s in settled:
        all_events.extend(s.events)

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
        history_context=None,
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
