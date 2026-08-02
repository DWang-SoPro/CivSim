"""LLM 调用包：客户端、任务拆分、意图解析、知识评估、叙事、摘要。"""

from backend.llm.client import LLMClient, LLMError, get_llm_client
from backend.llm.intent_parser import ActionScale, IntentResult, parse_intent
from backend.llm.narrator import (
    Importance,
    NarrationInput,
    ResultTier,
    format_year_label,
    narrate,
    narrate_stream,
)
from backend.llm.task_splitter import TaskSplitResult, split_tasks

__all__ = [
    "LLMClient",
    "LLMError",
    "get_llm_client",
    "ActionScale",
    "IntentResult",
    "parse_intent",
    "TaskSplitResult",
    "split_tasks",
    "NarrationInput",
    "ResultTier",
    "Importance",
    "format_year_label",
    "narrate",
    "narrate_stream",
]
