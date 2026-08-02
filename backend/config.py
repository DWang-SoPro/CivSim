"""配置模块：LLM 模型、数据库连接、引擎参数等。"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env_first(*names: str, default: str = "") -> str:
    """按优先级读取环境变量，取第一个非空值。"""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


@dataclass(frozen=True)
class Settings:
    """应用配置，从环境变量读取。"""

    database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost/civsim")
    # DeepSeek API：优先 DEEPSEEK_API_KEY，兼容旧名 LLM_API_KEY
    deepseek_api_key: str = _env_first("DEEPSEEK_API_KEY", "LLM_API_KEY")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    # DeepSeek V4 Flash（thinking 用 extra_body 开关，不再用 deepseek-reasoner）
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-v4-flash")
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))

    @property
    def llm_api_key(self) -> str:
        """兼容旧字段名。"""
        return self.deepseek_api_key


settings = Settings()
