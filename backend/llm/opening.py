"""新游戏的文明开场史官叙事。"""

from __future__ import annotations

import json
from typing import Protocol

from backend.llm.client import LLMError, get_llm_client, strip_code_fence
from backend.models.schemas import CivState

OPENING_MIN_CHARS = 150
OPENING_MAX_CHARS = 250
OPENING_MAX_ATTEMPTS = 2

OPENING_SYSTEM_PROMPT = """\
你是文明模拟游戏的史官旁白。根据用户提供的完整初始 CivState，为这个文明写一段开场背景。

严格要求：
- 正文 150–250 个中文字符，一到两段。
- 用清楚的现代白话，保留少量史官的沉稳语气；不写文言，不用生僻词。
- 自然交代时代与文明、人口土地与生产基础、统治与社会结构，以及当前最值得玩家留意的机遇或隐忧。
- 要综合整份状态，不要把字段逐项念成清单，不要直接暴露英文字段名。
- 不得发明输入中没有的具体君主、战争、灾害或确定历史事件。
- 只输出正文；不要标题、Markdown、引号、字数说明或额外解释。
"""


class OpeningLLMClient(Protocol):
    """开场生成所需的最小客户端接口，便于离线测试注入。"""

    async def call(
        self,
        messages: list[dict[str, str]],
        *,
        thinking: bool = False,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str: ...


def opening_character_count(text: str) -> int:
    """统计开场正文的非空白字符数。"""
    return len("".join(text.split()))


def build_opening_user_prompt(state: CivState) -> str:
    """将完整初始状态序列化为模型输入。"""
    state_json = json.dumps(
        state.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    return f"""\
请仅依据下列完整初始状态写开场背景。

【初始 CivState】
{state_json}
"""


async def generate_opening_narrative(
    state: CivState,
    *,
    client: OpeningLLMClient | None = None,
) -> str:
    """生成 150–250 字的白话史官开场。

    默认使用项目配置的 ``LLMClient``（当前默认模型为
    ``deepseek-v4-flash``），并显式关闭 thinking。首次字数不合格时
    允许模型自我修订一次，避免机械截断正文。
    """
    llm = client or get_llm_client()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": OPENING_SYSTEM_PROMPT},
        {"role": "user", "content": build_opening_user_prompt(state)},
    ]

    last_count = 0
    for attempt in range(OPENING_MAX_ATTEMPTS):
        raw = await llm.call(
            messages,
            thinking=False,
            temperature=0.7,
            max_tokens=512,
        )
        narrative = strip_code_fence(str(raw)).strip()
        last_count = opening_character_count(narrative)
        if OPENING_MIN_CHARS <= last_count <= OPENING_MAX_CHARS:
            return narrative

        if attempt + 1 < OPENING_MAX_ATTEMPTS:
            messages.extend(
                [
                    {"role": "assistant", "content": narrative},
                    {
                        "role": "user",
                        "content": (
                            f"上一稿为 {last_count} 个非空白字符，不符合 "
                            f"{OPENING_MIN_CHARS}–{OPENING_MAX_CHARS} 字要求。"
                            "请在不改变事实的前提下重写，仍只输出正文。"
                        ),
                    },
                ]
            )

    raise LLMError(
        "开场叙事字数校验失败："
        f"要求 {OPENING_MIN_CHARS}–{OPENING_MAX_CHARS} 字，实际 {last_count} 字"
    )
