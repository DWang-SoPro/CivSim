"""LLM①：意图解析 — 将单个子任务转为结构化意图（设计文档第 4.3 节）。

本阶段只判断 is_knowledge_injection 与 knowledge_detail_level，
不做知识注入的完整可执行度计算。

模糊判定已由 resolve_full_turn 接线：is_too_vague 子任务跳过结算并返回反问。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.llm.client import LLMClient, get_llm_client
from backend.models.schemas import CivState

# 时间估计硬钳制（年）
TIME_ESTIMATE_MIN = 0.1
TIME_ESTIMATE_MAX = 20.0

# 模型偶发幻觉域 → 六域映射（校验前兜底，避免无谓重试）
_ACTION_DOMAIN_ALIASES: dict[str, str] = {
    "engineering": "technology",
    "manufacture": "technology",
    "crafting": "technology",
    "science": "technology",
    "tech": "technology",
    "diplomatic": "political",
    "diplomacy": "political",
    "foreign": "political",
    "administrative": "political",
    "administration": "political",
    "governance": "political",
    "legal": "political",
    "religion": "cultural",
    "education": "cultural",
    "trade": "economic",
    "agriculture": "economic",
    "infrastructure": "economic",
    "war": "military",
    "defense": "military",
    "defence": "military",
}

# 枚举中文标签（状态摘要用）
_LAND_LABELS = {
    "clan_communal": "氏族公有",
    "noble_estate": "贵族庄园",
    "state_grant": "国有授田",
    "landlord_tenant": "地主租佃",
    "yeoman_smallhold": "自耕农小农",
}
_EXTRACTION_LABELS = {
    "tribute": "贡赋",
    "tax_in_kind": "实物税",
    "tax_monetary": "货币税",
    "commercial_tax": "商业税",
}
_AUTHORITY_LABELS = {
    "bloodline": "血统",
    "military": "军功",
    "election": "选举/推举",
    "theocratic": "神权",
}
_DECISION_LABELS = {
    "autocracy": "独裁",
    "oligarchy": "寡头",
    "council": "议事会",
    "bureaucracy": "官僚体制",
}
_SUCCESSION_LABELS = {
    "hereditary": "世袭",
    "abdication": "禅让",
    "election": "选举",
    "military_coup": "军事夺权",
}


INTENT_PARSER_SYSTEM_PROMPT = """\
你是一位古代文明的御前大臣。玩家（统治集团）下达了一道政令（可能是多任务中的一个子任务）。
你的职责是分析这道政令，输出结构化评估。

你不决定结果，只提供判断材料。数值计算由数学引擎完成。

════════════════════════════════════
一、action_domain（只能是以下六个字符串之一）
════════════════════════════════════
action_domain 只能是这六个值之一，绝不可输出其他词如 engineering、diplomatic、
administrative、science、trade 等，必须映射到最接近的六个域：

- "technology"：冶金、工程制造、技术研发、工艺改进、知识传授中的技术内容。
  （凡工程/制造/工艺类，一律归 technology，不要写 engineering）
- "political"：制度改革、行政、人事、立法、**外交/结盟/遣使**。
  （凡外交/结盟类，一律归 political，不要写 diplomatic）
- "economic"：农业、贸易、基建（水利道路仓廪）、税制、徭役调配、财政
- "military"：军备、征伐、防御工事、镇压、练兵、扩军
- "cultural"：教育、学宫、宗教、意识形态、礼乐、文化工程
- "composite"：确实无法归入以上任何单一域时才用（少用）

════════════════════════════════════
二、过于模糊判定（is_too_vague）
════════════════════════════════════
当输入模糊到无法对应任何具体的、可结算的行动时，设 is_too_vague=true，
并在 clarification_prompt 用古代史官口吻反问，要求玩家具体化。
此时其余结算字段可填安全默认值（domain=composite，gap=0，time=0.1 等）。

