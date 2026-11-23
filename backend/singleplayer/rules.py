"""Single-player decree vocabulary, varied literary chronicle, deep state & archive consultation."""

from __future__ import annotations

import random
import re
from typing import Any

from backend.engine.action_resolver import (
    FullTurnResult,
    estimate_class_tension,
    estimate_elite_cohesion,
    resolve_prepared_turn,
)
from backend.engine.food import calculate_food_surplus_from_state
from backend.engine.governance import governance_efficiency_from_state
from backend.llm.intent_parser import IntentResult, Prerequisites
from backend.llm.task_splitter import MAX_SUBTASKS, SubTask, TaskSplitResult
from backend.models.schemas import ActionResultTier, CivState
from backend.templates.actions import (
    ALL_ACTIONS,
    DOMAIN_LABELS,
    ActionDef,
    check_prerequisites,
    explain_unmet_prerequisites,
    generate_full_action_catalog,
)
from backend.templates.civilizations import CIVILIZATION_TEMPLATES

OPENINGS = {
    "zhou": "宗周初定，四方贡赋沿驿道入朝。渭水两岸的田地等着引渠，仓吏和匠人都在等你的第一道政令。",
    "egypt": "尼罗河的洪水退去，测田人重新立起界石。要让下一季的谷物进入粮仓，王廷须先决定如何使用民力。",
    "sumer": "幼发拉底河的支渠穿过城邦。神庙掌管粮秣，各城各有田界。先从一项能聚集人心的政事做起。",
    "harappa": "城门内，秤砣和砖块各有定制。商旅备舟，农人候雨，议事者等着今日的决定。",
    "babylon": "河渠把村庄连到巴比伦的市场。抄写员摊开泥板，记下新的王令以及它将如何改变这座城。",
    "greece": "海湾之间散布着城邦。田地有限，商船将至，广场上的议事者正等候今日的提案。",
}

# 完整开放全部 28 项标准政令及常见自然语言同义表达
ALIASES: dict[str, tuple[str, ...]] = {
    # 经济 (6)
    "econ_irrigation": ("修渠", "挖渠", "开渠", "修水利", "疏浚水渠", "修建水渠", "治水", "兴修水渠"),
    "econ_granary": ("建仓", "建粮仓", "建造粮仓", "修仓", "建仓储粮", "储粮", "设常平仓", "积谷备荒"),
    "econ_reclaim": ("垦荒", "开荒", "扩耕", "开垦农田", "辟田", "招民垦荒", "屯田开荒"),
    "econ_market": ("开市", "设市", "兴办集市", "开设集市", "通商", "鼓励商贸", "开放坊市"),
    "econ_tribute": ("整顿贡赋", "改定贡赋", "核定赋税", "清查赋税", "厘定贡赋", "改革税制"),
    "econ_currency": ("铸币", "统一铸币", "统一货币", "发行铸币", "铸行铜钱"),
    # 政治 (5)
    "pol_appoint": ("选官", "任官", "任命官员", "整顿吏治", "考课百官", "选任守令"),
    "pol_code": ("修律", "立法", "制定律法", "颁布律令", "明定刑律", "编修法典"),
    "pol_enfeoff": ("分封", "封建诸侯", "册封诸侯", "裂土分封", "分封宗亲"),
    "pol_prefecture": ("设郡县", "废分封", "改行郡县", "置郡县", "推行郡县制", "中央集权变法"),
    "pol_purge": ("裁抑豪强", "打击豪强", "整肃贵族", "削藩", "抑制兼并", "罢黜权贵"),
    # 军事 (6)
    "mil_drill": ("练兵", "阅兵", "训练军队", "校阅甲士", "整训军伍", "讲武"),
    "mil_walls": ("筑城", "修城", "修筑城墙", "加固城防", "深沟高垒", "营建城池"),
    "mil_arms": ("造兵器", "锻造甲兵", "扩充军备", "督造器械", "冶铸兵器"),
    "mil_standing": ("募兵", "组建常备军", "设常备军", "整编禁军", "养兵"),
    "mil_campaign": ("出征", "北伐", "东征", "西讨", "南征", "拓边", "经略边疆", "远征边地"),
    "mil_suppress": ("平叛", "剿匪", "讨平叛乱", "发兵平乱", "弹压地方"),
    # 文化 (5)
    "cul_school": ("办学", "设学", "建学宫", "兴办学宫", "兴学", "广设庠序"),
    "cul_ritual": ("祭祀", "祭天", "祭祖", "郊祭", "举行祭典", "大祀天地"),
    "cul_mandate": ("昭告天命", "宣示正统", "布告天下", "明定正朔"),
    "cul_temple": ("建宗庙", "修宗庙", "营建太庙", "立社稷坛"),
    "cul_canon": ("修史", "编修典籍", "整理古籍", "修纂国史", "校定经籍"),
    # 科技 (4)
    "tech_farm": ("改良农具", "改进耕具", "推广铁农具", "改良耒耜", "推广耕作新法"),
    "tech_engineer": ("研制器械", "钻研工巧", "召集工匠", "精研营造", "改良土木"),
    "tech_scholars": ("招贤", "招揽学者", "礼聘贤士", "延纳策士", "养士"),
    "tech_import": ("引进奇技", "博采异域工艺", "遣使求艺", "引入外来技艺"),
    # 综合 (2)
    "comp_tour": ("巡狩", "巡视地方", "东巡", "南巡", "省方问俗", "巡察州郡"),
    "comp_relief": ("赈灾", "赈济", "开仓赈济", "开仓放粮", "抚恤流民", "平粜救荒"),
}

