"""游戏会话 API：新建、行动菜单、存读档。"""

from __future__ import annotations

import secrets
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.sessions import GameSession, sessions
from backend.llm.client import LLMError
from backend.llm.opening import generate_opening_narrative
from backend.memory.store import MemoryStore
from backend.models.schemas import CivState
from backend.persistence.saves import (
    create_or_update_save,
    list_saves,
    load_save_into_session_data,
)
from backend.templates.actions import generate_action_menu
from backend.templates.civilizations import load_civ_state

router = APIRouter(prefix="/api/game", tags=["game"])


class NewGameRequest(BaseModel):
    """新建游戏请求。"""

    template_id: str
    seed: int | None = None


class NarrativeHistoryItem(BaseModel):
    """读档时附带的叙事历史条目。"""

    turn: int
    year: float
    text: str


class NewGameResponse(BaseModel):
    """新建 / 读档响应。"""

    game_id: str
    state: CivState
    seed: int
    opening_narrative: str
    history: list[NarrativeHistoryItem] | None = None
    status: str | None = None
    game_over_reason: str | None = None
    autosave_id: str | None = None


class ActionMenuItem(BaseModel):
    """单条可用行动。"""

    id: str
    name: str
    label: str
    domain: str
    domain_label: str
    description: str
    difficulty_hint: str
    suggested_input: str
    disabled: bool = False
    reason: Optional[str] = None


class ActionMenuResponse(BaseModel):
    """行动菜单响应。"""

    game_id: str
    items: list[ActionMenuItem]


class SaveGameRequest(BaseModel):
    """存档请求。"""

    slot_name: str | None = None
    autosave: bool = False


class SaveGameResponse(BaseModel):
    """存档响应。"""

    save_id: str
    saved_at: str
    slot_name: str | None = None


class SaveListItem(BaseModel):
    """存档列表项。"""

    save_id: str
    slot_name: str | None = None
    civ_name: str
    template_id: str
    turn: int
    year: float
    saved_at: str
    is_autosave: bool = False


class SaveListResponse(BaseModel):
    """存档列表。"""

    saves: list[SaveListItem]


def _build_session(
    *,
    game_id: str,
    state: CivState,
    store: MemoryStore,
    seed: int,
    status: str = "active",
    game_over_reason: str | None = None,
    autosave_id: str | None = None,
    opening_narrative: str | None = None,
    year_start: float | None = None,
    initial_population: int | None = None,
    peak_population: int | None = None,
    peak_territory: int | None = None,
) -> GameSession:
    return GameSession(
        game_id=game_id,
        state=state,
        store=store,
        seed=seed,
        status=status,  # type: ignore[arg-type]
        game_over_reason=game_over_reason,
        autosave_id=autosave_id,
        opening_narrative=opening_narrative,
        year_start=year_start if year_start is not None else state.year,
        initial_population=(
            initial_population if initial_population is not None else state.population
        ),
        peak_population=(
            peak_population if peak_population is not None else state.population
        ),
        peak_territory=(
            peak_territory
            if peak_territory is not None
            else state.territory_core + state.territory_frontier
        ),
    )


def _history_from_store(
    store: MemoryStore,
    opening: str,
    year0: float,
) -> list[NarrativeHistoryItem]:
    items: list[NarrativeHistoryItem] = []
    if opening:
        items.append(NarrativeHistoryItem(turn=0, year=year0, text=opening))
    for turn in store.get_all_turns():
        text = turn.narrative or turn.summary or ""
        if not text:
            continue
        items.append(
            NarrativeHistoryItem(
                turn=turn.turn,
                year=turn.year_end,
                text=text,
            )
        )
    return items


@router.post("/new", response_model=NewGameResponse)
async def new_game(request: NewGameRequest) -> NewGameResponse:
    """从文明模板创建一个进程内游戏会话。"""
    try:
        state = load_civ_state(request.template_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc.args[0])) from exc

    try:
        opening_narrative = await generate_opening_narrative(state)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    game_id = str(uuid4())
    seed = request.seed if request.seed is not None else secrets.randbits(32)
    session = _build_session(
        game_id=game_id,
        state=state,
        store=MemoryStore(game_id=game_id),
        seed=seed,
        opening_narrative=opening_narrative,
    )
    sessions.add(session)
    try:
        save_id, _ = create_or_update_save(
            session,
            slot_name=f"{state.civ_name}·自动存档",
            autosave=True,
            save_id=None,
        )
        session.autosave_id = save_id
    except Exception:
        pass
    return NewGameResponse(
        game_id=game_id,
        state=state,
        seed=seed,
        opening_narrative=opening_narrative,
        status=session.status,
        autosave_id=session.autosave_id,
    )


@router.get("/saves", response_model=SaveListResponse)
async def get_saves() -> SaveListResponse:
    """列出全部存档（新→旧）。"""
    rows = list_saves()
    return SaveListResponse(saves=[SaveListItem(**row) for row in rows])