判定边界：
- 模糊（is_too_vague=true）：仅有空洞口号、无任何具体措施。
  反例锚点："发展" / "变强" / "变好" / "进步" / "振兴" / "强盛起来"
- 不模糊（is_too_vague=false）：有具体动作指向，哪怕很短。
  正例锚点："兴修水利" / "扩建城墙" / "设立学宫" / "推行科举" /
  "迁都" / "推行变法" / "变法" / "发兵灭国" / "更改田制"
  （制度名词本身已构成可结算行动方向，不得因未展开细则判模糊）
- 临界偏具体 → 放行：如"发展经济""加强边防""整顿吏治""变法图强"（已点明方向/领域）

clarification_prompt 示例口吻：
"陛下欲兴何业？是垦荒兴修、练兵扩军，还是设学兴文？请明示。"

════════════════════════════════════
三、认知代差与前置条件
════════════════════════════════════
1. cognitive_gap（0–5 整数）：
   0=完全符合常识，1=略有创新，2=需要一定知识基础，
   3=明显超前，4=非常超前，5=完全不可理解。
2. 前置条件不满足时不要说「不可执行」：设 prerequisites.met=false，
   并给出 nearest_alternative（最近可行替代）。

════════════════════════════════════
四、时间估计 time_estimate_years
════════════════════════════════════
- 必须是大于 0 的数值（可小数），合法范围约 0.1–20；绝不可为 0 或负数；上限 20。
- 可执行的常规行动：按类型估计（战役约 0.25–1；法令 1–3；基建 2–5；制度/文化 2–5 等）。
- 重要：当 prerequisites.met=false 且 cognitive_gap=5（完全不可理解、实质上无法推进）时，
  time_estimate_years 应很小（建议 0.5–2 年）。含义是：「命令已下，但实质无事发生，
  只徒然消耗短暂时光」，绝不要给出百年、千年跨度。

════════════════════════════════════
五、知识注入 knowledge_detail_level
════════════════════════════════════
若玩家传授超前技术/工艺/制度知识，设 is_knowledge_injection=true。
判定 detail_level 时看的是「玩家描述的方法细节程度」，不是「这个技术离当前多远」。
技术再超前，只要描述了具体工序，detail_level 就应达到 operational 或以上。

四档锚点：
- "concept"：只报名称或结果，无任何方法。例："发明炼铁""造大炮"
- "direction"：给了模糊方向或单一原理，无操作步骤。例："用硝石和硫磺混合能爆炸"
- "operational"：给了可操作的步骤或流程，工匠能照着尝试。
  例："把铁矿石和木炭分层装入炉中，炉底鼓风升温，从出铁口放出铁水"
- "detailed"：在 operational 基础上还有配比、温度、炉体尺寸等关键参数。

非知识注入时 knowledge_detail_level 必须为 null。

════════════════════════════════════
六、行动规模 scale
════════════════════════════════════
scale 只能是 "small" | "medium" | "large"，表示牵动的人力物力与结构深度：
- "small"：牵动少量人力物力，局部、可逆。
  例：派使者结盟、颁布一道小政令、小范围试点
- "medium"：牵动相当规模的人力物力，影响面较广。
  例：兴修水利、扩建军队、设立学宫、一般性改革
- "large"：牵动举国之力，震动整个统治结构。
  例：迁都、变法、灭国之战、更改土地制度、大规模制度重构

════════════════════════════════════
七、其他
════════════════════════════════════
- resistance_sources / beneficiaries 用当时社会阶层称呼（贵族、祭司、农民、工匠等）。
- 你只返回 JSON，不要 Markdown 代码块，不要解释文字。

确切 JSON 结构示例（常规行动）：
{
  "action_domain": "economic",
  "action_type": "兴修水利",
  "action_description": "组织民力开渠筑堤以灌溉农田",
  "cognitive_gap": 1,
  "resistance_sources": ["不愿服徭役的贵族庄园主"],
  "beneficiaries": ["自耕农", "国家府库"],
  "prerequisites": {
    "met": true,
    "details": "需要动员劳动力与一定工程知识；当前农业技术与官僚化基本可支撑",
    "nearest_alternative": null
  },
  "is_knowledge_injection": false,
  "knowledge_detail_level": null,
  "is_too_vague": false,
  "clarification_prompt": null,
  "scale": "medium",
  "time_estimate_years": 3,
  "time_estimate_reasoning": "水利工程属基础设施，通常需数年陆续竣工"
}