DECREES: dict[str, ActionDef] = {a.id: a for a in ALL_ACTIONS if a.id in ALIASES}

LAND_LABELS = {
    "clan_communal": "氏族公田",
    "noble_estate": "贵族采邑",
    "state_grant": "国有授田",
    "landlord_tenant": "地主租佃",
    "yeoman_smallhold": "自耕小农",
}
AUTHORITY_SRC_LABELS = {
    "bloodline": "宗法血统",
    "military": "军功威权",
    "election": "公议推举",
    "theocratic": "神权天授",
}
DECISION_LABELS = {
    "autocracy": "王廷独断",
    "oligarchy": "贵胄合议",
    "council": "公民议事会",
    "bureaucracy": "百官考课",
}
SUCCESSION_LABELS = {
    "hereditary": "世袭罔替",
    "abdication": "推贤禅让",
    "election": "议会推选",
    "military_coup": "兵权更迭",
}
EXTRACTION_LABELS = {
    "tribute": "方物贡赋",
    "tax_in_kind": "实物田租",
    "tax_monetary": "折钱货币税",
    "commercial_tax": "关市商税",
}
TIER_LABELS: dict[ActionResultTier, tuple[str, str]] = {
    ActionResultTier.GREAT_SUCCESS: ("great", "大成"),
    ActionResultTier.SUCCESS: ("success", "顺遂"),
    ActionResultTier.PARTIAL: ("partial", "功半"),
    ActionResultTier.FAILURE: ("failure", "未果"),
    ActionResultTier.DISASTER: ("disaster", "偾事"),
}
SCALE_LABELS = {
    "small": "试办",
    "medium": "常制",
    "large": "举国",
}

