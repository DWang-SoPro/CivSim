"""第三层 — 长期索引：关键转折点检测、入库与关键词标签检索。

向量接口预留：`embed_text()` 当前未实现；landmarks 保留 embedding / embedding_model。
"""

from __future__ import annotations

from typing import Any, Optional

from backend.memory.store import LandmarkRecord, MemoryStore
from backend.models.schemas import CivState

# 触发阈值
TECH_BREAKTHROUGH_DELTA = 0.5
TERRITORY_CHANGE_RATIO = 0.20
LEGITIMACY_CRISIS_THRESHOLD = 0.3

# 稳定性极端事件关键词（events / narrative 粗匹配）
_EXTREME_EVENT_KEYWORDS = (
    "叛乱",
    "起义",
    "饥荒",
    "饿殍",
    "瘟疫",
    "大疫",
    "民变",
)

# 各触发类型默认重要性（检索排序用）
_IMPORTANCE = {
    "institutional": 5,
    "tech_breakthrough": 4,
    "territory": 4,
    "legitimacy_crisis": 5,
    "stability_extreme": 5,
    "religion": 4,
}


def embed_text(text: str, *, model: str = "glm-embedding-3") -> list[float] | None:
    """向量嵌入接口（预留）。

    将来接入 GLM Embedding-3 等模型。当前阶段不做向量检索，
    返回 None；调用方不得依赖非空结果。
    """
    _ = (text, model)
    return None


def snapshot_state(state: CivState) -> dict[str, Any]:
    """关键状态快照（写入 landmark.state_snapshot）。"""
    return {
        "population": state.population,
        "stability": state.stability,
        "authority": state.authority,
        "tech_agriculture": state.tech_agriculture,
        "tech_engineering": state.tech_engineering,
        "tech_knowledge": state.tech_knowledge,
        "territory_core": state.territory_core,
        "territory_frontier": state.territory_frontier,
        "land_system": state.land_system.value
        if hasattr(state.land_system, "value")
        else str(state.land_system),
        "bureaucratization": state.bureaucratization,
        "legitimacy_total": state.legitimacy_total(),
        "polity": {
            "authority_source": state.polity.authority_source.value
            if hasattr(state.polity.authority_source, "value")
            else str(state.polity.authority_source),
            "decision_structure": state.polity.decision_structure.value
            if hasattr(state.polity.decision_structure, "value")
            else str(state.polity.decision_structure),
            "succession": state.polity.succession.value
            if hasattr(state.polity.succession, "value")
            else str(state.polity.succession),
        },
    }


def _polity_tuple(state: CivState) -> tuple[str, str, str]:
    p = state.polity
    return (
        str(getattr(p.authority_source, "value", p.authority_source)),
        str(getattr(p.decision_structure, "value", p.decision_structure)),
        str(getattr(p.succession, "value", p.succession)),
    )


def _labor_tuple(state: CivState) -> tuple[float, float, float, float]:
    labor = state.labor_distribution
    return (labor.free_citizens, labor.serf, labor.slave, labor.corvee)


def _religions_sig(state: CivState) -> tuple[tuple[str, float, str], ...]:
    items = []
    for r in state.religions:
        name = getattr(r, "name", str(r))
        cov = float(getattr(r, "coverage", 0.0))
        relation = str(
            getattr(r.state_relation, "value", r.state_relation)
        )
        items.append((name, round(cov, 4), relation))
    return tuple(sorted(items))


def _total_territory(state: CivState) -> int:
    return int(state.territory_core) + int(state.territory_frontier)