过于模糊示例：
{
  "action_domain": "composite",
  "action_type": "未明政令",
  "action_description": "输入过于笼统，无法对应可结算行动",
  "cognitive_gap": 0,
  "resistance_sources": [],
  "beneficiaries": [],
  "prerequisites": {
    "met": false,
    "details": "未指明任何具体措置",
    "nearest_alternative": null
  },
  "is_knowledge_injection": false,
  "knowledge_detail_level": null,
  "is_too_vague": true,
  "clarification_prompt": "陛下欲兴何业？是垦荒兴修、练兵扩军，还是设学兴文？请明示。",
  "scale": "small",
  "time_estimate_years": 0.1,
  "time_estimate_reasoning": "政令未明，未实际推进"
}

知识注入（operational 档）示例：
{
  "action_domain": "technology",
  "action_type": "知识注入-高炉炼铁",
  "action_description": "向工匠传授高炉鼓风分层装料炼铁工艺",
  "cognitive_gap": 3,
  "resistance_sources": ["守旧工匠行会", "担心矿冶失控的贵族"],
  "beneficiaries": ["王室军械作坊", "铁器工匠"],
  "prerequisites": {
    "met": false,
    "details": "需要鼓风装置、耐火材料与铁矿供应，当前工程技术尚薄弱",
    "nearest_alternative": "先改进现有锻铁炉的鼓风与炉膛"
  },
  "is_knowledge_injection": true,
  "knowledge_detail_level": "operational",
  "is_too_vague": false,
  "clarification_prompt": null,
  "scale": "medium",
  "time_estimate_years": 5,
  "time_estimate_reasoning": "需试制、训练工匠并建立原料链，历时数年"
}

不可执行的极度超前示例（注意时间要短）：
{
  "action_domain": "technology",
  "action_type": "军事技术-核武器",
  "action_description": "试图研制核武器",
  "cognitive_gap": 5,
  "resistance_sources": ["祭司", "贵族"],
  "beneficiaries": ["王室"],
  "prerequisites": {
    "met": false,
    "details": "完全超出时代认知与工业基础",
    "nearest_alternative": "改进青铜冶炼与火攻器械"
  },
  "is_knowledge_injection": false,
  "knowledge_detail_level": null,
  "is_too_vague": false,
  "clarification_prompt": null,
  "scale": "large",
  "time_estimate_years": 1,
  "time_estimate_reasoning": "命令虽下，朝野茫然无措，实质无事发生，徒耗岁余"
}
"""


class ActionDomain(str, Enum):
    """行动领域。"""

    ECONOMIC = "economic"
    POLITICAL = "political"
    MILITARY = "military"
    CULTURAL = "cultural"
    TECHNOLOGY = "technology"
    COMPOSITE = "composite"


class KnowledgeDetailLevel(str, Enum):
    """知识注入描述可执行度档位。"""

    CONCEPT = "concept"
    DIRECTION = "direction"
    OPERATIONAL = "operational"
    DETAILED = "detailed"


class ActionScale(str, Enum):
    """行动规模：牵动的人力物力与结构深度。"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Prerequisites(BaseModel):
    """前置条件评估。"""

    met: bool = Field(..., description="当前是否基本满足前置条件")
    details: str = Field(..., description="需要什么条件、当前是否满足")
    nearest_alternative: Optional[str] = Field(
        default=None,
        description="不满足时最近的可行替代；满足可为 null",
    )


