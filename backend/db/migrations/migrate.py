"""简易迁移脚本：执行 migrations 目录下按文件名排序的 SQL。

用法：
  DATABASE_URL=postgresql://... python -m backend.db.migrations.migrate
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

from backend.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parent


async def run_migrations(dsn: str | None = None) -> None:
    """按文件名顺序执行全部 .sql 迁移。"""
    dsn = dsn or settings.database_url
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        applied = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM schema_migrations")
        }
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for path in sql_files:
            if path.name in applied:
                print(f"skip  {path.name}")
                continue
            sql = path.read_text(encoding="utf-8")
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations(filename) VALUES($1)",
                    path.name,
                )
            print(f"apply {path.name}")
    finally:
        await conn.close()


def main() -> None:
    """命令行入口。"""
    try:
        asyncio.run(run_migrations())
    except Exception as exc:  # noqa: BLE001
        print(f"迁移失败: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