def detect_landmark_events(
    *,
    turn: int,
    year: float,
    state_before: CivState,
    state_after: CivState,
    domain_tags: list[str],
    action_description: str,
    result_tier: str,
    events: list[str] | None = None,
    narrative: str = "",
) -> list[dict[str, Any]]:
    """检测本回合是否触发长期索引；返回待写入的 landmark 草稿列表。"""
    drafts: list[dict[str, Any]] = []
    events = events or []
    base_tags = [t.lower() for t in domain_tags]

    # 1) 制度变更
    land_changed = state_before.land_system != state_after.land_system
    labor_changed = _labor_tuple(state_before) != _labor_tuple(state_after)
    polity_changed = _polity_tuple(state_before) != _polity_tuple(state_after)
    if land_changed or labor_changed or polity_changed:
        parts = []
        if land_changed:
            parts.append(
                f"土地制度由{state_before.land_system.value}改为{state_after.land_system.value}"
            )
        if labor_changed:
            parts.append("劳动形态发生调整")
        if polity_changed:
            parts.append("政体组件发生变化")
        drafts.append(
            {
                "tags": list({*base_tags, "political", "institutional"}),
                "title": "制度变革：" + (action_description[:24] or "体制更张"),
                "summary": (
                    f"第{turn}回合，{ '；'.join(parts) }。"
                    f"行动「{action_description}」结果为{result_tier}，"
                    f"此后统治结构与利益格局随之改写。"
                ),
                "importance_score": _IMPORTANCE["institutional"],
                "trigger": "institutional",
            }
        )

    # 2) 技术突破
    tech_deltas = {
        "agriculture": state_after.tech_agriculture - state_before.tech_agriculture,
        "engineering": state_after.tech_engineering - state_before.tech_engineering,
        "knowledge": state_after.tech_knowledge - state_before.tech_knowledge,
    }
    for name, delta in tech_deltas.items():
        if delta >= TECH_BREAKTHROUGH_DELTA:
            drafts.append(
                {
                    "tags": list({*base_tags, "technology", f"tech_{name}"}),
                    "title": f"技术突破：{name}线跃升",
                    "summary": (
                        f"第{turn}回合，{name}技术线显著进步（结果{result_tier}）。"
                        f"缘于「{action_description}」，工匠与知识阶层获得新手段，"
                        f"可能在后续世代持续放大影响。"
                    ),
                    "importance_score": _IMPORTANCE["tech_breakthrough"],
                    "trigger": "tech_breakthrough",
                }
            )

    # 3) 领土大幅变化
    before_t = _total_territory(state_before)
    after_t = _total_territory(state_after)
    if before_t > 0:
        ratio = abs(after_t - before_t) / before_t
        if ratio >= TERRITORY_CHANGE_RATIO:
            direction = "扩张" if after_t > before_t else "收缩"
            drafts.append(
                {
                    "tags": list({*base_tags, "military", "territory"}),
                    "title": f"疆域{direction}",
                    "summary": (
                        f"第{turn}回合疆域显著{direction}，与「{action_description}」直接相关"
                        f"（结果{result_tier}）。边郡与核心区的治理压力随之改变。"
                    ),
                    "importance_score": _IMPORTANCE["territory"],
                    "trigger": "territory",
                }
            )

    # 4) 合法性危机
    leg = state_after.legitimacy_total()
    if leg < LEGITIMACY_CRISIS_THRESHOLD:
        drafts.append(
            {
                "tags": list({*base_tags, "political", "legitimacy"}),
                "title": "合法性危机",
                "summary": (
                    f"第{turn}回合总合法性跌入危局。"
                    f"在「{action_description}」之后，朝野对统治正当性的认同显著动摇，"
                    f"后续政令与征发都将更难推行。"
                ),
                "importance_score": _IMPORTANCE["legitimacy_crisis"],
                "trigger": "legitimacy_crisis",
            }
        )

    # 5) 稳定性极端事件
    blob = " ".join(events) + " " + (narrative or "")
    if any(k in blob for k in _EXTREME_EVENT_KEYWORDS) or state_after.stability < 20:
        if any(k in blob for k in _EXTREME_EVENT_KEYWORDS) or (
            state_before.stability - state_after.stability >= 15
        ):
            drafts.append(
                {
                    "tags": list({*base_tags, "political", "stability"}),
                    "title": "秩序震荡",
                    "summary": (
                        f"第{turn}回合出现叛乱/饥荒/瘟疫一类极端动荡迹象。"
                        f"与「{action_description}」（{result_tier}）相互牵连，"
                        f"民心与地方控制力受到重创。"
                    ),
                    "importance_score": _IMPORTANCE["stability_extreme"],
                    "trigger": "stability_extreme",
                }
            )

    # 6) 宗教变动
    if _religions_sig(state_before) != _religions_sig(state_after):
        drafts.append(
            {
                "tags": list({*base_tags, "cultural", "religion"}),
                "title": "宗教格局变动",
                "summary": (
                    f"第{turn}回合信仰版图改写，关联行动「{action_description}」。"
                    f"教权、祭祀与意识形态资源的再分配，将长期影响合法性与文化积累。"
                ),
                "importance_score": _IMPORTANCE["religion"],
                "trigger": "religion",
            }
        )

    # 补充 year/turn/snapshot 由调用方写入
    for d in drafts:
        d["turn"] = turn
        d["year"] = year
    return drafts


def create_landmarks_from_turn(
    store: MemoryStore,
    *,
    turn: int,
    year: float,
    state_before: CivState,
    state_after: CivState,
    domain_tags: list[str],
    action_description: str,
    result_tier: str,
    events: list[str] | None = None,
    narrative: str = "",
) -> list[LandmarkRecord]:
    """检测并写入本回合触发的 landmarks；embedding 字段留空。"""
    drafts = detect_landmark_events(
        turn=turn,
        year=year,
        state_before=state_before,
        state_after=state_after,
        domain_tags=domain_tags,
        action_description=action_description,
        result_tier=result_tier,
        events=events,
        narrative=narrative,
    )
    snap = snapshot_state(state_after)
    created: list[LandmarkRecord] = []
    for d in drafts:
        # 预留：将来在此调用 embed_text(d["summary"])
        emb = embed_text(d["summary"])
        record = LandmarkRecord(
            game_id=store.game_id,
            turn=turn,
            year=year,
            tags=sorted(set(d["tags"])),
            title=d["title"],
            summary=d["summary"],
            state_snapshot=snap,
            importance_score=int(d["importance_score"]),
            embedding=emb,
            embedding_model=None if emb is None else "glm-embedding-3",
        )
        created.append(store.add_landmark(record))
    return created


def format_landmarks_for_context(landmarks: list[LandmarkRecord]) -> str:
    """长期索引段落文本。"""
    if not landmarks:
        return "（无相关长期史事）"
    lines: list[str] = []
    for lm in landmarks:
        tags = "、".join(lm.tags)
        lines.append(f"· {lm.title}（第{lm.turn}回合，标签：{tags}）：{lm.summary}")
    return "\n".join(lines)


def query_landmarks_keyword(
    store: MemoryStore,
    domain_tags: list[str],
    *,
    limit: int = 5,
) -> list[LandmarkRecord]:
    """当前检索策略：关键词标签重叠。"""
    return store.query_landmarks_by_tags(domain_tags, limit=limit)


def query_landmarks_vector(
    store: MemoryStore,
    query_text: str,
    *,
    limit: int = 5,
) -> list[LandmarkRecord]:
    """将来的向量检索策略占位。"""
    _ = (store, query_text, limit)
    raise NotImplementedError(
        "向量检索尚未实现；请使用 query_landmarks_keyword。"
        "接入时在 embed_text() 生成 embedding 后按相似度排序。"
    )