# 按「领域 × 档位」提供多套白话史笔模板（由回合种子确定性轮换，彻底告别单句复读）
DOMAIN_TIER_NOTES: dict[str, dict[ActionResultTier, tuple[str, ...]]] = {
    "economic": {
        ActionResultTier.GREAT_SUCCESS: (
            "乡遂民夫踊跃赴工，田畴与仓廪气象一新，收效远超朝议预期",
            "水道与阡陌次第贯通，有司调度井然，当年便见粮秣充盈之象",
            "官民合力兴办农商，沿途舟车辐辏，府库积贮大增",
        ),
        ActionResultTier.SUCCESS: (
            "诸司依令督办，农桑与积贮稳步推进，民间生计渐见宽裕",
            "工役按农隙分期施行，不夺民时，所期实利已入官仓",
            "地方守令奉诏兴作，田亩与坊市秩序井然，国用有所增益",
        ),
        ActionResultTier.PARTIAL: (
            "近畿州县尚能奉行，远地因人力与器物掣肘，只收到半数成效",
            "政令虽下，然胥吏折耗、豪右观望，工程与实利皆打了几分折扣",
            "前段督办颇紧，入秋后民力渐疲，仅完结要冲数处",
        ),
        ActionResultTier.FAILURE: (
            "州郡互相推诿，征发失度而工料不继，终未见尺寸之功",
            "地方吏治懈怠，文书往返空耗岁时，原议之事中途搁浅",
        ),
        ActionResultTier.DISASTER: (
            "强征民夫失其农时，工地溃散、胥吏舞弊，反致闾里怨声四起",
            "调度乖方而耗费巨万，非但未得寸利，更令民间元气受损",
        ),
    },
    "political": {
        ActionResultTier.GREAT_SUCCESS: (
            "朝纲一振，诏令自王畿直达边邑，旧族敛迹而政事大通",
            "新制颁行天下，选任得人、章程分明，内外威权显著凝聚",
        ),
        ActionResultTier.SUCCESS: (
            "有司奉诏整饬纲纪，职守渐明，政令下行较往昔顺畅",
            "朝堂议定章程并付有司施行，地方观望之风有所收敛",
        ),
        ActionResultTier.PARTIAL: (
            "王城左近已依新制改易，但外藩旧族阳奉阴违，新旧之争尚存",
            "折冲樽俎之间互有退让，法度虽立而执行仍有参差",
        ),
        ActionResultTier.FAILURE: (
            "既得利益盘根错节，廷议纷纭难决，新令悬于城门而未能落地",
            "地方豪族联名陈情阻挠，政令行至半途便无疾而终",
        ),
        ActionResultTier.DISASTER: (
            "操切生变，朝野猜忌骤起，不仅新政顿挫，更伤及中枢威信",
            "新旧权贵借机倾轧，政局动荡，州郡号令一时紊乱",
        ),
    },
    "military": {
        ActionResultTier.GREAT_SUCCESS: (
            "旌旗整肃、甲仗精良，将士用命而捷报频传，四裔震慑",
            "军政调度神速，戍卫与拓边一举功成，军威大振",
        ),
        ActionResultTier.SUCCESS: (
            "营伍依期整训、守备渐固，朝廷折冲御侮之势得以夯实",
            "师出有律、粮道无虞，按期达成军略部署",
        ),
        ActionResultTier.PARTIAL: (
            "军务虽有所展布，然粮秣与甲仗供应吃紧，只收局部尺寸之效",
            "近畿营伍尚能依限奉行，远镇因转输与调度掣肘，仅成半数之功",
        ),
        ActionResultTier.FAILURE: (
            "调度失期而粮械不继，军务迁延日久，终未能达成原议",
            "将校号令不一、士卒疲敝，徒耗府库粮饷而未见实效",
        ),
        ActionResultTier.DISASTER: (
            "急征暴敛激起营伍哗变，军资折损殆尽，讯息传回令朝野震恐",
            "措置乖方以致师溃备弛，非但军略受挫，更令国威受损",
        ),
    },
    "cultural": {
        ActionResultTier.GREAT_SUCCESS: (
            "礼乐大备、弦歌相闻，四方士庶归心，王朝正统愈发稳固",
            "泮宫讲诵不绝，典章礼仪焕然可观，朝野风气为之一清",
        ),
        ActionResultTier.SUCCESS: (
            "礼官与博士依制行事，教化渐敷，人心渐趋安定",
            "仪典庄重、文教渐兴，识字知礼之士日见增多",
        ),
        ActionResultTier.PARTIAL: (
            "都邑之内礼教颇兴，然乡野僻远之地仍循旧俗，化俗尚需时日",
            "学舍与仪制初具规模，唯经费与师儒有限，收效徐缓",
        ),
        ActionResultTier.FAILURE: (
            "虚文浮礼流于表面，士人空谈而民间漠然，未收化民之效",
        ),
        ActionResultTier.DISASTER: (
            "靡费太甚以致劳民伤财，非但未能聚拢人心，反惹街谈巷议讥评",
        ),
    },
    "technology": {
        ActionResultTier.GREAT_SUCCESS: (
            "百工巧思竞发，新器良法迅速推行州郡，生产营造效率大进",
            "匠作局与民间巧匠互相砥砺，器用一新，远近争相仿效",
        ),
        ActionResultTier.SUCCESS: (
            "考工试制颇有斩获，改良器物渐次配发有司，技艺稳步精进",
            "工师潜心研习，新法试行有效，农工诸业渐得其利",
        ),
        ActionResultTier.PARTIAL: (
            "官坊虽制出良器，但铜铁与熟匠紧缺，眼下仅能小范围试用",
            "新法略见端倪，然民间墨守旧习，推广颇费周章",
        ),
        ActionResultTier.FAILURE: (
            "试制屡屡受挫，匠人散佚而器用粗疏，终未能堪大用",
        ),
        ActionResultTier.DISASTER: (
            "耗竭工料而强推未熟之法，器毁工伤，徒增府库亏空",
        ),
    },
    "composite": {
        ActionResultTier.GREAT_SUCCESS: (
            "皇华所至、恩威并济，流亡复业而欢声载道，上下隔阂大为消融",
            "抚恤与整饬双管齐下，地方积弊一扫，民心大定",
        ),
        ActionResultTier.SUCCESS: (
            "使者奉诏体察民隐、及时施政，地方紧绷之势明显缓和",
            "有司按章抚绥安辑，闾里重归安宁",
        ),
        ActionResultTier.PARTIAL: (
            "近处灾黎与郡县已得安抚，偏远山泽因道阻吏疲，恩泽尚未尽达",
            "虽解燃眉之急，然官仓与人手吃紧，善后尚留尾闾",
        ),
        ActionResultTier.FAILURE: (
            "层层盘剥之下实惠未及百姓，诏书虽美而民怨未平",
        ),
        ActionResultTier.DISASTER: (
            "赈抚失序、胥吏侵吞，饥民聚众哗变，局势反倒愈发棘手",
        ),
    },
}


