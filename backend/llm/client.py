"""LLM 调用封装（OpenAI 兼容接口，对接 DeepSeek V4 Flash）。

要点：
- thinking 模式经 extra_body 传递，不是顶层参数
- JSON mode 用 response_format={"type": "json_object"}
- thinking 模式下忽略 temperature/top_p；只取 content，忽略 reasoning_content
- 单次独立调用，不做多轮；JSON 解析失败或 API 报错最多重试 3 次
- thinking 的 reasoning tokens 计入 max_tokens；过小会得到空 content
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any, TypeVar

from openai import APIError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from backend.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# 判断类 JSON：thinking 会占 completion 额度，默认给足余量
_DEFAULT_JSON_MAX_TOKENS = 16384

# 剥离模型偶发包裹的 Markdown 代码块
_CODE_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


class LLMError(Exception):
    """LLM 调用或输出校验最终失败。"""


def strip_code_fence(text: str) -> str:
    """若整段被 ```json ... ``` 包裹则剥掉，否则原样返回。"""
    text = text.strip()
    match = _CODE_FENCE_RE.match(text)
    if match:
        return match.group(1).strip()
    return text


def parse_json_object(text: str) -> dict[str, Any]:
    """将模型文本解析为 JSON 对象。"""
    cleaned = strip_code_fence(text)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError(f"期望 JSON 对象，实际为 {type(data).__name__}")
    return data


class LLMClient:
    """DeepSeek V4 Flash 异步客户端。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.deepseek_api_key
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        self.max_retries = max_retries if max_retries is not None else settings.llm_max_retries
        if not self.api_key:
            raise LLMError(
                "未设置 DEEPSEEK_API_KEY。请在环境变量或 .env 中配置 API Key。"
            )
        self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def call(
        self,
        messages: list[dict[str, str]],
        *,
        thinking: bool = False,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """统一非流式调用，返回助手 content 文本。

        thinking=True 时经 extra_body 开启思考模式；此时不传 temperature。
        只读取 message.content，忽略同级 reasoning_content。
        """
        last_error: Exception | None = None
        attempts = max(1, self.max_retries)

        for attempt in range(1, attempts + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "extra_body": {
                        "thinking": {"type": "enabled" if thinking else "disabled"},
                    },
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens
                # thinking 模式下 temperature/top_p 不生效，故仅在关闭时传入
                if not thinking and temperature is not None:
                    kwargs["temperature"] = temperature

                response = await self._client.chat.completions.create(**kwargs)
                message = response.choices[0].message
                content = message.content
                if content is None or not str(content).strip():
                    raise LLMError("模型返回空 content（可能 max_tokens 过小截断了思考）")
                return str(content)
            except (APIError, RateLimitError, LLMError, TimeoutError, OSError) as exc:
                last_error = exc
                logger.warning(
                    "LLM 调用失败 (%s/%s): %s", attempt, attempts, exc
                )

        raise LLMError(f"LLM 调用在 {attempts} 次尝试后仍失败: {last_error}")

    async def call_json(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        *,
        max_tokens: int | None = _DEFAULT_JSON_MAX_TOKENS,
    ) -> T:
        """判断类任务便捷方法：开启 thinking + JSON mode，并用 Pydantic 校验。

        JSON 解析失败或校验失败会重试（计入 max_retries）。
        DeepSeek thinking+JSON 偶发空 content：同一次尝试内自动降级为关闭 thinking。
        """
        last_error: Exception | None = None
        attempts = max(1, self.max_retries)
        token_budget = (
            max_tokens if max_tokens is not None else _DEFAULT_JSON_MAX_TOKENS
        )

        for attempt in range(1, attempts + 1):
            try:
                raw = await self._raw_once(
                    messages,
                    thinking=True,
                    json_mode=True,
                    max_tokens=token_budget,
                    # 结构化判定不需要高强度长推理，降低空 content 概率
                    reasoning_effort="low",
                )
                data = parse_json_object(raw)
                return response_model.model_validate(data)
            except LLMError as exc:
                last_error = exc
                if "空 content" not in str(exc):
                    logger.warning(
                        "call_json 失败 (%s/%s): %s", attempt, attempts, exc
                    )
                    continue
                # thinking 耗尽预算或 JSON 偶发空答：降级为非 thinking 再试一次
                logger.warning(
                    "call_json 空 content，降级关闭 thinking 重试 (%s/%s): %s",
                    attempt,
                    attempts,
                    exc,
                )
                try:
                    raw = await self._raw_once(
                        messages,
                        thinking=False,
                        json_mode=True,
                        max_tokens=token_budget,
                        temperature=0.2,
                    )
                    data = parse_json_object(raw)
                    return response_model.model_validate(data)
                except (
                    APIError,
                    RateLimitError,
                    LLMError,
                    TimeoutError,
                    OSError,
                    json.JSONDecodeError,
                    ValidationError,
                    ValueError,
                ) as fallback_exc:
                    last_error = fallback_exc
                    logger.warning(
                        "call_json 降级重试仍失败 (%s/%s): %s",
                        attempt,
                        attempts,
                        fallback_exc,
                    )
            except (
                APIError,
                RateLimitError,
                TimeoutError,
                OSError,
                json.JSONDecodeError,
                ValidationError,
                ValueError,
            ) as exc:
                last_error = exc
                logger.warning(
                    "call_json 失败 (%s/%s): %s", attempt, attempts, exc
                )

        raise LLMError(
            f"call_json 在 {attempts} 次尝试后仍失败"
            f"（模型={response_model.__name__}）: {last_error}"
        )

    async def call_text_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.8,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """叙事类便捷方法：关闭 thinking + 流式输出，逐块 yield 文本。

        不使用 JSON mode；只取 delta.content，忽略 reasoning_content。
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "extra_body": {
                "thinking": {"type": "disabled"},
            },
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        try:
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                piece = getattr(delta, "content", None)
                if piece:
                    yield str(piece)
        except (APIError, RateLimitError, TimeoutError, OSError) as exc:
            raise LLMError(f"流式调用失败: {exc}") from exc

    async def _raw_once(
        self,
        messages: list[dict[str, str]],
        *,
        thinking: bool,
        json_mode: bool,
        max_tokens: int | None,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
    ) -> str:
        """单次 API 调用（无内部重试），供 call_json 外层重试使用。"""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "extra_body": {
                "thinking": {"type": "enabled" if thinking else "disabled"},
            },
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if not thinking and temperature is not None:
            kwargs["temperature"] = temperature
        # V4：thinking 开启时可压低推理强度，减少 reasoning 吃光 max_tokens
        if thinking and reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message
        content = message.content
        if content is None or not str(content).strip():
            finish = getattr(choice, "finish_reason", None)
            usage = getattr(response, "usage", None)
            reasoning = getattr(message, "reasoning_content", None)
            reasoning_len = len(str(reasoning)) if reasoning else 0
            usage_bits = ""
            if usage is not None:
                completion = getattr(usage, "completion_tokens", None)
                details = getattr(usage, "completion_tokens_details", None)
                reasoning_tokens = (
                    getattr(details, "reasoning_tokens", None) if details else None
                )
                usage_bits = (
                    f", completion_tokens={completion}"
                    f", reasoning_tokens={reasoning_tokens}"
                )
            raise LLMError(
                "模型返回空 content"
                f"（thinking={thinking}, finish_reason={finish}"
                f", reasoning_chars={reasoning_len}{usage_bits}）"
            )
        return str(content)


_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """获取进程内默认客户端（惰性创建）。"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
