"""Single-player decree vocabulary and chronicle, using CivSim's full numerical engine."""

import re

from backend.engine.action_resolver import FullTurnResult, resolve_prepared_turn
from backend.engine.food import calculate_food_surplus_from_state
from backend.llm.intent_parser import IntentResult, Prerequisites
from backend.llm.task_splitter import MAX_SUBTASKS, SubTask, TaskSplitResult
from backend.models.schemas import ActionResultTier, CivState
from backend.templates.actions import ALL_ACTIONS, ActionDef, check_prerequisites
from backend.templates.civilizations import CIVILIZATION_TEMPLATES


OPENINGS = {
    "zhou": "宗周初定，四方贡赋沿驿道入朝。渭水两岸的田地等着引渠，仓吏和匠人都在等你的第一道政令。",
    "egypt": "尼罗河的洪水退去，测田人重新立起界石。要让下一季的谷物进入粮仓，王廷须先决定如何使用民力。",
    "sumer": "幼发拉底河的支渠穿过城邦。神庙掌管粮秣，各城各有田界。先从一项能聚集人心的政事做起。",
    "harappa": "城门内，秤砣和砖块各有定制。商旅备舟，农人候雨，议事者等着今日的决定。",
    "babylon": "河渠把村庄连到巴比伦的市场。抄写员摊开泥板，记下新的王令以及它将如何改变这座城。",
    "greece": "海湾之间散布着城邦。田地有限，商船将至，广场上的议事者正等候今日的提案。",
}
# Ordering here is also the ordering of the offline decree palette.
ALIASES = {
    "econ_irrigation": ("修渠", "挖渠", "开渠", "修水利", "疏浚水渠", "修建水渠"),
    "econ_granary": ("建仓", "建粮仓", "建造粮仓", "修仓", "建仓储粮"),
    "econ_reclaim": ("垦荒", "开荒", "扩耕"),
    "tech_farm": ("改良农具", "改进耕具"),
    "cul_school": ("办学", "设学", "建学宫", "兴办学宫"),
    "econ_market": ("开市", "设市", "兴办集市", "开设集市"),
    "pol_appoint": ("选官", "任官", "任命官员"),
    "comp_relief": ("赈灾", "赈济", "开仓赈济", "开仓放粮"),
}
DECREES = {a.id: a for a in ALL_ACTIONS if a.id in ALIASES}
TIER_NOTES = {
    ActionResultTier.GREAT_SUCCESS: "地方响应甚速，成效超出原议",
    ActionResultTier.SUCCESS: "诸司依令施行，所议之事已见成效",
    ActionResultTier.PARTIAL: "各地办理有迟有速，只收到部分成效",
    ActionResultTier.FAILURE: "地方未能把政令落实，所期收效未现",
    ActionResultTier.DISASTER: "推行受挫，原定安排引起了反效果",
}


def catalog() -> dict:
    return {
        "templates": [{"id": k, "name": s.civ_name, "description": OPENINGS[k]}
                      for k, s in CIVILIZATION_TEMPLATES.items()],
        "decrees": [{"id": k, "title": DECREES[k].name, "text": DECREES[k].name,
                     "description": DECREES[k].description} for k in ALIASES],
    }


def statistics(s: CivState) -> list[dict]:
    values = [
        ("population", "人口", s.population, "人"), ("stability", "稳定", s.stability, "点"),
        ("authority", "统治力", s.authority, "点"),
        ("food", "粮食供需比", calculate_food_surplus_from_state(s), "倍"),
        ("agriculture", "农业技术", s.tech_agriculture, "级"),
        ("engineering", "工程技术", s.tech_engineering, "级"),
    ]
    return [{"id": key, "label": label, "value": round(value, 2), "unit": unit}
            for key, label, value, unit in values]