def catalog(state: CivState | None = None) -> dict[str, Any]:
    ref_state = state or CIVILIZATION_TEMPLATES["zhou"]
    return {
        "templates": [
            {"id": k, "name": s.civ_name, "description": OPENINGS[k]}
            for k, s in CIVILIZATION_TEMPLATES.items()
        ],
        "decrees": generate_full_action_catalog(ref_state),
    }


def _clamp01(val: float) -> float:
    return round(min(1.0, max(0.0, val)), 3)


def statistics(s: CivState, prev: CivState | None = None) -> list[dict[str, Any]]:
    food = calculate_food_surplus_from_state(s)
    specs = [
        ("population", "人口", round(s.population, 2), "人", _clamp01(s.population / 180000), False),
        ("stability", "稳定", round(s.stability, 2), "点", _clamp01(s.stability / 100), s.stability < 35),
        ("authority", "统治力", round(s.authority, 2), "点", _clamp01(s.authority / 100), s.authority < 25),
        ("food", "粮食供需比", round(food, 2), "倍", _clamp01(food / 2.0), food < 1.0),
        ("agriculture", "农业技术", round(s.tech_agriculture, 2), "级", _clamp01(s.tech_agriculture / 5.0), False),
        ("engineering", "工程技术", round(s.tech_engineering, 2), "级", _clamp01(s.tech_engineering / 5.0), False),
    ]
    prev_map = {item["id"]: item["value"] for item in statistics(prev)} if prev is not None else {}
    rows: list[dict[str, Any]] = []
    for key, label, val, unit, norm, warn in specs:
        row: dict[str, Any] = {
            "id": key,
            "label": label,
            "value": val,
            "unit": unit,
            "norm": norm,
        }
        if warn:
            row["warn"] = True
        if key in prev_map:
            old_val = prev_map[key]
            delta = round(val - old_val, 2)
            if delta != 0:
                row["before"] = old_val
                row["delta"] = delta
                row["good"] = delta > 0
        rows.append(row)
    return rows


def _polity_text(s: CivState) -> str:
    return " · ".join(
        (
            AUTHORITY_SRC_LABELS.get(s.polity.authority_source.value, s.polity.authority_source.value),
            DECISION_LABELS.get(s.polity.decision_structure.value, s.polity.decision_structure.value),
            SUCCESSION_LABELS.get(s.polity.succession.value, s.polity.succession.value),
        )
    )


