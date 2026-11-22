"""行动类型库与动态菜单生成（设计文档 §4.1–4.2）。

初版每个域 3–5 个行动，按当前 CivState 筛选可用项并粗算难度提示。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.engine.food import calculate_food_surplus_from_state
from backend.models.schemas import CivState

DifficultyHint = str  # 容易 / 中等 / 困难 / 极难

DOMAIN_LABELS: dict[str, str] = {
    "economic": "经济",
    "political": "政治",
    "military": "军事",
    "cultural": "文化",
    "technology": "科技",
    "composite": "综合",
}


@dataclass(frozen=True)
class ActionDef:
    """单条行动类型定义。"""

    id: str
    name: str
    domain: str
    description: str
    prerequisites: dict[str, float] = field(default_factory=dict)
    # 相对时代认知的超前程度粗分（0–5），用于难度提示
    cognitive_gap: int = 0
    suggested_input: str | None = None

    def input_text(self) -> str:
        return self.suggested_input or self.name


# ---------------------------------------------------------------------------
# 状态取值：支持前置条件键
# ---------------------------------------------------------------------------


PREREQ_LABELS: dict[str, tuple[str, str]] = {
    "food_surplus_ratio": ("粮食供需比", "倍"),
    "grain_reserve": ("官仓储粮", "倍"),
    "relief_capacity": ("赈济余力（粮产+仓储）", ""),
    "literacy_rate": ("识字率", ""),
    "authority": ("统治力", "点"),
    "stability": ("稳定", "点"),
    "bureaucratization": ("官僚化", ""),
    "tech_agriculture": ("农业技术", "级"),
    "tech_engineering": ("工程技术", "级"),
    "tech_knowledge": ("知识技术", "级"),
    "population": ("人口", "人"),
    "acc_academic": ("学术底蕴", ""),
    "acc_military": ("军事底蕴", ""),
    "acc_commercial": ("商业底蕴", ""),
    "acc_administrative": ("行政底蕴", ""),
    "acc_cultural": ("礼乐底蕴", ""),
    "legitimacy_traditional": ("传统正统", ""),
    "legitimacy_religious": ("天命/神权正统", ""),
    "class_tension": ("阶级矛盾", ""),
    "elite_cohesion": ("精英凝聚力", ""),
}


def _state_value(state: CivState, key: str) -> float:
    """从 CivState 解析前置条件数值；未知键视为 0。"""
    if key == "food_surplus_ratio":
        return float(calculate_food_surplus_from_state(state))
    if key == "grain_reserve":
        return float(getattr(state, "grain_reserve", 0.15))
    if key == "relief_capacity":
        # 既有当期粮产或官仓储粮其一可支应赈济，避免饥年反而无法开仓放粮
        food = float(calculate_food_surplus_from_state(state))
        reserve = float(getattr(state, "grain_reserve", 0.15))
        return max(food, 0.85 + reserve)
    if key == "literacy_rate":
        return float(state.literacy_rate())
    if key == "authority":
        return float(state.authority)
    if key == "stability":
        return float(state.stability)
    if key == "bureaucratization":
        return float(state.bureaucratization)
    if key == "tech_agriculture":
        return float(state.tech_agriculture)
    if key == "tech_engineering":
        return float(state.tech_engineering)
    if key == "tech_knowledge":
        return float(state.tech_knowledge)
    if key == "population":
        return float(state.population)
    if key.startswith("acc_"):
        field_name = key[4:]
        return float(getattr(state.accumulations, field_name, 0.0))
    if key == "legitimacy_traditional":
        return float(state.legitimacy.traditional)
    if key == "legitimacy_religious":
        return float(state.legitimacy.religious)
    if key == "class_tension":
        return float(state.class_tension if state.class_tension is not None else 0.4)
    if key == "elite_cohesion":
        return float(state.elite_cohesion if state.elite_cohesion is not None else 0.5)
    return 0.0


def explain_unmet_prerequisites(
    action: ActionDef | dict[str, Any], state: CivState
) -> list[str]:
    """返回未满足的前置条件可读说明；全部满足时返回空列表。"""
    prereqs = (
        (action.get("prerequisites") or {})
        if isinstance(action, dict)
        else action.prerequisites
    )
    missing: list[str] = []
    for key, minimum in prereqs.items():
        current = _state_value(state, key)
        target = float(minimum)
        if current + 1e-9 < target:
            label, unit = PREREQ_LABELS.get(key, (key, ""))
            missing.append(f"{label}需 ≥ {target:g}{unit}（现 {current:.2f}{unit}）")
    return missing


def check_prerequisites(action: ActionDef | dict[str, Any], state: CivState) -> bool:
    """检查行动前置条件是否全部满足。"""
    if isinstance(action, dict):
        prereqs = action.get("prerequisites") or {}
    else:
        prereqs = action.prerequisites
    for key, minimum in prereqs.items():
        if _state_value(state, key) + 1e-9 < float(minimum):
            return False
    return True


def estimate_difficulty(action: ActionDef, state: CivState) -> DifficultyHint:
    """基于认知差距与当前状态相对前置条件的裕度，粗算难度。"""
    # 裕度：各前置条件 (current/min) 的最小值；无前置视为宽松
    margins: list[float] = []
    for key, minimum in action.prerequisites.items():
        min_v = float(minimum)
        if min_v <= 0:
            continue
        margins.append(_state_value(state, key) / min_v)

    if margins:
        min_margin = min(margins)
    else:
        min_margin = 2.0

    # 认知分与裕度合成粗分：越高越难
    # margin >= 1.4 → 宽裕；1.0–1.4 → 刚好；接近 1.0 且 cognitive 高 → 难
    score = action.cognitive_gap * 1.2
    if min_margin < 1.05:
        score += 2.5
    elif min_margin < 1.2:
        score += 1.5
    elif min_margin < 1.5:
        score += 0.6
    else:
        score -= 0.4

    # 统治力/稳定偏低时政治军事类再抬一点
    if action.domain in {"political", "military"} and state.authority < 40:
        score += 0.8
    if action.domain == "military" and _state_value(state, "food_surplus_ratio") < 1.15:
        score += 0.5

    if score >= 4.5:
        return "极难"
    if score >= 3.0:
        return "困难"
    if score >= 1.5:
        return "中等"
    return "容易"


# ---------------------------------------------------------------------------
# 行动库（初版：约 26 条，宁少勿滥）
# ---------------------------------------------------------------------------

ALL_ACTIONS: list[ActionDef] = [
    # ---- 经济 ----
    ActionDef(
        id="econ_reclaim",
        name="开垦荒地",
        domain="economic",
        description="组织民力开荒扩耕，提高可耕地与粮产。",
        prerequisites={"tech_agriculture": 0.8},
        cognitive_gap=0,
    ),
    ActionDef(
        id="econ_irrigation",
        name="兴修水利",
        domain="economic",
        description="挖渠筑堰，改善灌溉，稳固农事。",
        prerequisites={"tech_agriculture": 0.9, "food_surplus_ratio": 0.85},
        cognitive_gap=1,
    ),
    ActionDef(
        id="econ_granary",
        name="修建粮仓",
        domain="economic",
        description="于要冲建仓积谷，以备凶年。",
        prerequisites={"tech_engineering": 0.8, "food_surplus_ratio": 0.85},
        cognitive_gap=0,
    ),
    ActionDef(
        id="econ_market",
        name="开设市集",
        domain="economic",
        description="开放坊市、规范交易，促商旅往来。",
        prerequisites={"tech_knowledge": 0.8, "authority": 18},
        cognitive_gap=1,
    ),
    ActionDef(
        id="econ_tribute",
        name="调整贡赋",
        domain="economic",
        description="改定诸侯/地方贡赋轻重与征缴方式。",
        prerequisites={"authority": 40},
        cognitive_gap=1,
    ),
    ActionDef(
        id="econ_currency",
        name="铸造货币",
        domain="economic",
        description="统一铸币以便商贾，需工程与商业根基。",
        prerequisites={
            "tech_engineering": 2.0,
            "acc_commercial": 0.5,
            "bureaucratization": 0.35,
        },
        cognitive_gap=3,
    ),
    # ---- 政治 ----
    ActionDef(
        id="pol_appoint",
        name="任命官吏",
        domain="political",
        description="选任地方守令与朝中职官，理顺政令。",
        prerequisites={"authority": 18, "bureaucratization": 0.15},
        cognitive_gap=0,
    ),
    ActionDef(
        id="pol_code",
        name="编纂律令",
        domain="political",
        description="整理刑律与礼法，昭示天下。",
        prerequisites={"tech_knowledge": 1.0, "bureaucratization": 0.2},
        cognitive_gap=1,
    ),
    ActionDef(
        id="pol_enfeoff",
        name="分封诸侯",
        domain="political",
        description="以土地与名号分封宗亲功臣，巩固藩屏。",
        prerequisites={"authority": 40, "legitimacy_traditional": 0.4},
        cognitive_gap=0,
    ),
    ActionDef(
        id="pol_prefecture",
        name="推行郡县",
        domain="political",
        description="以郡县代封建，强化中央直控地方。",
        prerequisites={
            "bureaucratization": 0.35,
            "tech_knowledge": 1.5,
            "authority": 45,
        },
        cognitive_gap=3,
    ),
    ActionDef(
        id="pol_purge",
        name="整肃权贵",
        domain="political",
        description="裁抑强宗、罢黜不法，强化王权（阻力极大）。",
        prerequisites={"authority": 55, "stability": 45},
        cognitive_gap=2,
    ),
    # ---- 军事 ----
    ActionDef(
        id="mil_drill",
        name="操练士卒",
        domain="military",
        description="按季节校阅、训练甲士与徒兵。",
        prerequisites={"food_surplus_ratio": 1.0, "acc_military": 0.2},
        cognitive_gap=0,
    ),
    ActionDef(
        id="mil_walls",
        name="修筑城池",
        domain="military",
        description="加固城垣、挖壕设障，备御外患。",
        prerequisites={"tech_engineering": 1.0, "food_surplus_ratio": 1.0},
        cognitive_gap=1,
    ),
    ActionDef(
        id="mil_arms",
        name="铸造兵器",
        domain="military",
        description="扩作甲兵车马，充实府库武备。",
        prerequisites={"tech_engineering": 1.0, "food_surplus_ratio": 1.05},
        cognitive_gap=1,
    ),
    ActionDef(
        id="mil_standing",
        name="建立常备军",
        domain="military",
        description="养不耕之卒以备征伐，需充足余粮。",
        prerequisites={"food_surplus_ratio": 1.2, "acc_military": 0.3},
        cognitive_gap=2,
    ),
    ActionDef(
        id="mil_campaign",
        name="征伐边疆",
        domain="military",
        description="出兵经略边地，扩张或慑服外族。",
        prerequisites={
            "food_surplus_ratio": 1.15,
            "acc_military": 0.35,
            "authority": 40,
        },
        cognitive_gap=2,
    ),
    ActionDef(
        id="mil_suppress",
        name="镇压叛乱",
        domain="military",
        description="发兵平定地方骚乱与叛附。",
        prerequisites={"authority": 25, "acc_military": 0.2},
        cognitive_gap=1,
    ),
    # ---- 文化 ----
    ActionDef(
        id="cul_school",
        name="设立学宫",
        domain="cultural",
        description="于都邑设学，延师授业，培养识字人才。",
        prerequisites={"tech_knowledge": 0.8, "food_surplus_ratio": 0.88},
        cognitive_gap=1,
    ),
    ActionDef(
        id="cul_ritual",
        name="举行大祭",
        domain="cultural",
        description="祭祀天地祖先，以礼乐巩固正统。",
        prerequisites={"legitimacy_religious": 0.3, "acc_cultural": 0.2},
        cognitive_gap=0,
    ),
    ActionDef(
        id="cul_mandate",
        name="宣扬天命",
        domain="cultural",
        description="广布天命叙事，强化统治合法性。",
        prerequisites={"authority": 30, "acc_cultural": 0.3},
        cognitive_gap=1,
    ),
    ActionDef(
        id="cul_temple",
        name="修建宗庙",
        domain="cultural",
        description="营建宗庙社稷，昭示血缘与正统。",
        prerequisites={"food_surplus_ratio": 1.0, "acc_cultural": 0.3},
        cognitive_gap=1,
    ),
    ActionDef(
        id="cul_canon",
        name="编纂典籍",
        domain="cultural",
        description="整理典章史册，传之后世（需较高知识水平）。",
        prerequisites={"tech_knowledge": 1.6, "acc_academic": 0.4},
        cognitive_gap=2,
    ),
    # ---- 科技 ----
    ActionDef(
        id="tech_farm",
        name="改进农具",
        domain="technology",
        description="推广铁器/改良农具，提升耕作效率。",
        prerequisites={"tech_agriculture": 1.0, "food_surplus_ratio": 0.85},
        cognitive_gap=1,
    ),
    ActionDef(
        id="tech_engineer",
        name="钻研营造",
        domain="technology",
        description="集工匠研习筑城、造桥、器械之术。",
        prerequisites={"tech_engineering": 1.0, "food_surplus_ratio": 1.05},
        cognitive_gap=1,
    ),
    ActionDef(
        id="tech_scholars",
        name="延揽学者",
        domain="technology",
        description="招纳博学之士，充实知识与文书能力。",
        prerequisites={"tech_knowledge": 1.0, "food_surplus_ratio": 1.1},
        cognitive_gap=1,
    ),
    ActionDef(
        id="tech_import",
        name="引进异域技艺",
        domain="technology",
        description="自远方习得新工艺与知识（认知跨度大）。",
        prerequisites={"tech_knowledge": 1.8, "acc_commercial": 0.4},
        cognitive_gap=4,
    ),
    # ---- 综合 ----
    ActionDef(
        id="comp_tour",
        name="巡狩四方",
        domain="composite",
        description="天子巡行邦国，昭示威仪、体察民情。",
        prerequisites={"authority": 35, "food_surplus_ratio": 1.05},
        cognitive_gap=0,
    ),
    ActionDef(
        id="comp_relief",
        name="赈济饥民",
        domain="composite",
        description="开仓放粮、安抚流民，缓和社会张力。",
        prerequisites={"relief_capacity": 0.92, "authority": 18},
        cognitive_gap=0,
    ),
]


def generate_full_action_catalog(state: CivState) -> list[dict[str, Any]]:
    """返回全部 28 项行动，含当前是否可用、难度及未满足前提说明。"""
    domain_order = {d: i for i, d in enumerate(DOMAIN_LABELS)}
    items: list[dict[str, Any]] = []
    for action in ALL_ACTIONS:
        unmet = explain_unmet_prerequisites(action, state)
        ok = len(unmet) == 0
        items.append(
            {
                "id": action.id,
                "name": action.name,
                "title": action.name,
                "text": action.input_text(),
                "domain": action.domain,
                "domainLabel": DOMAIN_LABELS.get(action.domain, action.domain),
                "description": action.description,
                "difficulty": estimate_difficulty(action, state) if ok else "受限",
                "available": ok,
                "unmetReason": "；".join(unmet) if unmet else None,
            }
        )
    items.sort(key=lambda item: (domain_order.get(item["domain"], 99), not item["available"], item["name"]))
    return items


def generate_action_menu(state: CivState) -> list[dict[str, Any]]:
    """根据当前状态动态生成可用行动菜单。"""
    available: list[dict[str, Any]] = []
    for action in ALL_ACTIONS:
        if not check_prerequisites(action, state):
            continue
        available.append(
            {
                "id": action.id,
                "name": action.name,
                "label": action.name,
                "domain": action.domain,
                "domain_label": DOMAIN_LABELS.get(action.domain, action.domain),
                "description": action.description,
                "difficulty_hint": estimate_difficulty(action, state),
                "suggested_input": action.input_text(),
                "disabled": False,
                "reason": None,
            }
        )
    # 稳定排序：按域顺序再按名称
    domain_order = {d: i for i, d in enumerate(DOMAIN_LABELS)}
    available.sort(key=lambda item: (domain_order.get(item["domain"], 99), item["name"]))
    return available


def menu_stats_for_state(state: CivState) -> dict[str, Any]:
    """调试/验收用：行动库规模与当前可用数。"""
    by_domain: dict[str, int] = {}
    for action in ALL_ACTIONS:
        by_domain[action.domain] = by_domain.get(action.domain, 0) + 1
    available = generate_action_menu(state)
    avail_by_domain: dict[str, int] = {}
    for item in available:
        d = item["domain"]
        avail_by_domain[d] = avail_by_domain.get(d, 0) + 1
    return {
        "total_actions": len(ALL_ACTIONS),
        "by_domain": by_domain,
        "available_count": len(available),
        "available_by_domain": avail_by_domain,
        "available_names": [a["name"] for a in available],
    }