def parse_local(text: str) -> tuple[list[tuple[ActionDef, str]], str | None]:
    """Restrict offline orders to affirmative, recognized commands. Unknown clauses never run."""
    if re.search(r"不|勿|莫|停止|暂停|取消|还是|或者|是否|为何|为什么|[?？]|(?:吗|么)[。！!]?\s*$", text):
        return [], "本地政令须指明要办的事项。请选定一道肯定的政令，例如「兴修水利」。"
    fragments = re.split(r"\s*(?:[、，,；;。\n]+|并且|然后|并|再|同时|以及|和)\s*", text.strip())
    orders = []
    lookup = {name: a for k, a in DECREES.items() for name in (a.name, *ALIASES[k])}
    for fragment in filter(None, fragments):
        cleaned = re.sub(r"^(?:(?:今年|本年|下令|颁令|决定|请|先|集中民力|组织民力|动员民力|只|要|在本地|在各地)\s*)+", "", fragment)
        scale = "medium"
        for key, pattern in (("large", r"^(?:大规模|举国|全面|全国|大举)"), ("small", r"^(?:小规模|试行|局部|先行试点)")):
            if re.match(pattern, cleaned):
                scale, cleaned = key, re.sub(pattern, "", cleaned).strip()
                break
        action = lookup.get(cleaned.strip(" ！!"))
        if not action:
            return [], "本地史官尚未识别这项安排。可选「兴修水利」或「修建粮仓」，也可用顿号组合两道政令。"
        if any(a.id == action.id for a, _ in orders):
            return [], "这一回合重复列出了同一事项，请保留一项并指明规模。"
        orders.append((action, scale))
    if not 1 <= len(orders) <= MAX_SUBTASKS:
        return [], f"请提出 1 至 {MAX_SUBTASKS} 项具体政令。"
    return orders, None


async def resolve_local(state: CivState, text: str, orders, seed: int) -> FullTurnResult:
    subtasks, parsed = [], []
    for i, (action, scale) in enumerate(orders, 1):
        task = SubTask(id=f"t{i}", description=action.description, original_fragment=action.name, priority=i)
        subtasks.append(task)
        met = check_prerequisites(action, state)
        intent = IntentResult(
            action_domain=action.domain, action_type=action.name, action_description=action.description,
            cognitive_gap=action.cognitive_gap, scale=scale, time_estimate_years={"small": 1, "medium": 2, "large": 4}[scale],
            time_estimate_reasoning="按本地政令的动员规模计年",
            prerequisites=Prerequisites(met=met, details="具备所需条件" if met else "当前国势尚未达到政令前提"),
        )
        parsed.append((task.id, action.name, intent))
    split = TaskSplitResult(is_multi_task=len(orders)>1, subtasks=subtasks, split_reason="按明确的本地政令拆分")
    return await resolve_prepared_turn(state, text, split, parsed, rng_seed=seed)


def chronicle(result: FullTurnResult) -> str:
    lines = [sub.intent.action_type + "：" + (
        TIER_NOTES[sub.result_tier] if sub.intent.prerequisites.met else "国中条件未备，未能如期推行"
    ) + "。" for sub in result.subtasks if sub.result_tier is not None]
    cap = result.capacity
    if cap and cap.dilution_factor < 0.999:
        lines.append(f"各项政令共需 {cap.total_demand:.1f} 国力，本轮可调 {cap.available:.1f}，实际效果折为 {cap.dilution_factor:.0%}。")
    before, after = result.state_before, result.state_after
    lines.append(f"经 {result.turn_years:g} 年，户口由 {before.population:,} 至 {after.population:,}。")
    if cap and cap.dilution_factor < 0.999:
        lines.append("议事者请下回合择要而行，集中可用的民力。")
    elif calculate_food_surplus_from_state(after) < 1:
        lines.append("仓吏报称收成还供不上所需，下一次议事宜先看田亩和粮数。")
    elif after.stability < 40:
        lines.append("地方人心未定，下一次议事宜先察民生，再定役期。")
    lines.extend(result.vague_prompts)
    return "".join(lines)