@router.post("/load/{save_id}", response_model=NewGameResponse)
async def load_game(save_id: str) -> NewGameResponse:
    """从存档恢复为新的活跃会话（新 game_id）。"""
    try:
        data = load_save_into_session_data(save_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc

    game_id = str(uuid4())
    store = data["store"]
    store.game_id = game_id
    state: CivState = data["state"]
    opening = str(data.get("opening_narrative") or "")
    status = str(data.get("status") or "active")
    game_over_reason = data.get("game_over_reason")

    session = _build_session(
        game_id=game_id,
        state=state,
        store=store,
        seed=int(data["seed"]),
        status=status if status in {"active", "game_over", "awaiting_clarification"} else "active",
        game_over_reason=game_over_reason if status == "game_over" else None,
        autosave_id=save_id if data.get("is_autosave") else None,
        opening_narrative=opening,
        year_start=data.get("year_start"),
        initial_population=data.get("initial_population"),
        peak_population=data.get("peak_population"),
        peak_territory=data.get("peak_territory"),
    )
    if session.status != "game_over":
        session.status = "active"
        session.game_over_reason = None
    sessions.add(session)

    if not opening:
        turns = store.get_all_turns()
        if turns:
            opening = turns[-1].narrative or turns[-1].summary or "（已读档）"
        else:
            y = int(abs(state.year))
            opening = f"{state.civ_name}的史册自约{y}年前后续写。"

    history = _history_from_store(store, opening if state.turn == 0 else opening, state.year)
    # 若有回合记录，开局叙事用存档里的 opening；历史条目去重 turn0
    if store.get_all_turns() and opening:
        history = _history_from_store(store, opening, data.get("year_start") or state.year)

    return NewGameResponse(
        game_id=game_id,
        state=state,
        seed=session.seed,
        opening_narrative=opening,
        history=history,
        status=session.status,
        game_over_reason=session.game_over_reason,
        autosave_id=session.autosave_id,
    )


@router.get("/{game_id}/menu", response_model=ActionMenuResponse)
async def get_action_menu(game_id: UUID) -> ActionMenuResponse:
    """返回当前状态下可用的行动建议菜单。"""
    key = str(game_id)
    session = sessions.get(key)
    if session is None:
        raise HTTPException(status_code=404, detail="游戏不存在")
    items = [ActionMenuItem(**item) for item in generate_action_menu(session.state)]
    return ActionMenuResponse(game_id=key, items=items)


@router.post("/{game_id}/save", response_model=SaveGameResponse)
async def save_game(game_id: UUID, request: SaveGameRequest) -> SaveGameResponse:
    """将当前局序列化写入 SQLite 存档。"""
    key = str(game_id)
    session = sessions.get(key)
    if session is None:
        raise HTTPException(status_code=404, detail="游戏不存在")

    if request.autosave:
        slot_name = request.slot_name or f"{session.state.civ_name}·自动存档"
        save_id, saved_at = create_or_update_save(
            session,
            slot_name=slot_name,
            autosave=True,
            save_id=session.autosave_id,
        )
        session.autosave_id = save_id
    else:
        slot_name = request.slot_name or (
            f"{session.state.civ_name}·第{session.state.turn}回合"
        )
        save_id, saved_at = create_or_update_save(
            session,
            slot_name=slot_name,
            autosave=False,
            save_id=None,
        )
    return SaveGameResponse(save_id=save_id, saved_at=saved_at, slot_name=slot_name)


@router.post("/{game_id}/debug/end", response_model=dict[str, Any])
async def debug_force_game_over(game_id: UUID) -> dict[str, Any]:
    """开发用：强制触发终局并广播完整 game_over 帧（便于 UI 验收）。"""
    from backend.api.websocket import ws_hub
    from backend.llm.gameover_lesson import (
        build_game_over_payload,
        generate_historical_lesson,
        landmarks_as_achievements,
    )

    key = str(game_id)
    session = sessions.get(key)
    if session is None:
        raise HTTPException(status_code=404, detail="游戏不存在")

    reason = "civilization_collapse"
    session.status = "game_over"
    session.game_over_reason = reason
    achievements = landmarks_as_achievements(session.store.get_all_landmarks())
    lesson = await generate_historical_lesson(
        session.state,
        reason=reason,
        total_turns=session.state.turn,
        year_start=session.year_start,
        year_end=session.state.year,
        achievements=[str(a.get("title") or "") for a in achievements],
    )
    payload = build_game_over_payload(
        session.state,
        reason=reason,
        year_start=session.year_start,
        peak_population=session.peak_population,
        peak_territory=session.peak_territory,
        achievements=achievements,
        historical_lesson=lesson,
    )
    await ws_hub.broadcast(
        key,
        {
            "type": "game_over",
            "turn": session.state.turn,
            "stream_id": "debug-end",
            "payload": payload,
        },
    )
    return {"ok": True, "payload": payload}
