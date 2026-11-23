"""单人模式天工图谱（科技里程碑）与典章制度演进评估。"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from backend.models.schemas import (
    CivState,
    DecisionStructure,
    LandSystem,
    SurplusExtraction,
)

# ---------------------------------------------------------------------------
# 指标度量表（用于统一计算各节点门槛达成度）
# ---------------------------------------------------------------------------

_MetricSpec = tuple[str, Callable[[CivState], float], Callable[[float], str]]

_METRICS: dict[str, _MetricSpec] = {
    "tech_agriculture": (
        "农业技艺",
        lambda s: float(s.tech_agriculture),
        lambda v: f"Lv {v:.2f}",
    ),
    "tech_engineering": (
        "工程营造",
        lambda s: float(s.tech_engineering),
        lambda v: f"Lv {v:.2f}",
    ),
    "tech_knowledge": (
        "礼乐典籍",
        lambda s: float(s.tech_knowledge),
        lambda v: f"Lv {v:.2f}",
    ),
    "grain_reserve": (
        "官仓余粮",
        lambda s: float(s.grain_reserve),
        lambda v: f"{round(v * 100)}%",
    ),
    "bureaucratization": (
        "官僚化度",
        lambda s: float(s.bureaucratization),
        lambda v: f"{round(v * 100)}%",
    ),
    "acc_academic": (
        "学术积累",
        lambda s: float(s.accumulations.academic),
        lambda v: f"{v:.2f}",
    ),
    "acc_commercial": (
        "商业积累",
        lambda s: float(s.accumulations.commercial),
        lambda v: f"{v:.2f}",
    ),
    "acc_military": (
        "军事积累",
        lambda s: float(s.accumulations.military),
        lambda v: f"{v:.2f}",
    ),
}


# ---------------------------------------------------------------------------
# 三大技艺脉络 × 五阶里程碑（共 15 节点）
# ---------------------------------------------------------------------------

TECH_BRANCHES: tuple[dict[str, Any], ...] = (
    {
        "id": "agriculture",
        "name": "农桑水利脉",
        "metricKey": "tech_agriculture",
        "accent": "agri",
        "nodes": (
            {
                "id": "agri_slash_hoe",
                "stage": 1,
                "era": "初耕",
                "name": "耒耜初耕",
                "subtitle": "辟土播百谷",
                "art": "stone_ard",
                "effect": "确立基础旱涝轮作与耜耕范式，可推行「开垦荒地」「兴修水利」。",
                "chronicleNote": "断木为耜，揉木为耒，民始知深耕易耨之利。",
                "reqs": (("tech_agriculture", 1.0),),
                "suggestedDecrees": ("开垦荒地", "兴修水利"),
            },
            {
                "id": "agri_bronze_plow",
                "stage": 2,
                "era": "耦耕",
                "name": "青铜耦犁",
                "subtitle": "深耕破板土",
                "art": "bronze_plow",
                "effect": "金属铧刃提升亩产余粮；达 Lv 1.7 后精耕细作将推动自耕小农涌现。",
                "chronicleNote": "铸铜为铧，二耜并耕，熟田日辟而仓廪渐实。",
                "reqs": (("tech_agriculture", 1.55),),
                "suggestedDecrees": ("改进农具", "兴修水利", "开垦荒地"),
            },
            {
                "id": "agri_channel_net",
                "stage": 3,
                "era": "兴渠",
                "name": "沟洫灌渠",
                "subtitle": "引川注阡陌",
                "art": "canal_weir",
                "effect": "骨干渠系与堰闸成网，显著缓冲季候水旱波动并支撑更高人口密度。",
                "chronicleNote": "筑堰分洪，十里一沟，百里一洫，泽国化为沃野。",
                "reqs": (("tech_agriculture", 2.2), ("tech_engineering", 1.5)),
                "suggestedDecrees": ("兴修水利", "钻研营造", "修建粮仓"),
            },
            {
                "id": "agri_ever_normal",
                "stage": 4,
                "era": "备荒",
                "name": "常平仓廩",
                "subtitle": "丰敛以济凶",
                "art": "ever_normal_granary",
                "effect": "建立官仓备荒体系与高储粮周转，大幅增强灾年「赈济饥民」兜底能力。",
                "chronicleNote": "丰岁籴谷入仓，荒年发粟赈民，斗米不致腾踊。",
                "reqs": (("tech_agriculture", 2.9), ("grain_reserve", 0.35)),
                "suggestedDecrees": ("修建粮仓", "改进农具", "赈济饥民"),
            },
            {
                "id": "agri_intensive_iron",
                "stage": 5,
                "era": "精耕",
                "name": "铁犁精耕",
                "subtitle": "曲面深翻土",
                "art": "iron_coulter",
                "effect": "铁器耕作与水利复种并进，释放庞大农业剩余以供养大一统工商业与军备。",
                "chronicleNote": "铁铧破坚，曲辕回转，一夫百亩而余粮充栋。",
                "reqs": (("tech_agriculture", 3.8), ("tech_engineering", 2.4)),
                "suggestedDecrees": ("改进农具", "引进异域技艺", "兴修水利"),
            },
        ),
    },
    {
        "id": "engineering",
        "name": "营造工兵脉",
        "metricKey": "tech_engineering",
        "accent": "eng",
        "nodes": (
            {
                "id": "eng_rammed_earth",
                "stage": 1,
                "era": "版筑",
                "name": "版筑夯土",
                "subtitle": "立城郭高墙",
                "art": "rammed_wall",
                "effect": "掌握百堵版筑与粮仓营建标准，可展开「修筑城池」「修建粮仓」。",
                "chronicleNote": "缩板以载，筑之登登，都邑郭郭由是而固。",
                "reqs": (("tech_engineering", 0.8),),
                "suggestedDecrees": ("修筑城池", "修建粮仓"),
            },
            {
                "id": "eng_bronze_foundry",
                "stage": 2,
                "era": "范铸",
                "name": "青铜冶铸",
                "subtitle": "合范成礼兵",
                "art": "bronze_foundry",
                "effect": "官营作坊合范量产矛戟与农具，带动兵甲精良与营建效率跃升。",
                "chronicleNote": "六齐调铜锡，范型出利器，工官之名著于鼎彝。",
                "reqs": (("tech_engineering", 1.5),),
                "suggestedDecrees": ("钻研营造", "铸造兵器", "修筑城池"),
            },
            {
                "id": "eng_coin_gauge",
                "stage": 3,
                "era": "衡制",
                "name": "泉府铸币",
                "subtitle": "统一度量衡",
                "art": "mint_coinage",
                "effect": "解锁统一铸币工艺，配合市集与官僚体系可推行「铸造货币」并开征货币税。",
                "chronicleNote": "范模齐一，圜钱流布四方，商旅不复困于物物相易。",
                "reqs": (
                    ("tech_engineering", 2.0),
                    ("acc_commercial", 0.45),
                    ("bureaucratization", 0.35),
                ),
                "suggestedDecrees": ("铸造货币", "开设市集", "钻研营造"),
            },
            {
                "id": "eng_standing_bastion",
                "stage": 4,
                "era": "坚壁",
                "name": "坚壁虎符",
                "subtitle": "兵械皆有律",
                "art": "city_bastion",
                "effect": "城防瓮城与虎符调度成型，常备军及远征兵团战斗效率与后勤稳定性大幅提高。",
                "chronicleNote": "深壕重关，铜符发兵，千里军需皆有定程。",
                "reqs": (("tech_engineering", 2.7), ("acc_military", 0.45)),
                "suggestedDecrees": ("建立常备军", "操练士卒", "修筑城池"),
            },
            {
                "id": "eng_blast_gear",
                "stage": 5,
                "era": "水排",
                "name": "水排鼓风",
                "subtitle": "借水力冶铁",
                "art": "water_bellows",
                "effect": "水力机械鼓风冶炼成型，铁器兵械与大型工程建造迈入高效率量产阶段。",
                "chronicleNote": "激水转轮，牵排鼓风，炉火昼夜不熄而百工皆足。",
                "reqs": (("tech_engineering", 3.6), ("tech_knowledge", 2.2)),
                "suggestedDecrees": ("钻研营造", "引进异域技艺", "铸造兵器"),
            },
        ),
    },
    {
        "id": "knowledge",
        "name": "礼乐典籍脉",
        "metricKey": "tech_knowledge",
        "accent": "know",
        "nodes": (
            {
                "id": "know_tally_script",
                "stage": 1,
                "era": "契刻",
                "name": "结绳刻符",
                "subtitle": "史官记朝事",
                "art": "oracle_script",
                "effect": "确立甲骨、泥板或简帛记事，为文书统计、学宫兴办与成文法奠基。",
                "chronicleNote": "书契既作，百官以治，万民以察。",
                "reqs": (("tech_knowledge", 0.8),),
                "suggestedDecrees": ("设立学宫", "编纂律令"),
            },
            {
                "id": "know_palace_academy",
                "stage": 2,
                "era": "兴学",
                "name": "太学典诰",
                "subtitle": "育士养官才",
                "art": "academy_scroll",
                "effect": "学宫覆盖与学术传统成形，持续抬升官僚化上限与识字率。",
                "chronicleNote": "建辟雍太学，聚天下俊彦以习礼乐算术。",
                "reqs": (("tech_knowledge", 1.4), ("acc_academic", 0.3)),
                "suggestedDecrees": ("设立学宫", "延揽学者", "任命官吏"),
            },
            {
                "id": "know_statutory_code",
                "stage": 3,
                "era": "明法",
                "name": "明法颁律",
                "subtitle": "铸刑书定序",
                "art": "bronze_statute",
                "effect": "法典律令配合郡县官吏网络，推动决策结构向「郡县官僚体系」跃迁。",
                "chronicleNote": "悬法象魏，赏罚不私贵戚，政令自朝廷直达闾里。",
                "reqs": (("tech_knowledge", 1.8), ("bureaucratization", 0.35)),
                "suggestedDecrees": ("编纂律令", "推行郡县", "任命官吏"),
            },
            {
                "id": "know_canon_archive",
                "stage": 4,
                "era": "修史",
                "name": "石渠修史",
                "subtitle": "汇聚百家言",
                "art": "canon_library",
                "effect": "具备官修典籍与统合意识形态的能力，可推行「编纂典籍」稳固法理合法性。",
                "chronicleNote": "石渠藏典，校雠百家，文脉绵延而礼法有所宗。",
                "reqs": (("tech_knowledge", 2.5), ("acc_academic", 0.5)),
                "suggestedDecrees": ("编纂典籍", "延揽学者", "设立学宫"),
            },
            {
                "id": "know_print_compass",
                "stage": 5,
                "era": "格物",
                "name": "格物致知",
                "subtitle": "历算传四方",
                "art": "armillary_press",
                "effect": "天文历算与典籍传布体系臻于成熟，统筹学术、工程与跨文明交流进入高峰。",
                "chronicleNote": "浑仪测天度，典籍广传布，穷理致用而技艺日新。",
                "reqs": (("tech_knowledge", 3.4), ("acc_academic", 0.75)),
                "suggestedDecrees": ("引进异域技艺", "编纂典籍", "延揽学者"),
            },
        ),
    },
)


# ---------------------------------------------------------------------------
# 典章制度演进图谱（田制 · 中枢政体 · 赋役征发）
# ---------------------------------------------------------------------------

LAND_NODES: tuple[dict[str, Any], ...] = (
    {
        "id": LandSystem.CLAN_COMMUNAL.value,
        "name": "氏族公社田制",
        "summary": "宗族或村社共同耕作、按习俗均分收获，阶级张力低但剩余率受限。",
        "triggerHint": "早期部落与河谷公社形态。",
        "suggestedDecrees": ("开垦荒地", "调整贡赋"),
    },
    {
        "id": LandSystem.NOBLE_ESTATE.value,
        "name": "贵族采邑领地",
        "summary": "食邑封君领有田土与依附农，封建兵源充沛但易滋生世袭割据。",
        "triggerHint": "在权威充足时施行「分封诸侯」可演进为此制。",
        "suggestedDecrees": ("分封诸侯", "整肃权贵"),
    },
    {
        "id": LandSystem.STATE_GRANT.value,
        "name": "井田/国有授田",
        "summary": "王室授田于民并按井田或口分收租，兼顾国家财政与田制秩序。",
        "triggerHint": "官僚化 ≥ 36% 时施行「推行郡县」可改采邑/公社为国有授田。",
        "suggestedDecrees": ("推行郡县", "调整贡赋"),
    },
    {
        "id": LandSystem.YEOMAN_SMALLHOLD.value,
        "name": "自耕小农田制",
        "summary": "编户齐民自耕自有土地，农业生产积极性最高，赋税与兵源皆稳。",
        "triggerHint": "农业技艺达 Lv 1.70 后「改进农具」可壮大自耕农比例。",
        "suggestedDecrees": ("改进农具", "开垦荒地"),
    },
    {
        "id": LandSystem.LANDLORD_TENANT.value,
        "name": "地主佃农租佃",
        "summary": "土地兼并形成租佃契约，商品与地租集中但易推高阶级矛盾。",
        "triggerHint": "兼并或剧变后形成，宜「整肃权贵」「调整贡赋」以缓和张力。",
        "suggestedDecrees": ("整肃权贵", "赈济饥民"),
    },
)

POLITY_NODES: tuple[dict[str, Any], ...] = (
    {
        "id": DecisionStructure.COUNCIL.value,
        "name": "城邦/长老议事",
        "summary": "决策需经长老或公民议会商讨，法理稳固但急令调动较缓。",
        "triggerHint": "早期城邦与联邦议事传统。",
        "suggestedDecrees": ("编纂律令", "推行郡县"),
    },
    {
        "id": DecisionStructure.OLIGARCHY.value,
        "name": "世卿贵族共治",
        "summary": "政权由世家宗室分享，重视传统礼制与贵戚同盟。",
        "triggerHint": "大族林立下由王室与公卿共议国政。",
        "suggestedDecrees": ("任命官吏", "推行郡县"),
    },
    {
        "id": DecisionStructure.AUTOCRACY.value,
        "name": "王权独断专制",
        "summary": "最高君主集中兵刑决断之权，令出必行，宜慎防精英离心。",
        "triggerHint": "王权强化阶段，可凭权威统合礼制与政令。",
        "suggestedDecrees": ("宣扬天命", "整肃权贵"),
    },
    {
        "id": DecisionStructure.BUREAUCRACY.value,
        "name": "郡县官僚体系",
        "summary": "按律令与考课任免流官治理地方，突破血缘束缚与疆域治理瓶颈。",
        "triggerHint": "官僚化 ≥ 52% 时施行「推行郡县」可正式确立郡县官僚制。",
        "suggestedDecrees": ("推行郡县", "编纂律令", "任命官吏"),
    },
)

TAX_NODES: tuple[dict[str, Any], ...] = (
    {
        "id": SurplusExtraction.TRIBUTE.value,
        "name": "纳贡征役",
        "summary": "依属邦与宗室分封按季纳贡并征发力役。",
        "triggerHint": "早期核心征发方式，与「分封诸侯」「巡狩四方」相契。",
        "suggestedDecrees": ("调整贡赋", "巡狩四方"),
    },
    {
        "id": SurplusExtraction.TAX_IN_KIND.value,
        "name": "实物田赋",
        "summary": "按田亩与收成征敛谷帛实物入官仓。",
        "triggerHint": "推行「调整贡赋」或以粮仓收储稳固实物赋税。",
        "suggestedDecrees": ("调整贡赋", "修建粮仓"),
    },
    {
        "id": SurplusExtraction.TAX_MONETARY.value,
        "name": "货币赋税",
        "summary": "以铸币计征赋税，降低远途转运损耗并激活国库周转。",
        "triggerHint": "施行「铸造货币」后正式增开货币赋税。",
        "suggestedDecrees": ("铸造货币", "调整贡赋"),
    },
    {
        "id": SurplusExtraction.COMMERCIAL_TAX.value,
        "name": "工商关税",
        "summary": "向市集行商与关隘贸易抽取商税，扩充非农财政来源。",
        "triggerHint": "施行「开设市集」后可增开工商税源。",
        "suggestedDecrees": ("开设市集", "引进异域技艺"),
    },
)


def _node_by_id(collection: tuple[dict[str, Any], ...], node_id: str) -> dict[str, Any] | None:
    for item in collection:
        if item["id"] == node_id:
            return item
    return None


def _eval_tech_node(
    node_spec: dict[str, Any],
    branch_spec: dict[str, Any],
    state: CivState,
    visited_techs: set[str],
    next_assigned: bool,
) -> tuple[dict[str, Any], bool]:
    reqs_out: list[dict[str, Any]] = []
    ratios: list[float] = []
    all_met = True
    for metric_key, target in node_spec["reqs"]:
        label, getter, fmt = _METRICS[metric_key]
        cur = getter(state)
        met = cur >= target - 1e-9
        if not met:
            all_met = False
        ratio = min(1.0, max(0.0, cur / target)) if target > 0 else 1.0
        ratios.append(ratio)
        reqs_out.append(
            {
                "key": metric_key,
                "label": label,
                "current": round(cur, 3),
                "target": target,
                "currentText": fmt(cur),
                "targetText": fmt(target),
                "met": met,
                "ratio": round(ratio, 4),
            }
        )

    unlocked = all_met or (node_spec["id"] in visited_techs)
    if unlocked:
        status = "unlocked"
        progress = 100
    elif not next_assigned:
        status = "next"
        next_assigned = True
        raw_pct = round(sum(ratios) / len(ratios) * 100) if ratios else 0
        progress = min(99, raw_pct)
    else:
        status = "locked"
        raw_pct = round(sum(ratios) / len(ratios) * 100) if ratios else 0
        progress = min(99, raw_pct)

    return (
        {
            "id": node_spec["id"],
            "branchId": branch_spec["id"],
            "branchName": branch_spec["name"],
            "stage": node_spec["stage"],
            "era": node_spec["era"],
            "name": node_spec["name"],
            "subtitle": node_spec["subtitle"],
            "art": node_spec["art"],
            "effect": node_spec["effect"],
            "chronicleNote": node_spec["chronicleNote"],
            "status": status,
            "unlocked": unlocked,
            "progress": progress,
            "reqs": reqs_out,
            "suggestedDecrees": list(node_spec["suggestedDecrees"]),
        },
        next_assigned,
    )


def _eval_institution_list(
    specs: tuple[dict[str, Any], ...],
    active_ids: set[str],
    visited_ids: set[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for spec in specs:
        nid = spec["id"]
        is_active = nid in active_ids
        is_unlocked = is_active or (nid in visited_ids)
        status = "active" if is_active else ("unlocked" if is_unlocked else "locked")
        out.append(
            {
                "id": nid,
                "name": spec["name"],
                "summary": spec["summary"],
                "triggerHint": spec["triggerHint"],
                "suggestedDecrees": list(spec["suggestedDecrees"]),
                "active": is_active,
                "unlocked": is_unlocked,
                "status": status,
            }
        )
    return out


def detect_turn_unlocks(
    before: CivState | None,
    after: CivState,
    *,
    visited_techs: Iterable[str] = (),
    visited_lands: Iterable[str] = (),
    visited_polities: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """对比回合前后状态，检测本回合新解锁的技艺节点、田制更易、政体演进与新征发税制。"""
    if before is None:
        return []

    seen_techs = set(visited_techs)
    seen_lands = set(visited_lands) | {before.land_system.value}
    seen_polities = set(visited_polities) | {before.polity.decision_structure.value}
    unlocks: list[dict[str, Any]] = []

    for branch in TECH_BRANCHES:
        for node_spec in branch["nodes"]:
            nid = node_spec["id"]
            if nid in seen_techs:
                continue
            before_node, _ = _eval_tech_node(node_spec, branch, before, set(), False)
            after_node, _ = _eval_tech_node(node_spec, branch, after, set(), False)
            if not before_node["unlocked"] and after_node["unlocked"]:
                unlocks.append(
                    {
                        "id": nid,
                        "targetNodeId": nid,
                        "kind": "tech",
                        "kindLabel": "天工新脉",
                        "branchId": branch["id"],
                        "branchName": branch["name"],
                        "name": node_spec["name"],
                        "subtitle": node_spec["subtitle"],
                        "art": node_spec["art"],
                        "effect": node_spec["effect"],
                    }
                )

    new_land = after.land_system.value
    if new_land != before.land_system.value and new_land not in seen_lands:
        spec = _node_by_id(LAND_NODES, new_land)
        if spec:
            unlocks.append(
                {
                    "id": f"land:{new_land}",
                    "targetNodeId": new_land,
                    "kind": "land",
                    "kindLabel": "田制更易",
                    "branchName": "田制演进",
                    "name": spec["name"],
                    "subtitle": "生产关系跃迁",
                    "art": "",
                    "effect": spec["summary"],
                }
            )

    new_polity = after.polity.decision_structure.value
    if new_polity != before.polity.decision_structure.value and new_polity not in seen_polities:
        spec = _node_by_id(POLITY_NODES, new_polity)
        if spec:
            unlocks.append(
                {
                    "id": f"polity:{new_polity}",
                    "targetNodeId": new_polity,
                    "kind": "polity",
                    "kindLabel": "政体演进",
                    "branchName": "中枢政体",
                    "name": spec["name"],
                    "subtitle": "中枢改制",
                    "art": "",
                    "effect": spec["summary"],
                }
            )

    before_taxes = {t.value for t in before.surplus_extraction}
    for tax in after.surplus_extraction:
        if tax.value not in before_taxes:
            spec = _node_by_id(TAX_NODES, tax.value)
            if spec:
                unlocks.append(
                    {
                        "id": f"tax:{tax.value}",
                        "targetNodeId": tax.value,
                        "kind": "tax",
                        "kindLabel": "新开征发",
                        "branchName": "赋役征发",
                        "name": spec["name"],
                        "subtitle": "财用新制",
                        "art": "",
                        "effect": spec["summary"],
                    }
                )

    return unlocks


def evaluate_progression(
    state: CivState,
    prev_state: CivState | None = None,
    *,
    visited_lands: Iterable[str] = (),
    visited_polities: Iterable[str] = (),
    visited_techs: Iterable[str] = (),
    recent_unlocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """生成完整的天工图谱（3×5 科技节点 + 田制/政体/赋役制度演进 + 本回合新解锁）。"""
    seen_techs = set(visited_techs)
    seen_lands = set(visited_lands) | {state.land_system.value}
    seen_polities = set(visited_polities) | {state.polity.decision_structure.value}
    if prev_state is not None:
        seen_lands.add(prev_state.land_system.value)
        seen_polities.add(prev_state.polity.decision_structure.value)

    branches_out: list[dict[str, Any]] = []
    unlocked_total = 0
    total_nodes = 0
    focus_candidate: str | None = None

    for branch in TECH_BRANCHES:
        nodes_out: list[dict[str, Any]] = []
        next_assigned = False
        branch_unlocked = 0
        for node_spec in branch["nodes"]:
            node_eval, next_assigned = _eval_tech_node(
                node_spec,
                branch,
                state,
                seen_techs,
                next_assigned,
            )
            if node_eval["unlocked"]:
                branch_unlocked += 1
            elif node_eval["status"] == "next" and focus_candidate is None:
                focus_candidate = node_eval["id"]
            nodes_out.append(node_eval)
            total_nodes += 1

        unlocked_total += branch_unlocked
        _, getter, fmt = _METRICS[branch["metricKey"]]
        level = getter(state)
        branches_out.append(
            {
                "id": branch["id"],
                "name": branch["name"],
                "metricKey": branch["metricKey"],
                "accent": branch["accent"],
                "level": round(level, 2),
                "levelText": fmt(level),
                "unlockedCount": branch_unlocked,
                "totalCount": len(nodes_out),
                "nodes": nodes_out,
            }
        )

    if recent_unlocks is None:
        recent = detect_turn_unlocks(
            prev_state,
            state,
            visited_techs=seen_techs,
            visited_lands={state.land_system.value},
            visited_polities={state.polity.decision_structure.value},
        )
    else:
        recent = recent_unlocks

    focus_id = (
        recent[0]["targetNodeId"]
        if recent
        else (focus_candidate or branches_out[0]["nodes"][0]["id"])
    )

    land_active = {state.land_system.value}
    polity_active = {state.polity.decision_structure.value}
    tax_active = {t.value for t in state.surplus_extraction}

    return {
        "unlockedCount": unlocked_total,
        "totalNodes": total_nodes,
        "focusNodeId": focus_id,
        "recentUnlocks": recent,
        "branches": branches_out,
        "institutions": {
            "land": {
                "title": "田制演进",
                "currentId": state.land_system.value,
                "nodes": _eval_institution_list(LAND_NODES, land_active, seen_lands),
            },
            "polity": {
                "title": "中枢政体",
                "currentId": state.polity.decision_structure.value,
                "nodes": _eval_institution_list(POLITY_NODES, polity_active, seen_polities),
            },
            "tax": {
                "title": "赋役征发",
                "activeIds": [t.value for t in state.surplus_extraction],
                "nodes": _eval_institution_list(TAX_NODES, tax_active, tax_active),
            },
        },
    }
