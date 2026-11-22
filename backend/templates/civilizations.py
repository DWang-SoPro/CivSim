"""六个文明模板（设计文档第九章）。

每个模板为合法 CivState 初始值；提供生产关系组合校验。
"""

from __future__ import annotations

from typing import Any

from backend.models.schemas import (
    Accumulations,
    AuthoritySource,
    CivState,
    DecisionStructure,
    LaborDistribution,
    LandSystem,
    Legitimacy,
    Polity,
    Religion,
    ReligionType,
    StateRelation,
    Succession,
    SurplusExtraction,
)

# 提取方式前置条件：
# - tax_in_kind：官僚化 ≥ 0.2
# - tax_monetary：官僚化 ≥ 0.4 或 商业积累 ≥ 0.5（商业网络可替代官僚）
# - commercial_tax：官僚化 ≥ 0.3 或 商业积累 ≥ 0.4
EXTRACTION_BUREAU_MIN: dict[SurplusExtraction, float] = {
    SurplusExtraction.TAX_IN_KIND: 0.2,
    SurplusExtraction.TAX_MONETARY: 0.4,
    SurplusExtraction.COMMERCIAL_TAX: 0.3,
}
EXTRACTION_COMMERCIAL_ALT: dict[SurplusExtraction, float] = {
    SurplusExtraction.TAX_MONETARY: 0.5,
    SurplusExtraction.COMMERCIAL_TAX: 0.4,
}

# 土地制度允许的直接后继（文档：不可跳跃，如 clan → yeoman）
LAND_SYSTEM_TRANSITIONS: dict[LandSystem, set[LandSystem]] = {
    LandSystem.CLAN_COMMUNAL: {
        LandSystem.CLAN_COMMUNAL,
        LandSystem.NOBLE_ESTATE,
        LandSystem.STATE_GRANT,
    },
    LandSystem.NOBLE_ESTATE: {
        LandSystem.NOBLE_ESTATE,
        LandSystem.STATE_GRANT,
        LandSystem.LANDLORD_TENANT,
        LandSystem.YEOMAN_SMALLHOLD,
    },
    LandSystem.STATE_GRANT: {
        LandSystem.STATE_GRANT,
        LandSystem.NOBLE_ESTATE,
        LandSystem.LANDLORD_TENANT,
        LandSystem.YEOMAN_SMALLHOLD,
    },
    LandSystem.LANDLORD_TENANT: {
        LandSystem.LANDLORD_TENANT,
        LandSystem.YEOMAN_SMALLHOLD,
        LandSystem.STATE_GRANT,
    },
    LandSystem.YEOMAN_SMALLHOLD: {
        LandSystem.YEOMAN_SMALLHOLD,
        LandSystem.LANDLORD_TENANT,
        LandSystem.STATE_GRANT,
    },
}


def _labor(**kwargs: float) -> LaborDistribution:
    return LaborDistribution(**kwargs)


def _acc(**kwargs: float) -> Accumulations:
    return Accumulations(**kwargs)