def deep_panel(s: CivState, prev: CivState | None = None) -> dict[str, Any]:
    """输出深层制度、社会张力与底蕴数据（含相对上一回合的原位差值与极性）。"""
    ct = estimate_class_tension(s)
    ec = estimate_elite_cohesion(s)
    gov = governance_efficiency_from_state(s)
    polity_text = _polity_text(s)
    land_text = LAND_LABELS.get(s.land_system.value, s.land_system.value)

    ind_specs = [
        ("grain_reserve", "官仓储粮", round(s.grain_reserve, 2), "年", _clamp01(s.grain_reserve / 1.2), s.grain_reserve < 0.08, False),
        ("governance", "治理效率", round(gov * 100, 1), "%", _clamp01(gov), gov < 0.10, False),
        ("bureaucratization", "官僚化", round(s.bureaucratization * 100, 1), "%", _clamp01(s.bureaucratization), False, False),
        ("literacy", "识字率", round(s.literacy_rate() * 100, 1), "%", _clamp01(s.literacy_rate() / 0.5), False, False),
        ("knowledge", "知识技术", round(s.tech_knowledge, 2), "级", _clamp01(s.tech_knowledge / 5.0), False, False),
        ("class_tension", "阶级矛盾", round(ct * 100, 1), "%", _clamp01(ct), ct >= 0.65, True),
        ("elite_cohesion", "精英凝聚", round(ec * 100, 1), "%", _clamp01(ec), ec <= 0.25, False),
    ]

    prev_panel = deep_panel(prev) if prev is not None else None
    prev_ind = {item["id"]: item["value"] for item in prev_panel["indicators"]} if prev_panel else {}
    prev_acc = {item["id"]: item["value"] for item in prev_panel["accumulations"]} if prev_panel else {}

    indicators: list[dict[str, Any]] = []
    for key, label, val, unit, norm, warn, inverse in ind_specs:
        item: dict[str, Any] = {
            "id": key,
            "label": label,
            "value": val,
            "unit": unit,
            "norm": norm,
            "warn": warn,
        }
        if inverse:
            item["inverse"] = True
        if key in prev_ind:
            old_val = prev_ind[key]
            delta = round(val - old_val, 2)
            if delta != 0:
                item["before"] = old_val
                item["delta"] = delta
                item["good"] = (delta < 0) if inverse else (delta > 0)
        indicators.append(item)

    acc_specs = [
        ("academic", "学术", round(s.accumulations.academic, 2)),
        ("military", "军事", round(s.accumulations.military, 2)),
        ("commercial", "商业", round(s.accumulations.commercial, 2)),
        ("administrative", "行政", round(s.accumulations.administrative, 2)),
        ("cultural", "礼乐", round(s.accumulations.cultural, 2)),
    ]
    accumulations: list[dict[str, Any]] = []
    for key, label, val in acc_specs:
        acc_item: dict[str, Any] = {"id": key, "label": label, "value": val}
        if key in prev_acc:
            old_val = prev_acc[key]
            delta = round(val - old_val, 2)
            if delta != 0:
                acc_item["before"] = old_val
                acc_item["delta"] = delta
                acc_item["good"] = delta > 0
        accumulations.append(acc_item)

    total_terr = s.territory_core + s.territory_frontier
    structure: dict[str, Any] = {
        "territoryCore": s.territory_core,
        "territoryFrontier": s.territory_frontier,
        "territoryTotal": total_terr,
        "landSystem": land_text,
        "polity": polity_text,
        "extractions": [
            EXTRACTION_LABELS.get(item.value, item.value)
            for item in s.surplus_extraction
        ],
        "labor": [
            {"label": "自由民", "pct": round(s.labor_distribution.free_citizens * 100)},
            {"label": "徭役", "pct": round(s.labor_distribution.corvee * 100)},
            {"label": "农奴", "pct": round(s.labor_distribution.serf * 100)},
            {"label": "奴隶", "pct": round(s.labor_distribution.slave * 100)},
        ],
    }
    if prev is not None:
        prev_terr = prev.territory_core + prev.territory_frontier
        if total_terr != prev_terr:
            structure["territoryBefore"] = prev_terr
            structure["territoryDelta"] = total_terr - prev_terr
        prev_land = LAND_LABELS.get(prev.land_system.value, prev.land_system.value)
        if land_text != prev_land:
            structure["landSystemBefore"] = prev_land
        prev_pol = _polity_text(prev)
        if polity_text != prev_pol:
            structure["polityBefore"] = prev_pol

    return {
        "indicators": indicators,
        "structure": structure,
        "accumulations": accumulations,
    }


def turn_changes(before: CivState, after: CivState) -> list[dict[str, Any]]:
    """计算前后两轮的完整数值变动（含正负利弊极性与核心/深层分组）。"""
    changes: list[dict[str, Any]] = []
    for item in statistics(after, before):
        if "delta" in item:
            changes.append(
                {
                    "id": item["id"],
                    "label": "粮食供需比" if item["id"] == "food" else item["label"],
                    "unit": item["unit"],
                    "before": item["before"],
                    "after": item["value"],
                    "delta": item["delta"],
                    "good": item["good"],
                    "group": "core",
                }
            )
    panel = deep_panel(after, before)
    for ind in panel["indicators"]:
        if "delta" not in ind:
            continue
        is_core = ind["id"] == "grain_reserve"
        threshold = 0.01 if ind["unit"] in ("年", "级") else 0.1
        if abs(ind["delta"]) < threshold:
            continue
        changes.append(
            {
                "id": ind["id"],
                "label": ind["label"],
                "unit": ind["unit"],
                "before": ind["before"],
                "after": ind["value"],
                "delta": ind["delta"],
                "good": ind["good"],
                "group": "core" if is_core else "deep",
            }
        )
    struct = panel["structure"]
    if "territoryDelta" in struct:
        changes.append(
            {
                "id": "territory",
                "label": "版图",
                "unit": "km²",
                "before": struct["territoryBefore"],
                "after": struct["territoryTotal"],
                "delta": struct["territoryDelta"],
                "good": struct["territoryDelta"] > 0,
                "group": "core",
            }
        )
    for acc in panel["accumulations"]:
        # 仅在底蕴发生显著进益 (>= +0.02) 或实质折损 (<= -0.06，排除每轮自然微衰减) 时列入本轮变动要报
        if "delta" in acc and (acc["delta"] >= 0.02 or acc["delta"] <= -0.06):
            changes.append(
                {
                    "id": f"acc_{acc['id']}",
                    "label": f"{acc['label']}底蕴",
                    "unit": "",
                    "before": acc["before"],
                    "after": acc["value"],
                    "delta": acc["delta"],
                    "good": acc["good"],
                    "group": "deep",
                }
            )
    return changes