class IntentResult(BaseModel):
    """意图解析结构化输出（设计文档 4.3 + 模糊判定 + 规模）。"""

    action_domain: ActionDomain
    action_type: str = Field(..., min_length=1)
    action_description: str = Field(..., min_length=1)
    cognitive_gap: int = Field(..., ge=0, le=5, description="认知代差 0–5")
    resistance_sources: list[str] = Field(default_factory=list)
    beneficiaries: list[str] = Field(default_factory=list)
    prerequisites: Prerequisites
    is_knowledge_injection: bool = False
    knowledge_detail_level: Optional[KnowledgeDetailLevel] = None
    is_too_vague: bool = Field(
        default=False,
        description="输入过于模糊、无法对应可结算行动",
    )
    clarification_prompt: Optional[str] = Field(
        default=None,
        description="is_too_vague=true 时的史官口吻反问；否则 null",
    )
    scale: ActionScale = Field(
        default=ActionScale.MEDIUM,
        description="行动规模 small|medium|large",
    )
    time_estimate_years: float = Field(
        ...,
        ge=TIME_ESTIMATE_MIN,
        le=TIME_ESTIMATE_MAX,
        description=f"预估年数，钳制到 [{TIME_ESTIMATE_MIN}, {TIME_ESTIMATE_MAX}]",
    )
    time_estimate_reasoning: str = Field(..., min_length=1)

    @field_validator("action_domain", mode="before")
    @classmethod
    def map_domain_aliases(cls, v: object) -> object:
        """把幻觉域名映射到六合法域，避免校验失败重试。"""
        if isinstance(v, str):
            key = v.strip().lower()
            return _ACTION_DOMAIN_ALIASES.get(key, key)
        return v

    @field_validator("scale", mode="before")
    @classmethod
    def normalize_scale(cls, v: object) -> object:
        """规模别名归一；缺失时由默认值 medium 兜底。"""
        if v is None or v == "":
            return ActionScale.MEDIUM
        if isinstance(v, str):
            key = v.strip().lower()
            aliases = {
                "s": "small",
                "m": "medium",
                "l": "large",
                "小": "small",
                "中": "medium",
                "大": "large",
            }
            return aliases.get(key, key)
        return v

    @field_validator("cognitive_gap", mode="before")
    @classmethod
    def coerce_gap(cls, v: object) -> object:
        """允许模型返回浮点，收成整数。"""
        if isinstance(v, float):
            return int(round(v))
        return v

    @field_validator("time_estimate_years", mode="before")
    @classmethod
    def clamp_time_estimate(cls, v: object) -> object:
        """≤0 钳到 0.1；>20 钳到 20。不因此触发重试。"""
        if v is None or v == "":
            return TIME_ESTIMATE_MIN
        try:
            t = float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return TIME_ESTIMATE_MIN
        if t <= 0:
            return TIME_ESTIMATE_MIN
        if t > TIME_ESTIMATE_MAX:
            return TIME_ESTIMATE_MAX
        return t

    @model_validator(mode="before")
    @classmethod
    def fill_vague_defaults(cls, data: Any) -> Any:
        """模糊输入时补全可结算字段的安全默认值。"""
        if not isinstance(data, dict):
            return data
        if not data.get("is_too_vague"):
            return data
        data.setdefault("action_domain", "composite")
        data.setdefault("action_type", "未明政令")
        data.setdefault("action_description", "输入过于笼统，无法对应可结算行动")
        data.setdefault("cognitive_gap", 0)
        data.setdefault("resistance_sources", [])
        data.setdefault("beneficiaries", [])
        data.setdefault(
            "prerequisites",
            {
                "met": False,
                "details": "未指明任何具体措置",
                "nearest_alternative": None,
            },
        )
        data.setdefault("is_knowledge_injection", False)
        data.setdefault("knowledge_detail_level", None)
        data.setdefault("scale", "small")
        data.setdefault("time_estimate_years", TIME_ESTIMATE_MIN)
        data.setdefault("time_estimate_reasoning", "政令未明，未实际推进")
        if not data.get("clarification_prompt"):
            data["clarification_prompt"] = (
                "陛下欲兴何业？是垦荒兴修、练兵扩军，还是设学兴文？请明示。"
            )
        return data

    @model_validator(mode="after")
    def post_normalize(self) -> IntentResult:
        """知识档位一致性；模糊时强制 clarification；非模糊清空反问。"""
        updates: dict[str, Any] = {}

        if self.is_too_vague:
            if not (self.clarification_prompt and self.clarification_prompt.strip()):
                updates["clarification_prompt"] = (
                    "陛下欲兴何业？是垦荒兴修、练兵扩军，还是设学兴文？请明示。"
                )
            updates["is_knowledge_injection"] = False
            updates["knowledge_detail_level"] = None
        else:
            if self.clarification_prompt is not None:
                updates["clarification_prompt"] = None

        if not self.is_too_vague:
            if not self.is_knowledge_injection:
                if self.knowledge_detail_level is not None:
                    updates["knowledge_detail_level"] = None
            elif self.knowledge_detail_level is None:
                updates["knowledge_detail_level"] = KnowledgeDetailLevel.CONCEPT

        if updates:
            return self.model_copy(update=updates)
        return self


