"""治理效率衰减模型（设计文档 §3.2）。

E_governance = bureaucratization × e^(-D_norm / V_norm)
D_norm = territory_frontier / max(territory_core, 1)
V_norm = (tech_engineering + tech_knowledge) / 2
"""

from __future__ import annotations

import math

from backend.models.schemas import CivState


def governance_efficiency(
    bureaucratization: float,
    territory_frontier: float,
    territory_core: float,
    tech_engineering: float,
    tech_knowledge: float,
) -> float:
    """计算治理效率 E。

    Args:
        bureaucratization: 官僚化程度，期望 0.0—1.0
        territory_frontier: 边疆面积
        territory_core: 核心领土面积
        tech_engineering: 工程技术等级
        tech_knowledge: 知识技术等级

    Returns:
        治理效率，钳制在 [0.0, 1.0]。V_norm 为 0 时按极大衰减处理。
    """
    d_norm = territory_frontier / max(territory_core, 1.0)
    v_norm = (tech_engineering + tech_knowledge) / 2.0

    if v_norm <= 0.0:
        # 无交通/通讯能力时，边疆完全失控（指数项趋于无穷）
        e = 0.0 if d_norm > 0.0 else float(bureaucratization)
    else:
        e = bureaucratization * math.exp(-d_norm / v_norm)

    if math.isnan(e) or math.isinf(e):
        return 0.0
    return max(0.0, min(1.0, e))


def governance_efficiency_from_state(state: CivState) -> float:
    """从 CivState 计算治理效率。"""
    return governance_efficiency(
        bureaucratization=state.bureaucratization,
        territory_frontier=float(state.territory_frontier),
        territory_core=float(state.territory_core),
        tech_engineering=state.tech_engineering,
        tech_knowledge=state.tech_knowledge,
    )
