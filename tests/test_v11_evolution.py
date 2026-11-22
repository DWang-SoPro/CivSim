"""v1.1 全面进化验收测试：数值修复、28项国策、制度演变、被动事件、宿主模型桥与删档/问史。"""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from backend.engine.action_resolver import _ACTION_EFFECTS, _apply_tier_and_dilution
from backend.engine.passive_events import resolve_passive_event
from backend.models.schemas import (
    ActionResultTier,
    CivState,
    DecisionStructure,
    LandSystem,
    SurplusExtraction,
)
from backend.singleplayer.model import HostModelBridge
from backend.singleplayer.rules import ALIASES, parse_local, resolve_local
from backend.singleplayer.store import GameError, LocalGames
from backend.templates.actions import ALL_ACTIONS, generate_full_action_catalog
from backend.templates.civilizations import load_civ_state, validate_production_relations


def test_disaster_tier_never_flips_costs_into_rewards() -> None:
    """军事惨败不得反号白送人口与稳定；赈济成功应切实降低阶级矛盾。"""
    mil_base = _ACTION_EFFECTS["征伐边疆"]
    disaster = _apply_tier_and_dilution(mil_base, ActionResultTier.DISASTER, 1.0)
    assert disaster["population_pct"] < mil_base["population_pct"] < 0.0
    assert disaster["stability"] < mil_base["stability"] < 0.0
    assert disaster["class_tension"] > mil_base["class_tension"] > 0.0
    assert disaster["authority"] < 0.0
    assert disaster["territory_frontier"] < 0.0

    relief_base = _ACTION_EFFECTS["赈济饥民"]
    relief_ok = _apply_tier_and_dilution(relief_base, ActionResultTier.SUCCESS, 1.0)
    relief_bad = _apply_tier_and_dilution(relief_base, ActionResultTier.DISASTER, 1.0)
    assert relief_ok["class_tension"] < -0.04
    assert relief_bad["class_tension"] > 0.0


@pytest.mark.parametrize("tid", ["sumer", "egypt", "harappa", "babylon", "zhou", "greece"])
def test_all_six_templates_have_healthy_opening_decrees_and_relief(tid: str) -> None:
    """修复苏美尔与希腊开局死锁：六大文明第 0 回合均至少有 8 项可执行国策，且能开市、兴水利、垦荒、赈灾。"""
    state = load_civ_state(tid)
    catalog = generate_full_action_catalog(state)
    assert len(catalog) == len(ALL_ACTIONS) == len(ALIASES) == 28
    available_names = {item["name"] for item in catalog if item["available"]}
    assert len(available_names) >= 8
    assert {"开垦荒地", "兴修水利", "修建粮仓", "赈济饥民"} <= available_names


def test_offline_28_decrees_aliases_and_varied_chronicle() -> None:
    """离线词表覆盖全部 28 项国策（含开垦农田等同义词），连续多回合叙事有变化。"""
    orders, clarify = parse_local("同时开垦农田、练兵、办学")
    assert clarify is None
    assert [a.name for a, _ in orders] == ["开垦荒地", "操练士卒", "设立学宫"]

    state = load_civ_state("zhou")
    narratives: list[str] = []
    for i in range(4):
        single, _ = parse_local("兴修水利")
        res = asyncio.run(resolve_local(state, "兴修水利", single, seed=100 + i))
        assert res.state_after is not None
        from backend.singleplayer.rules import chronicle
        narratives.append(chronicle(res))
        state = res.state_after
    assert len(set(narratives)) >= 2


def test_structural_evolution_territory_granary_and_institutions() -> None:
    """开垦荒地扩核心耕地、修建粮仓增储粮、推行郡县推动田制与官僚政体演进。"""
    state = load_civ_state("babylon").model_copy(
        update={"bureaucratization": 0.48, "tech_knowledge": 1.6, "authority": 65.0}
    )
    core_before = state.territory_core
    frontier_before = state.territory_frontier
    reserve_before = state.grain_reserve

    orders, clarify = parse_local("开垦荒地、修建粮仓、推行郡县")
    assert clarify is None
    # 多次尝试不同种子以覆盖成功档位，验证制度跃迁合法性
    transitioned = False
    for seed in range(1, 25):
        res = asyncio.run(resolve_local(state, "开垦荒地、修建粮仓、推行郡县", orders, seed=seed))
        after = res.state_after
        assert after is not None
        ok, issues = validate_production_relations(after)
        assert ok, issues
        if (
            after.land_system == LandSystem.STATE_GRANT
            and after.polity.decision_structure == DecisionStructure.BUREAUCRACY
        ):
            assert after.territory_core > core_before
            assert after.territory_frontier < frontier_before
            assert after.grain_reserve > reserve_before
            transitioned = True
            break
    assert transitioned

    # 开设市集解锁关市商税
    market_state = load_civ_state("harappa")
    assert SurplusExtraction.COMMERCIAL_TAX not in market_state.surplus_extraction
    m_orders, _ = parse_local("开设市集")
    for seed in range(1, 20):
        m_res = asyncio.run(resolve_local(market_state, "开设市集", m_orders, seed=seed))
        if SurplusExtraction.COMMERCIAL_TAX in m_res.state_after.surplus_extraction:
            ok, issues = validate_production_relations(m_res.state_after)
            assert ok, issues
            break
    else:
        pytest.fail("开设市集应在商业底蕴满足时解锁商税")