def turn_outcomes(result: FullTurnResult) -> list[dict[str, Any]]:
    """提取每项子政令的结算品阶，供前端展示清晰回执徽章。"""
    outcomes: list[dict[str, Any]] = []
    for sub in result.subtasks:
        if sub.result_tier is None:
            continue
        met = bool(sub.intent.prerequisites.met)
        if not met:
            tier_key, tier_cn = "blocked", "未备"
        else:
            tier_key, tier_cn = TIER_LABELS.get(sub.result_tier, ("partial", "已办"))
        scale_val = sub.intent.scale.value
        outcomes.append(
            {
                "name": sub.intent.action_type,
                "scale": scale_val,
                "scaleLabel": SCALE_LABELS.get(scale_val, "常制"),
                "tier": tier_key,
                "tierLabel": tier_cn,
                "met": met,
            }
        )
    return outcomes


def _suggest_similar(fragment: str) -> str:
    chars = set(fragment)
    scored: list[tuple[int, str]] = []
    for action_id, action in DECREES.items():
        pool = " ".join((action.name, action.description, *ALIASES[action_id]))
        overlap = sum(1 for ch in chars if ch in pool and ch.strip())
        if overlap > 0:
            scored.append((overlap, action.name))
    scored.sort(key=lambda item: (-item[0], item[1]))
    picks = [name for _, name in scored[:3]] or ["兴修水利", "开垦荒地", "操练士卒"]
    return "、".join(f"「{name}」" for name in picks)


def parse_local(text: str) -> tuple[list[tuple[ActionDef, str]], str | None]:
    """Restrict offline orders to affirmative, recognized commands. Unknown clauses never run."""
    if re.search(
        r"不|勿|莫|停止|暂停|取消|还是|或者|是否|为何|为什么|[?？]|(?:吗|么)[。！!]?\s*$",
        text,
    ):
        return [], "本地政令须指明要办的事项。请选定一道肯定的政令，例如「兴修水利」或「操练士卒」。"
    fragments = re.split(
        r"\s*(?:[、，,；;。\n]+|并且|然后|并|再|同时|以及|和|兼)\s*",
        text.strip(),
    )
    orders: list[tuple[ActionDef, str]] = []
    lookup = {
        name: a
        for k, a in DECREES.items()
        for name in (a.name, *ALIASES[k])
    }
    for fragment in filter(None, fragments):
        cleaned = re.sub(
            r"^(?:(?:今年|本年|下令|颁令|诏令|传令|决定|请|先|集中民力|组织民力|动员民力|命有司|着有司|只|要|在本地|在各地|于各地)\s*)+",
            "",
            fragment,
        )
        scale = "medium"
        for key, pattern in (
            ("large", r"^(?:大规模|举国|全面|全国|大举|倾国)"),
            ("small", r"^(?:小规模|试行|局部|先行试点|小幅)"),
        ):
            if re.match(pattern, cleaned):
                scale, cleaned = key, re.sub(pattern, "", cleaned).strip()
                break
        token = cleaned.strip(" ！!「」『』\"'")
        action = lookup.get(token)
        if not action:
            suggestions = _suggest_similar(token)
            return (
                [],
                f"本地史官尚未收录「{token[:18]}」这道政令。可试 {suggestions}，或展开政令面板从 28 项国策中选取；连接万相模型后可自由拟诏。",
            )
        if any(a.id == action.id for a, _ in orders):
            return [], "这一回合重复列出了同一事项，请保留一项并指明规模。"
        orders.append((action, scale))
    if not 1 <= len(orders) <= MAX_SUBTASKS:
        return [], f"请提出 1 至 {MAX_SUBTASKS} 项具体政令。"
    return orders, None


async def resolve_local(
    state: CivState, text: str, orders: list[tuple[ActionDef, str]], seed: int
) -> FullTurnResult:
    subtasks, parsed = [], []
    for i, (action, scale) in enumerate(orders, 1):
        task = SubTask(
            id=f"t{i}",
            description=action.description,
            original_fragment=action.name,
            priority=i,
        )
        subtasks.append(task)
        unmet = explain_unmet_prerequisites(action, state)
        met = len(unmet) == 0 and check_prerequisites(action, state)
        intent = IntentResult(
            action_domain=action.domain,
            action_type=action.name,
            action_description=action.description,
            cognitive_gap=action.cognitive_gap,
            scale=scale,
            time_estimate_years={"small": 1, "medium": 2, "large": 4}[scale],
            time_estimate_reasoning="按本地政令的动员规模计年",
            prerequisites=Prerequisites(
                met=met,
                details="具备所需条件" if met else "、".join(unmet) or "当前国势尚未达到政令前提",
            ),
        )
        parsed.append((task.id, action.name, intent))
    split = TaskSplitResult(
        is_multi_task=len(orders) > 1,
        subtasks=subtasks,
        split_reason="按明确的本地政令拆分",
    )
    return await resolve_prepared_turn(state, text, split, parsed, rng_seed=seed)


