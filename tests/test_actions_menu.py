"""行动菜单生成测试。"""

from __future__ import annotations

from backend.templates.actions import (
    ALL_ACTIONS,
    generate_action_menu,
    menu_stats_for_state,
)
from backend.templates.civilizations import load_civ_state


def test_action_library_size_and_domains() -> None:
    assert 20 <= len(ALL_ACTIONS) <= 35
    domains = {a.domain for a in ALL_ACTIONS}
    assert domains >= {
        "economic",
        "political",
        "military",
        "cultural",
        "technology",
        "composite",
    }


def test_zhou_opening_has_enough_actions() -> None:
    state = load_civ_state("zhou")
    menu = generate_action_menu(state)
    assert len(menu) >= 10
    stats = menu_stats_for_state(state)
    assert stats["available_count"] == len(menu)
    assert all(item["difficulty_hint"] in {"容易", "中等", "困难", "极难"} for item in menu)
    # 开局不应放出铸造货币 / 引进异域技艺等明显超前项
    names = {item["name"] for item in menu}
    assert "铸造货币" not in names
    assert "引进异域技艺" not in names
    assert "兴修水利" in names
