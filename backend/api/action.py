"""行动处理主入口（第一阶段占位）。

后续阶段：意图解析 → 数学引擎 → 叙事生成。
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/game", tags=["action"])
