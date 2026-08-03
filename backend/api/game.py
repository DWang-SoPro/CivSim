"""游戏会话 API。"""

from __future__ import annotations

import secrets
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.sessions import GameSession, sessions
from backend.llm.client import LLMError
from backend.llm.opening import generate_opening_narrative
from backend.memory.store import MemoryStore
from backend.models.schemas import CivState
from backend.templates.civilizations import load_civ_state

router = APIRouter(prefix="/api/game", tags=["game"])


class NewGameRequest(BaseModel):
    """新建游戏请求。"""

    template_id: str
    seed: int | None = None


class NewGameResponse(BaseModel):
    """新建游戏响应。"""

    game_id: str
    state: CivState
    seed: int
    opening_narrative: str


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
    # 32 位整数可被浏览器 JavaScript Number 精确表示。
    seed = request.seed if request.seed is not None else secrets.randbits(32)
    session = GameSession(
        game_id=game_id,
        state=state,
        store=MemoryStore(game_id=game_id),
        seed=seed,
    )
    sessions.add(session)
    return NewGameResponse(
        game_id=game_id,
        state=state,
        seed=seed,
        opening_narrative=opening_narrative,
    )
