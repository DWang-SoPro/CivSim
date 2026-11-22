"""文明状态完整数据模型（设计文档第二章）。

所有字段带中文注释，标明含义与取值范围。枚举用 Enum，数值用 Field 约束。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------


class LandSystem(str, Enum):
    """土地制度：文明同一时间一种主导制度，可并存过渡态。"""

    CLAN_COMMUNAL = "clan_communal"  # 氏族公有，集体耕作
    NOBLE_ESTATE = "noble_estate"  # 贵族庄园，农民依附
    STATE_GRANT = "state_grant"  # 国有授田，按功/职分配
    LANDLORD_TENANT = "landlord_tenant"  # 地主租佃，农民交租
    YEOMAN_SMALLHOLD = "yeoman_smallhold"  # 自耕农小农，个体经营


class SurplusExtraction(str, Enum):
    """剩余提取方式。"""

    TRIBUTE = "tribute"  # 贡赋
    TAX_IN_KIND = "tax_in_kind"  # 实物税
    TAX_MONETARY = "tax_monetary"  # 货币税
    COMMERCIAL_TAX = "commercial_tax"  # 商业税


class AuthoritySource(str, Enum):
    """权力来源。"""

    BLOODLINE = "bloodline"  # 血统
    MILITARY = "military"  # 军功
    ELECTION = "election"  # 选举/推举
    THEOCRATIC = "theocratic"  # 神权


class DecisionStructure(str, Enum):
    """决策结构。"""

    AUTOCRACY = "autocracy"  # 独裁
    OLIGARCHY = "oligarchy"  # 寡头
    COUNCIL = "council"  # 议事会
    BUREAUCRACY = "bureaucracy"  # 官僚体制


class Succession(str, Enum):
    """继承方式。"""

    HEREDITARY = "hereditary"  # 世袭
    ABDICATION = "abdication"  # 禅让
    ELECTION = "election"  # 选举
    MILITARY_COUP = "military_coup"  # 军事夺权


class ReligionType(str, Enum):
    """宗教类型。"""

    NATURE_WORSHIP = "nature_worship"  # 多神自然崇拜
    ANCESTOR_WORSHIP = "ancestor_worship"  # 祖先崇拜
    CITY_PATRON = "city_patron"  # 城邦守护神
    MONOTHEISM = "monotheism"  # 一神教
    POLYTHEISTIC = "polytheistic"  # 多神教
    PHILOSOPHICAL = "philosophical"  # 哲学伦理体系


class StateRelation(str, Enum):
    """宗教与国家的关系。"""

    STATE_RELIGION = "state_religion"  # 国教
    PROTECTED = "protected"  # 受庇护
    TOLERATED = "tolerated"  # 容忍
    SUPPRESSED = "suppressed"  # 受压制


class ActionResultTier(str, Enum):
    """行动结果档位（社会摩擦掷骰映射）。"""

    GREAT_SUCCESS = "great_success"  # 大成功，效果 150%
    SUCCESS = "success"  # 成功，效果 100%
    PARTIAL = "partial"  # 部分成功，效果 50%
    FAILURE = "failure"  # 失败，效果 0% + 副作用
    DISASTER = "disaster"  # 灾难性失败，负面效果 + 严重副作用


# ---------------------------------------------------------------------------
# 子结构
# ---------------------------------------------------------------------------


class LaborDistribution(BaseModel):
    """劳动形态比例分布，四类比例之和必须为 1.0。"""

    free_citizens: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="自由民（自主劳动）比例，范围 0.0—1.0",
    )
    corvee: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="徭役（义务劳动，保留人身自由）比例，范围 0.0—1.0",
    )
    serf: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="农奴（依附土地，有限人身自由）比例，范围 0.0—1.0",
    )
    slave: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="奴隶（无人身自由）比例，范围 0.0—1.0",
    )

    @model_validator(mode="after")
    def proportions_sum_to_one(self) -> LaborDistribution:
        """校验四类劳动比例之和约为 1.0。"""
        total = self.free_citizens + self.corvee + self.serf + self.slave
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"劳动形态比例之和必须为 1.0，当前为 {total}")
        return self


class Polity(BaseModel):
    """政体结构：权力来源 × 决策结构 × 继承方式。"""

    authority_source: AuthoritySource = Field(..., description="权力来源")
    decision_structure: DecisionStructure = Field(..., description="决策结构")
    succession: Succession = Field(..., description="继承方式")


class Legitimacy(BaseModel):
    """合法性结构：多个来源各自强度，非单一数值。"""

    traditional: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="传统型合法性：「我们家族一直统治」，范围 0.0—1.0",
    )
    religious: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="宗教型合法性：「天命所归/神选」，范围 0.0—1.0",
    )
    performance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="绩效型合法性：「我带来了胜利/繁荣」，范围 0.0—1.0",
    )
    legal: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="法理型合法性：「制度规定我来统治」，范围 0.0—1.0",
    )


class Religion(BaseModel):
    """单个宗教实体。"""

    name: str = Field(..., description="宗教名称")
    type: ReligionType = Field(..., description="宗教类型")
    coverage: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="人口覆盖率，范围 0.0—1.0；所有宗教 coverage 之和 ≤ 1.0",
    )
    state_relation: StateRelation = Field(..., description="与国家的关系")
    organization: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="组织化程度：0=散漫民间信仰，1=高度组织化教团",
    )
    knowledge_carrier: bool = Field(
        ...,
        description="是否承担教育/记录/历法职能",
    )
    economic_power: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="经济实力（神殿经济/教会地产/什一税），范围 0.0—1.0",
    )


class Accumulations(BaseModel):
    """五个领域的路径积累值（设计文档第六节）。实践中约 0—3.0，无硬上限。"""

    academic: float = Field(
        default=0.0,
        ge=0.0,
        description="学术基础：教育/研究/知识传播，≥ 0.0",
    )
    military: float = Field(
        default=0.0,
        ge=0.0,
        description="军事传统：练兵/战争/军事改革，≥ 0.0",
    )
    commercial: float = Field(
        default=0.0,
        ge=0.0,
        description="商业生态：贸易/市场/货币，≥ 0.0",
    )
    administrative: float = Field(
        default=0.0,
        ge=0.0,
        description="行政经验：官僚/法律/制度建设，≥ 0.0",
    )
    cultural: float = Field(
        default=0.0,
        ge=0.0,
        description="宗教文化：宗教/仪式/意识形态，≥ 0.0",
    )


# ---------------------------------------------------------------------------
# 完整文明状态
# ---------------------------------------------------------------------------


class CivState(BaseModel):
    """完整文明状态：物质基底 + 生产关系 + 上层建筑 + 社会张力 + 积累值。"""

    # ---- 元信息 ----
    civ_name: str = Field(..., description="文明名称")
    template_id: str = Field(..., description="模板标识符")
    turn: int = Field(default=0, ge=0, description="当前回合数，≥ 0")
    year: float = Field(..., description="当前年份（可为负表示公元前）")

    # ---- 第一层：物质基底 ----
    population: int = Field(
        ...,
        ge=0,
        description="人口（整数）。初始范围约 10,000—100,000",
    )
    tech_agriculture: float = Field(
        ...,
        ge=0.0,
        description="农业技术线等级，连续浮点，0.0 起步，约 5.0 对应近代早期",
    )
    tech_engineering: float = Field(
        ...,
        ge=0.0,
        description="工程与军事技术线等级，连续浮点，≥ 0.0",
    )
    tech_knowledge: float = Field(
        ...,
        ge=0.0,
        description="知识与文化技术线等级，连续浮点，≥ 0.0",
    )
    territory_core: int = Field(
        ...,
        ge=0,
        description="核心领土面积（km²），治理效率不衰减",
    )
    territory_frontier: int = Field(
        ...,
        ge=0,
        description="边疆领土面积（km²），治理效率随距离衰减",
    )
    biome_fertility: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="生态肥力，范围 0.0—1.0；开局由地域决定",
    )
    agricultural_modifier: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description=(
            "农业修正系数：肥力之外的农业禀赋（灌溉传统、作物品种、耕作技艺等），"
            "范围约 0.5—2.0，默认 1.0；用于模板级盈余校准，不改动领土"
        ),
    )
    grain_reserve: float = Field(
        default=0.15,
        ge=0.0,
        le=2.0,
        description="官仓余粮储备（折合全国年口粮倍数，0.0—2.0，默认 0.15 以兼容旧存档）",
    )

    # ---- 第二层：生产关系 ----
    land_system: LandSystem = Field(..., description="主导土地制度")
    labor_distribution: LaborDistribution = Field(..., description="劳动形态比例分布")
    surplus_extraction: list[SurplusExtraction] = Field(
        ...,
        min_length=1,
        description="剩余提取方式列表（可多种并存）",
    )

    # ---- 第三层：上层建筑 ----
    polity: Polity = Field(..., description="政体结构三子维度组合")
    bureaucratization: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="官僚化程度，范围 0.0—1.0；上限受知识技术约束",
    )
    legitimacy: Legitimacy = Field(..., description="合法性结构")
    religions: list[Religion] = Field(
        default_factory=list,
        description="宗教实体列表，可有 0 到多个",
    )

    # ---- 派生/控制指标 ----
    stability: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="稳定性，范围 0—100",
    )
    authority: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="统治力，范围 0—100，反映统治集团实际控制力",
    )

    # ---- 第四层：社会张力（可由前三层计算，模板可给初始值）----
    class_tension: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="阶级矛盾，范围 0.0—1.0；None 表示由引擎按公式计算",
    )
    elite_cohesion: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="精英凝聚力，范围 0.0—1.0；None 表示由引擎估算",
    )

    # ---- 路径积累 ----
    accumulations: Accumulations = Field(
        default_factory=Accumulations,
        description="五个领域的路径积累值",
    )

    # ---- 辅助：知识机构覆盖率（影响识字率）----
    knowledge_institution_coverage: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="知识机构覆盖率，范围 0.0—1.0；由宗教知识载体与学宫建设决定",
    )

    @field_validator("surplus_extraction")
    @classmethod
    def unique_extractions(cls, v: list[SurplusExtraction]) -> list[SurplusExtraction]:
        """提取方式去重，保持顺序。"""
        seen: set[SurplusExtraction] = set()
        result: list[SurplusExtraction] = []
        for item in v:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @model_validator(mode="after")
    def religion_coverage_cap(self) -> CivState:
        """所有宗教覆盖率之和不得超过 1.0。"""
        total = sum(r.coverage for r in self.religions)
        if total > 1.0 + 1e-6:
            raise ValueError(f"宗教覆盖率之和不得超过 1.0，当前为 {total}")
        return self

    def legitimacy_total(self) -> float:
        """总合法性：各来源强度的简单平均（权重由社会结构决定，MVP 取等权）。"""
        leg = self.legitimacy
        return (leg.traditional + leg.religious + leg.performance + leg.legal) / 4.0

    def literacy_rate(self) -> float:
        """识字率 = min(tech_knowledge × 0.15, 0.8) × 知识机构覆盖率。"""
        return min(self.tech_knowledge * 0.15, 0.8) * self.knowledge_institution_coverage