def chronicle(result: FullTurnResult) -> str:
    """生成有层次、随回合种子轮换意象的白话史官纪事。"""
    rng = random.Random(result.rng_seed ^ 0x5A17)
    segments: list[str] = []

    for idx, sub in enumerate(result.subtasks):
        if sub.result_tier is None:
            continue
        name = sub.intent.action_type
        if not sub.intent.prerequisites.met:
            reason = sub.intent.prerequisites.details or "国中条件未备"
            segments.append(f"{name}：因{reason}，有司无从措手，未能如期推行。")
            continue
        domain_key = sub.intent.action_domain.value
        pool = DOMAIN_TIER_NOTES.get(domain_key, DOMAIN_TIER_NOTES["composite"]).get(
            sub.result_tier,
            ("诸司依令办理。",),
        )
        chosen = pool[(result.rng_seed + idx * 7) % len(pool)]
        scale_prefix = {"small": "先行局部试办", "medium": "", "large": "举国大兴役作，"}[
            sub.intent.scale.value
        ]
        if scale_prefix:
            segments.append(f"{name}：{scale_prefix}{chosen}。")
        else:
            segments.append(f"{name}：{chosen}。")

    # 附加本轮制度演进与被动天灾/边患/丰年事件（过滤通用受益/阻力短句）
    for ev in result.events:
        if any(
            kw in ev
            for kw in ("从中得利", "阻挠政令", "遭遇", "略有反应", "茫然无措")
        ):
            continue
        segments.append(ev.rstrip("。") + "。")

    cap = result.capacity
    if cap and cap.dilution_factor < 0.999:
        segments.append(
            f"朝廷并举多事，共需 {cap.total_demand:.1f} 国力而本轮可调 {cap.available:.1f}，实效折为 {cap.dilution_factor:.0%}。"
        )

    before, after = result.state_before, result.state_after
    if after is not None:
        pop_diff = after.population - before.population
        pop_templates = (
            f"历时 {result.turn_years:g} 载，在册户口由 {before.population:,} 演至 {after.population:,}。",
            f"经 {result.turn_years:g} 年生聚调度，编户自 {before.population:,} 变为 {after.population:,}。",
            f"前后 {result.turn_years:g} 年间，国中丁口由 {before.population:,} 迁至 {after.population:,}。",
        )
        segments.append(pop_templates[rng.randrange(len(pop_templates))])

        ct = estimate_class_tension(after)
        ec = estimate_elite_cohesion(after)
        food_after = calculate_food_surplus_from_state(after)
        if cap and cap.dilution_factor < 0.85:
            segments.append("史臣按：政出多门则民力分薄，下轮宜择一二要务专力图之。")
        elif food_after < 0.98:
            segments.append("仓吏急报当季粮产尚不敷食，亟宜开垦荒地、兴修水利或改良耕具。")
        elif ct >= 0.68:
            segments.append("乡野贫富悬殊、怨气暗积，宜早施赈济、修明律令或裁抑兼并。")
        elif ec <= 0.24:
            segments.append("朝中宗室贵胄离心日显，宜借祭祀、巡狩或选官安抚中枢。")
        elif after.stability < 38:
            segments.append("四方人心未定，下轮施政当以安民休养为先。")
        elif pop_diff > 0 and after.grain_reserve >= 0.45 and rng.random() < 0.35:
            segments.append("常平仓廪渐实，朝野颇有余裕可图远略。")

    segments.extend(result.vague_prompts)
    return "".join(segments)