def build_state_summary(state: CivState) -> str:
    """从 CivState 提取关键字段，生成中文状态摘要供提示词使用。"""
    land = _LAND_LABELS.get(state.land_system.value, state.land_system.value)
    extractions = "、".join(
        _EXTRACTION_LABELS.get(e.value, e.value) for e in state.surplus_extraction
    )
    auth = _AUTHORITY_LABELS.get(
        state.polity.authority_source.value, state.polity.authority_source.value
    )
    decision = _DECISION_LABELS.get(
        state.polity.decision_structure.value, state.polity.decision_structure.value
    )
    succession = _SUCCESSION_LABELS.get(
        state.polity.succession.value, state.polity.succession.value
    )
    year = state.year
    year_str = f"公元前 {abs(year):.0f} 年" if year < 0 else f"公元 {year:.0f} 年"

    return (
        f"文明名：{state.civ_name}（模板 {state.template_id}）\n"
        f"年份：{year_str}；回合：{state.turn}\n"
        f"人口：{state.population}；稳定性：{state.stability:.1f}；统治力：{state.authority:.1f}\n"
        f"科技三线：农业 {state.tech_agriculture:.2f} / "
        f"工程 {state.tech_engineering:.2f} / 知识 {state.tech_knowledge:.2f}\n"
        f"官僚化：{state.bureaucratization:.2f}；识字率约：{state.literacy_rate():.2%}\n"
        f"主要制度：土地={land}；提取={extractions}；"
        f"权力来源={auth}；决策={decision}；继承={succession}\n"
        f"领土：核心 {state.territory_core} km² / 边疆 {state.territory_frontier} km²；"
        f"肥力 {state.biome_fertility:.2f}"
    )


def _build_user_prompt(
    subtask_description: str,
    state: CivState,
    recent_summary: str = "",
) -> str:
    """组装用户侧提示。"""
    summary = build_state_summary(state)
    recent = recent_summary.strip() or "（暂无近期摘要）"
    return (
        f"当前文明状态：\n{summary}\n\n"
        f"最近摘要：\n{recent}\n\n"
        f"请解析以下政令（子任务）：\n{subtask_description.strip()}"
    )


async def parse_intent(
    player_input: str,
    state: CivState,
    *,
    recent_summary: str = "",
    client: LLMClient | None = None,
) -> IntentResult:
    """将单个子任务的自然语言转为结构化意图。

    TODO(管线)：若 result.is_too_vague，跳过数学引擎，直接返回 clarification_prompt。
    """
    text = player_input.strip()
    if not text:
        raise ValueError("意图解析输入不能为空")

    llm = client or get_llm_client()
    messages = [
        {"role": "system", "content": INTENT_PARSER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_prompt(text, state, recent_summary),
        },
    ]
    return await llm.call_json(messages, IntentResult)
