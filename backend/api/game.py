"""游戏 CRUD：新建 / 存档 / 读档（第一阶段占位）。"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/game", tags=["game"])


@router.get("/health")
async def game_health() -> dict[str, str]:
    """游戏模块健康检查占位。"""
    return {"module": "game", "status": "stub"}