def _build_templates() -> dict[str, CivState]:
    """构建六个文明初始状态。"""
    sumer = CivState(
        civ_name="苏美尔城邦联盟",
        template_id="sumer",
        turn=0,
        year=-3000.0,
        population=30000,
        tech_agriculture=1.0,
        tech_engineering=0.8,
        tech_knowledge=1.0,
        territory_core=300,
        territory_frontier=200,
        biome_fertility=0.75,
        # 两河灌溉发达：补偿小领土，使开局盈余 ≈0.90（modifier=1 时约 0.74）
        agricultural_modifier=0.90 / 0.7427800269905533,
        grain_reserve=0.14,
        land_system=LandSystem.NOBLE_ESTATE,
        labor_distribution=_labor(
            free_citizens=0.4, corvee=0.3, serf=0.1, slave=0.2
        ),
        surplus_extraction=[SurplusExtraction.TRIBUTE, SurplusExtraction.TAX_IN_KIND],
        polity=Polity(
            authority_source=AuthoritySource.THEOCRATIC,
            decision_structure=DecisionStructure.COUNCIL,
            succession=Succession.ELECTION,
        ),
        bureaucratization=0.25,
        legitimacy=Legitimacy(
            traditional=0.4, religious=0.7, performance=0.3, legal=0.1
        ),
        religions=[
            Religion(
                name="城邦守护神信仰",
                type=ReligionType.CITY_PATRON,
                coverage=0.9,
                state_relation=StateRelation.STATE_RELIGION,
                organization=0.6,
                knowledge_carrier=True,
                economic_power=0.5,
            )
        ],
        stability=65.0,
        authority=25.0,
        knowledge_institution_coverage=0.6,
        accumulations=_acc(
            academic=0.3,
            military=0.2,
            commercial=0.4,
            administrative=0.2,
            cultural=0.5,
        ),
    )

    egypt = CivState(
        civ_name="早王朝埃及",
        template_id="egypt",
        turn=0,
        year=-3000.0,
        population=40000,
        tech_agriculture=1.0,
        tech_engineering=0.9,
        tech_knowledge=0.8,
        territory_core=600,
        territory_frontier=200,
        biome_fertility=0.85,
        grain_reserve=0.24,
        land_system=LandSystem.STATE_GRANT,
        labor_distribution=_labor(
            free_citizens=0.3, corvee=0.5, serf=0.1, slave=0.1
        ),
        surplus_extraction=[SurplusExtraction.TAX_IN_KIND],
        polity=Polity(
            authority_source=AuthoritySource.THEOCRATIC,
            decision_structure=DecisionStructure.AUTOCRACY,
            succession=Succession.HEREDITARY,
        ),
        bureaucratization=0.35,
        legitimacy=Legitimacy(
            traditional=0.5, religious=0.8, performance=0.4, legal=0.2
        ),
        religions=[
            Religion(
                name="太阳神崇拜",
                type=ReligionType.POLYTHEISTIC,
                coverage=0.95,
                state_relation=StateRelation.STATE_RELIGION,
                organization=0.7,
                knowledge_carrier=True,
                economic_power=0.6,
            )
        ],
        stability=70.0,
        authority=50.0,
        knowledge_institution_coverage=0.5,
        accumulations=_acc(
            academic=0.2,
            military=0.1,
            commercial=0.1,
            administrative=0.4,
            cultural=0.6,
        ),
    )

    harappa = CivState(
        civ_name="哈拉帕联盟",
        template_id="harappa",
        turn=0,
        year=-2000.0,
        population=50000,
        tech_agriculture=1.2,
        tech_engineering=1.0,
        tech_knowledge=0.8,
        territory_core=800,
        territory_frontier=400,
        biome_fertility=0.65,
        grain_reserve=0.18,
        land_system=LandSystem.CLAN_COMMUNAL,
        labor_distribution=_labor(
            free_citizens=0.7, corvee=0.2, serf=0.05, slave=0.05
        ),
        surplus_extraction=[SurplusExtraction.TRIBUTE],
        polity=Polity(
            authority_source=AuthoritySource.ELECTION,
            decision_structure=DecisionStructure.COUNCIL,
            succession=Succession.ELECTION,
        ),
        bureaucratization=0.2,
        legitimacy=Legitimacy(
            traditional=0.6, religious=0.3, performance=0.5, legal=0.1
        ),
        religions=[
            Religion(
                name="自然崇拜",
                type=ReligionType.NATURE_WORSHIP,
                coverage=0.7,
                state_relation=StateRelation.TOLERATED,
                organization=0.2,
                knowledge_carrier=False,
                economic_power=0.1,
            )
        ],
        stability=82.0,
        authority=20.0,
        knowledge_institution_coverage=0.3,
        accumulations=_acc(
            academic=0.2,
            military=0.1,
            commercial=0.5,
            administrative=0.1,
            cultural=0.2,
        ),
    )

    babylon = CivState(
        civ_name="古巴比伦王国",
        template_id="babylon",
        turn=0,
        year=-2000.0,
        population=60000,
        tech_agriculture=1.2,
        tech_engineering=1.1,
        tech_knowledge=1.3,
        territory_core=800,
        territory_frontier=700,
        biome_fertility=0.70,
        grain_reserve=0.18,
        land_system=LandSystem.NOBLE_ESTATE,
        labor_distribution=_labor(
            free_citizens=0.3, corvee=0.3, serf=0.2, slave=0.2
        ),
        surplus_extraction=[SurplusExtraction.TAX_IN_KIND, SurplusExtraction.TRIBUTE],
        polity=Polity(
            authority_source=AuthoritySource.MILITARY,
            decision_structure=DecisionStructure.AUTOCRACY,
            succession=Succession.HEREDITARY,
        ),
        bureaucratization=0.4,
        legitimacy=Legitimacy(
            traditional=0.3, religious=0.5, performance=0.6, legal=0.4
        ),
        religions=[
            Religion(
                name="马尔杜克神崇拜",
                type=ReligionType.CITY_PATRON,
                coverage=0.7,
                state_relation=StateRelation.STATE_RELIGION,
                organization=0.5,
                knowledge_carrier=True,
                economic_power=0.4,
            )
        ],
        stability=75.0,
        authority=45.0,
        knowledge_institution_coverage=0.55,
        accumulations=_acc(
            academic=0.4,
            military=0.3,
            commercial=0.3,
            administrative=0.5,
            cultural=0.3,
        ),
    )

    zhou = CivState(
        civ_name="西周王朝",
        template_id="zhou",
        turn=0,
        year=-1000.0,
        population=80000,
        tech_agriculture=1.5,
        tech_engineering=1.3,
        tech_knowledge=1.2,
        territory_core=1000,
        territory_frontier=1000,
        biome_fertility=0.65,
        grain_reserve=0.20,
        land_system=LandSystem.STATE_GRANT,
        labor_distribution=_labor(
            free_citizens=0.3, corvee=0.4, serf=0.2, slave=0.1
        ),
        surplus_extraction=[SurplusExtraction.TRIBUTE, SurplusExtraction.TAX_IN_KIND],
        polity=Polity(
            authority_source=AuthoritySource.BLOODLINE,
            decision_structure=DecisionStructure.OLIGARCHY,
            succession=Succession.HEREDITARY,
        ),
        bureaucratization=0.3,
        legitimacy=Legitimacy(
            traditional=0.8, religious=0.5, performance=0.4, legal=0.2
        ),
        religions=[
            Religion(
                name="天命信仰与祖先崇拜",
                type=ReligionType.ANCESTOR_WORSHIP,
                coverage=0.8,
                state_relation=StateRelation.STATE_RELIGION,
                organization=0.4,
                knowledge_carrier=True,
                economic_power=0.3,
            )
        ],
        stability=70.0,
        authority=60.0,
        knowledge_institution_coverage=0.5,
        accumulations=_acc(
            academic=0.3,
            military=0.4,
            commercial=0.2,
            administrative=0.3,
            cultural=0.5,
        ),
    )

    greece = CivState(
        civ_name="古希腊城邦",
        template_id="greece",
        turn=0,
        year=-500.0,
        population=45000,
        tech_agriculture=1.3,
        tech_engineering=1.5,
        tech_knowledge=1.8,
        territory_core=400,
        territory_frontier=200,
        biome_fertility=0.55,
        # 多山贫瘠但有一定耕作技艺：开局盈余 ≈0.90（modifier=1 时约 0.62）
        agricultural_modifier=0.90 / 0.6184587394411957,
        grain_reserve=0.12,
        land_system=LandSystem.YEOMAN_SMALLHOLD,
        labor_distribution=_labor(
            free_citizens=0.5, corvee=0.1, serf=0.0, slave=0.4
        ),
        surplus_extraction=[
            SurplusExtraction.TAX_MONETARY,
            SurplusExtraction.COMMERCIAL_TAX,
        ],
        polity=Polity(
            authority_source=AuthoritySource.ELECTION,
            decision_structure=DecisionStructure.COUNCIL,
            succession=Succession.ELECTION,
        ),
        bureaucratization=0.2,
        legitimacy=Legitimacy(
            traditional=0.2, religious=0.2, performance=0.5, legal=0.5
        ),
        religions=[
            Religion(
                name="奥林匹斯诸神",
                type=ReligionType.POLYTHEISTIC,
                coverage=0.8,
                state_relation=StateRelation.TOLERATED,
                organization=0.3,
                knowledge_carrier=False,
                economic_power=0.2,
            )
        ],
        stability=60.0,
        authority=20.0,
        knowledge_institution_coverage=0.7,
        accumulations=_acc(
            academic=0.8,
            military=0.3,
            commercial=0.6,
            administrative=0.2,
            cultural=0.7,
        ),
    )

    return {
        "sumer": sumer,
        "egypt": egypt,
        "harappa": harappa,
        "babylon": babylon,
        "zhou": zhou,
        "greece": greece,
    }


