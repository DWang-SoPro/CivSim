"""新游戏开场叙事：完整状态输入、关闭 thinking 与 API 返回。"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

import pytest
from fastapi import HTTPException

from backend.api.game import NewGameRequest, new_game
from backend.api.sessions import sessions
from backend.llm import opening
from backend.llm.opening import (
    OPENING_MAX_CHARS,
    OPENING_MIN_CHARS,
    generate_opening_narrative,
    opening_character_count,
)
from backend.models.schemas import CivState
from backend.templates.civilizations import load_civ_state


VALID_OPENING = (
    "公元前一千年前后，这个王朝的人们散居在王城、田野与边地之间，靠农耕、贡赋和尚未完备的工程技艺维持生计。"
    "土地由国家授予，大量劳力仍要承担役使；宗族贵族掌握议事与传承权，血统、礼制和祖先信仰共同支撑王权。"
    "眼下社会尚称安定，人口与农地也足以支撑新政，但官僚组织仍然有限，边地与贵族之间的命令传递并不稳固。"
    "如何把粮食、民力和日渐积累的治理经验变成真正的国力，将决定这个文明能否走得更远。"
)


class FakeOpeningClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[list[dict[str, str]], dict[str, Any]]] = []

    async def call(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        self.calls.append((deepcopy(messages), dict(kwargs)))
        return self.responses.pop(0)


def test_new_game_generates_opening_from_complete_state_without_thinking(
    monkeypatch: Any,
) -> None:
    assert OPENING_MIN_CHARS <= opening_character_count(VALID_OPENING) <= OPENING_MAX_CHARS
    sessions.clear()
    fake = FakeOpeningClient([VALID_OPENING])
    monkeypatch.setattr(opening, "get_llm_client", lambda: fake)

    try:
        response = asyncio.run(
            new_game(NewGameRequest(template_id="zhou", seed=2026))
        )
        assert response.opening_narrative == VALID_OPENING
        assert response.seed == 2026
        assert sessions.get(response.game_id) is not None

        assert len(fake.calls) == 1
        messages, kwargs = fake.calls[0]
        assert kwargs["thinking"] is False
        assert kwargs["temperature"] == pytest.approx(0.7)
        assert kwargs["max_tokens"] == 512

        user_prompt = messages[-1]["content"]
        # 每个 CivState 顶层字段都应出现，不是只用文明名的薄提示。
        for field_name in CivState.model_fields:
            assert f'"{field_name}"' in user_prompt
        assert '"civ_name": "西周王朝"' in user_prompt
        assert '"religions"' in user_prompt
        assert '"accumulations"' in user_prompt
    finally:
        sessions.clear()


def test_opening_retries_once_when_first_draft_has_wrong_length() -> None:
    fake = FakeOpeningClient(["太短", f"```\n{VALID_OPENING}\n```"])
    result = asyncio.run(
        generate_opening_narrative(
            load_civ_state("zhou"),
            client=fake,
        )
    )

    assert result == VALID_OPENING
    assert len(fake.calls) == 2
    assert "偏短" in fake.calls[1][0][-1]["content"]
    assert "150–250" in fake.calls[1][0][-1]["content"]


def test_opening_accepts_soft_overage_near_target_max() -> None:
    """略超目标上限（如 252）不应开局失败。"""
    from backend.llm.opening import OPENING_ACCEPT_MAX_CHARS, opening_character_count

    # 构造刚好落在 251–ACCEPT_MAX 的文稿
    base = VALID_OPENING
    while opening_character_count(base) <= OPENING_MAX_CHARS:
        base += "余韵尚在。"
    assert OPENING_MAX_CHARS < opening_character_count(base) <= OPENING_ACCEPT_MAX_CHARS

    fake = FakeOpeningClient([base])
    result = asyncio.run(
        generate_opening_narrative(load_civ_state("zhou"), client=fake)
    )
    assert result == base
    assert len(fake.calls) == 1


def test_new_game_llm_failure_returns_503_without_orphan_session(
    monkeypatch: Any,
) -> None:
    sessions.clear()
    fake = FakeOpeningClient(["太短", "仍然太短", "还是太短"])
    monkeypatch.setattr(opening, "get_llm_client", lambda: fake)

    try:
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(new_game(NewGameRequest(template_id="zhou", seed=1)))
        assert exc_info.value.status_code == 503
        assert len(sessions) == 0
        assert len(fake.calls) == 3
    finally:
        sessions.clear()