def test_passive_event_determinism_and_granary_mitigation() -> None:
    """第 3 回合起可触发确定性随机事件，且充裕官仓储粮能平粜化解旱涝灾荒。"""
    rich_granary = load_civ_state("zhou").model_copy(update={"turn": 4, "grain_reserve": 0.45})
    empty_granary = rich_granary.model_copy(update={"grain_reserve": 0.02})

    found_calamity_seed = None
    import random
    for seed in range(500):
        ev = resolve_passive_event(rich_granary, 2.0, rng=random.Random(seed))
        if ev is not None and ev.id == "natural_calamity":
            found_calamity_seed = seed
            break
    assert found_calamity_seed is not None

    mitigated = resolve_passive_event(rich_granary, 2.0, rng=random.Random(found_calamity_seed))
    unmitigated = resolve_passive_event(empty_granary, 2.0, rng=random.Random(found_calamity_seed))
    assert mitigated is not None and mitigated.mitigated is True
    assert unmitigated is not None and unmitigated.mitigated is False
    assert mitigated.state_after.population == rich_granary.population
    assert unmitigated.state_after.population < empty_granary.population
    # 相同种子完全可复现
    again = resolve_passive_event(rich_granary, 2.0, rng=random.Random(found_calamity_seed))
    assert again == mitigated


def test_legacy_100_save_compat_delete_and_consult(tmp_path) -> None:
    """兼容无 grain_reserve 的 1.0.0 旧存档 JSON，且支持幂等删档与深度问史官。"""
    db_path = tmp_path / "saves.sqlite3"
    store = LocalGames(db_path)
    g1 = store.mutate("new", {"templateId": "greece", "requestId": "new-1"})
    g2 = store.mutate("new", {"templateId": "zhou", "requestId": "new-2"})

    # 模拟 1.0.0 旧版不含 grain_reserve 字段的 JSON 存档
    with store.connect() as db, db:
        row = db.execute("SELECT state FROM positions WHERE game=? AND turn=0", (g1["gameId"],)).fetchone()
        legacy_dict = json.loads(row["state"])
        legacy_dict.pop("grain_reserve", None)
        db.execute("UPDATE positions SET state=? WHERE game=? AND turn=0", (json.dumps(legacy_dict), g1["gameId"]))

    loaded = store.get(g1["gameId"])
    assert loaded["panel"]["indicators"][0]["id"] == "grain_reserve"
    assert len(loaded["availableDecrees"]) == 28

    # 深度问史官不推进回合
    ans1 = store.consult(g1["gameId"], "当前国势有何隐忧与建议？")
    assert ans1["turn"] == 0 and ans1["source"] == "local" and "粮食供需比" in ans1["answer"]
    ans2 = store.consult(g1["gameId"], "现行田制与政体如何？")
    assert "自耕小农" in ans2["answer"]

    # 幂等删除存档
    deleted = store.mutate("delete", {"gameId": g2["gameId"], "requestId": "del-g2"})
    assert deleted["deletedGameId"] == g2["gameId"]
    assert [item["gameId"] for item in deleted["games"]] == [g1["gameId"]]
    assert store.mutate("delete", {"gameId": g2["gameId"], "requestId": "del-g2"}) == deleted
    with pytest.raises(GameError, match="找不到"):
        store.get(g2["gameId"])


def test_host_model_bridge_auto_detect_and_mode_toggle(tmp_path, monkeypatch) -> None:
    """万相宿主模型桥：自动探测可用状态、支持一键切回离线规则、并在宿主离线时自动兜底。"""
    import io
    import os
    import urllib.request

    state_flag = {"available": True, "model": "wanxiang-pro"}
    secret = "h" * 40

    class FakeResp(io.BytesIO):
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()

    def fake_urlopen(req, timeout=1.5):
        assert req.full_url == "http://127.0.0.1:18999/api/phases/civsim-llm/v1/status"
        if req.get_header("Authorization") != f"Bearer {secret}":
            raise OSError("forbidden")
        return FakeResp(json.dumps(state_flag).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.delenv("CIVSIM_MODEL_MODE", raising=False)
    monkeypatch.setenv("CIVSIM_HOST_MODEL_URL", "http://127.0.0.1:18999/api/phases/civsim-llm/v1")
    monkeypatch.setenv("CIVSIM_HOST_MODEL_TOKEN", secret)
    bridge = HostModelBridge.from_environment()
    assert bridge is not None
    # Token 已从环境变量弹出，不残留在 os.environ
    assert "CIVSIM_HOST_MODEL_TOKEN" not in os.environ

    store = LocalGames(tmp_path / "host.db", host_bridge=bridge)
    cat = store.catalog_info()
    assert cat["mode"] == "model" and cat["modelName"] == "wanxiang-pro" and cat["canToggleModel"] is True

    # 玩家手动切换为离线规则
    offline_cat = store.set_mode("offline")
    assert offline_cat["mode"] == "offline" and offline_cat["canToggleModel"] is True

    # 切回 auto，当宿主未登录/无模型时自动退回离线规则
    store.set_mode("auto")
    state_flag["available"] = False
    fallback_cat = store.catalog_info()
    assert fallback_cat["mode"] == "offline"