CIVILIZATION_TEMPLATES: dict[str, CivState] = _build_templates()


def list_templates() -> list[str]:
    """返回全部模板 ID。"""
    return list(CIVILIZATION_TEMPLATES.keys())


def get_template(template_id: str) -> CivState:
    """获取模板的深拷贝初始状态。"""
    if template_id not in CIVILIZATION_TEMPLATES:
        raise KeyError(f"未知文明模板: {template_id}")
    return CIVILIZATION_TEMPLATES[template_id].model_copy(deep=True)


def load_civ_state(template_id: str) -> CivState:
    """加载模板为可游玩的 CivState（同 get_template）。"""
    return get_template(template_id)


def check_extraction_prerequisites(state: CivState) -> list[str]:
    """检查剩余提取方式是否满足前置条件，返回问题列表。

    货币税 / 商业税可用商业积累作为官僚化的替代路径。
    """
    issues: list[str] = []
    commercial = state.accumulations.commercial
    bureau = state.bureaucratization

    for method in state.surplus_extraction:
        if method == SurplusExtraction.TRIBUTE:
            continue

        min_bureau = EXTRACTION_BUREAU_MIN.get(method)
        if min_bureau is None:
            continue

        alt_commercial = EXTRACTION_COMMERCIAL_ALT.get(method)
        bureau_ok = bureau >= min_bureau
        commercial_ok = alt_commercial is not None and commercial >= alt_commercial

        if alt_commercial is not None:
            if not (bureau_ok or commercial_ok):
                issues.append(
                    f"提取方式 {method.value} 需要官僚化 ≥ {min_bureau} "
                    f"或商业积累 ≥ {alt_commercial}，"
                    f"当前官僚化={bureau}、商业积累={commercial}"
                )
        elif not bureau_ok:
            issues.append(
                f"提取方式 {method.value} 需要官僚化 ≥ {min_bureau}，"
                f"当前为 {bureau}"
            )
    return issues


