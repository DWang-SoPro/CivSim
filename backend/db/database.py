"""数据库连接管理（第一阶段占位）。"""

from __future__ import annotations

from typing import Optional

import asyncpg

from backend.config import settings

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """获取全局连接池。"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=settings.database_url)
    return _pool


async def close_pool() -> None:
    """关闭连接池。"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