def consult_archive(question: str, state: CivState, history: list[dict[str, Any]]) -> str:
    """本地深度问史官：支持按回合查卷、跨回合趋势复盘、以及当前国势诊断。"""
    q = question.strip()
    if not history:
        return "史馆尚未录得本局记事。"

    m = re.search(r"第\s*(\d+)\s*(?:回合|轮)", q)
    if m:
        turn_no = int(m.group(1))
        entry = next((row for row in history if row.get("turn") == turn_no), None)
        if not entry:
            return f"当前史卷中尚无第 {turn_no} 回合的记录（本局现至第 {state.turn} 回合）。"
        changes = "、".join(
            f"{c['label']} {c['after'] - c['before']:+.2f}{c['unit']}"
            for c in entry.get("changes", [])[:5]
        )
        year = entry["year"]
        year_str = f"公元前 {abs(round(year))} 年" if year < 0 else f"公元 {round(year)} 年"
        return (
            f"{year_str}（{'开国' if turn_no == 0 else f'第 {turn_no} 回合'}），"
            f"政令「{entry.get('decree', '立国')}」：{entry.get('narrative', '')}"
            + (f" 当轮变动：{changes}。" if changes else "")
        )

    # 制度 / 疆域 / 社会张力专项提问优先匹配，避免被「如何」等通用疑问词截胡
    if any(kw in q for kw in ("制度", "田制", "土地", "政体", "赋税", "税")):
        panel = deep_panel(state)["structure"]
        taxes = "、".join(panel["extractions"])
        return (
            f"本朝现行「{panel['landSystem']}」，中枢体制为「{panel['polity']}」，"
            f"岁入仰赖{taxes}；官僚化 {state.bureaucratization:.0%}，识字率 {state.literacy_rate():.1%}。"
        )
    if any(kw in q for kw in ("疆域", "领土", "边疆", "版图")):
        gov = governance_efficiency_from_state(state)
        return (
            f"现辖核心畿甸 {state.territory_core:,} km²、边疆藩属 {state.territory_frontier:,} km²，"
            f"边疆治理传导效率 {gov:.0%}。"
        )
    if any(kw in q for kw in ("矛盾", "张力", "民怨", "豪强", "凝聚", "贵族")):
        ct = estimate_class_tension(state)
        ec = estimate_elite_cohesion(state)
        return (
            f"当前阶级矛盾 {ct:.0%}（>80% 且稳定低迷易酿大乱），"
            f"统治精英凝聚力 {ec:.0%}（<15% 易致中枢瓦解），官仓储粮 {state.grain_reserve:.2f} 年。"
        )

    # 诊断与施政建议类提问
    if any(kw in q for kw in ("建议", "隐忧", "局势", "国势", "怎么办", "下一步", "风险", "危机")):
        food = calculate_food_surplus_from_state(state)
        ct = estimate_class_tension(state)
        ec = estimate_elite_cohesion(state)
        gov = governance_efficiency_from_state(state)
        diagnoses: list[str] = []
        if food < 1.0:
            diagnoses.append(f"粮食供需比仅 {food:.2f} 倍（入不敷出），建议优先「开垦荒地」或「兴修水利」")
        else:
            diagnoses.append(f"粮食供需比 {food:.2f} 倍，官仓储粮可支 {state.grain_reserve:.2f} 年")
        if ct >= 0.60:
            diagnoses.append(f"阶级矛盾已升至 {ct:.0%}，有民变隐忧，宜「赈济饥民」「编纂律令」或「整肃权贵」")
        if ec <= 0.30:
            diagnoses.append(f"精英凝聚力偏低（{ec:.0%}），防备权贵瓦解，宜「举行大祭」「分封诸侯」或「巡狩四方」")
        if gov < 0.25 and state.territory_frontier > 300:
            diagnoses.append(f"边疆治理效率仅 {gov:.0%}，宜「任命官吏」「设立学宫」或「推行郡县」")
        if state.accumulations.military < 0.30 and state.territory_frontier >= 300:
            diagnoses.append("边防武备尚薄，农闲时可「操练士卒」「修筑城池」以备边患")
        return f"史官奏对（第 {state.turn} 回合）：" + "；".join(diagnoses) + "。"

    # 指标跨回合趋势查询
    stat_aliases = (
        ("food", ("粮食", "粮", "收成", "仓")),
        ("population", ("人口", "户口", "丁口")),
        ("stability", ("稳定", "民心", "治安")),
        ("authority", ("统治力", "统治", "王权", "威权")),
        ("agriculture", ("农业", "农具", "耕作")),
        ("engineering", ("工程", "营造", "器械")),
    )
    current_stats = {row["id"]: row for row in statistics(state)}
    for stat_id, keywords in stat_aliases:
        if any(kw in q for kw in keywords):
            cur = current_stats[stat_id]
            touches = []
            for item in history[-6:]:
                for ch in item.get("changes", []):
                    if ch["id"] == stat_id:
                        delta = ch["after"] - ch["before"]
                        touches.append(f"第{item['turn']}回合（{item['decree']}）{delta:+.2f}{cur['unit']}")
            extra = ""
            if stat_id == "food":
                extra = f"，官仓现储 {state.grain_reserve:.2f} 年口粮"
            trend_text = "；".join(touches[-4:]) if touches else "近几回合该项数值保持平稳"
            return f"{cur['label']}现为 {cur['value']:g}{cur['unit']}{extra}。近期轨迹：{trend_text}。"

    # 默认：汇总最近一至两回合国史要略
    latest = history[-1]
    year = latest["year"]
    year_str = f"公元前 {abs(round(year))} 年" if year < 0 else f"公元 {round(year)} 年"
    changes = "、".join(
        f"{c['label']} {c['after'] - c['before']:+.2f}{c['unit']}"
        for c in latest.get("changes", [])[:4]
    )
    return (
        f"{year_str}（{'开国' if latest['turn'] == 0 else f'第 {latest['turn']} 回合'}）："
        f"{latest['narrative']}" + (f" 国势变动：{changes}。" if changes else "")
    )