def can_transition_land_system(current: LandSystem, target: LandSystem) -> bool:
    """土地制度是否允许从 current 直接变更到 target。"""
    return target in LAND_SYSTEM_TRANSITIONS.get(current, set())


def validate_production_relations(state: CivState) -> tuple[bool, list[str]]:
    """校验生产关系组合是否结构合法。

    硬约束：
      1. 劳动比例之和 = 1.0（Pydantic 已保证，此处复核）
      2. 至少一种剩余提取方式
      3. 土地制度为已知枚举
      4. 氏族公有不应以奴隶为主导劳动形态（slave > 0.5）
      5. clan_communal 不应与 landlord_tenant 并存为「当前制度」
         （当前制度是单一枚举，此项通过枚举本身满足）

    另检查提取方式前置（含商业积累 OR 分支，见 check_extraction_prerequisites）。

    Returns:
        (是否合法, 问题列表)；提取前置不满足时亦为不合法。
    """
    issues: list[str] = []

    labor = state.labor_distribution
    total = labor.free_citizens + labor.corvee + labor.serf + labor.slave
    if abs(total - 1.0) > 1e-6:
        issues.append(f"劳动比例之和不为 1.0：{total}")

    if not state.surplus_extraction:
        issues.append("至少需要一种剩余提取方式")

    if state.land_system == LandSystem.CLAN_COMMUNAL and labor.slave > 0.5:
        issues.append("氏族公有制下奴隶比例不应超过 50%")

    if state.land_system == LandSystem.YEOMAN_SMALLHOLD and labor.serf > 0.5:
        issues.append("自耕农制度下农奴比例不应超过 50%")

    issues.extend(check_extraction_prerequisites(state))
    ok = len(issues) == 0
    return ok, issues


def template_as_dict(template_id: str) -> dict[str, Any]:
    """导出模板为可序列化字典。"""
    return get_template(template_id).model_dump(mode="json")
