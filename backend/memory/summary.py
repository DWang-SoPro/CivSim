"""第二层 — 中期摘要：每 5 回合用 V4 Flash 压缩最近 5 回合。"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from backend.llm.client import LLMClient, get_llm_client
from backend.llm.narrator import format_year_label
from backend.memory.recent import format_one_turn
from backend.memory.store import MemoryStore, SummaryRecord, TurnRecord

SUMMARY_INTERVAL = 5  # 第 5、10、15… 回合触发
SUMMARY_WORD_HINT = "200-300"


class MidSummaryResult(BaseModel):
    """中期摘要 LLM 结构化输出。"""

    content: str = Field(..., min_length=40, description="200–300 字纯文本摘要")
    domain_frequencies: dict[str, int] = Field(
        default_factory=dict,
        description="各行动领域出现频次，如 political: 2",
    )

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        text = v.strip()
        if not text:
            raise ValueError("摘要 content 不能为空")
        return text

    @field_validator("domain_frequencies", mode="before")
    @classmethod
    def normalize_freqs(cls, v: Any) -> dict[str, int]:
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("domain_frequencies 必须是对象")
        out: dict[str, int] = {}
        for key, val in v.items():
            try:
                out[str(key)] = int(val)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"domain_frequencies[{key}] 非法") from exc
        return out


SUMMARY_SYSTEM_PROMPT = """\
你是文明史编纂官，负责把最近若干回合的完整记录压缩成中期历史摘要。

【任务】
压缩为一段 200–300 字的纯文本摘要（中文）。

【必须保留】
1. 这几轮中最重要的 1–3 件事及其因果关系
2. 各维度的主要变化方向（上升 / 下降 / 稳定），不要写具体数字
3. 每轮行动所属的领域标签（用于积累值追踪；可在文中自然点明）
4. 任何可能在未来产生长期影响的种子事件

【不要保留】
数值细节、叙事修辞、重复信息、逐回合流水账

【输出】
只返回 JSON，不要 Markdown 代码块，不要解释文字。结构如下：
{
  "content": "200到300字的纯文本摘要……",
  "domain_frequencies": {
    "political": 1,
    "economic": 2,
    "military": 0,
    "cultural": 0,
    "technology": 1,
    "composite": 0
  }
}
domain_frequencies 统计本批回合中各领域出现次数（按回合主领域计；多领域回合可记多个）。
"""


def should_trigger_summary(current_turn: int, interval: int = SUMMARY_INTERVAL) -> bool:
    """第 5、10、15… 回合触发。"""
    return current_turn > 0 and current_turn % interval == 0


def _count_domain_frequencies(turns: list[TurnRecord]) -> dict[str, int]:
    freqs: dict[str, int] = {
        "political": 0,
        "economic": 0,
        "military": 0,
        "cultural": 0,
        "technology": 0,
        "composite": 0,
    }
    for t in turns:
        for tag in t.domain_tags:
            key = tag.lower()
            if key in freqs:
                freqs[key] += 1
            else:
                freqs[key] = freqs.get(key, 0) + 1
    return freqs


def build_summary_user_prompt(
    civ_name: str,
    turns: list[TurnRecord],
) -> str:
    """组装摘要压缩的用户提示。"""
    if not turns:
        raise ValueError("无回合可供摘要")
    year_start = format_year_label(turns[0].year_start)
    year_end = format_year_label(turns[-1].year_end)
    body = "\n\n".join(format_one_turn(t) for t in turns)
    # 附上完整叙事便于因果抽取（近期 format 只截了 80 字）
    narratives = []
    for t in turns:
        narratives.append(
            f"--- 第{t.turn}回合叙事全文 ---\n{(t.narrative or '（无）').strip()}"
        )
    return f"""\
以下是{civ_name}最近{len(turns)}轮（{year_start}—{year_end}）的完整记录。
请按系统要求压缩为 {SUMMARY_WORD_HINT} 字摘要，并返回 JSON。

【回合摘要条目】
{body}

【叙事全文】
{chr(10).join(narratives)}
"""


async def compress_turns(
    civ_name: str,
    turns: list[TurnRecord],
    *,
    client: LLMClient | None = None,
) -> MidSummaryResult:
    """调用 V4 Flash（thinking + JSON）压缩回合记录。"""
    llm = client or get_llm_client()
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": build_summary_user_prompt(civ_name, turns)},
    ]
    result = await llm.call_json(messages, MidSummaryResult)
    # 若模型漏了频次，用本地统计补全
    if not result.domain_frequencies:
        result = MidSummaryResult(
            content=result.content,
            domain_frequencies=_count_domain_frequencies(turns),
        )
    return result


async def maybe_create_summary(
    store: MemoryStore,
    *,
    current_turn: int,
    civ_name: str,
    client: LLMClient | None = None,
    interval: int = SUMMARY_INTERVAL,
) -> Optional[SummaryRecord]:
    """若 current_turn 为 interval 倍数，压缩最近 interval 回合并入库。"""
    if not should_trigger_summary(current_turn, interval=interval):
        return None
    turn_end = current_turn
    turn_start = current_turn - interval + 1
    turns = store.get_turns_in_range(turn_start, turn_end)
    if not turns:
        return None
    compressed = await compress_turns(civ_name, turns, client=client)
    record = SummaryRecord(
        game_id=store.game_id,
        turn_start=turn_start,
        turn_end=turn_end,
        year_start=turns[0].year_start,
        year_end=turns[-1].year_end,
        content=compressed.content,
        domain_frequencies=compressed.domain_frequencies,
    )
    return store.add_summary(record)


def format_summaries_for_context(summaries: list[SummaryRecord]) -> str:
    """中期摘要段落文本。"""
    if not summaries:
        return "（尚无中期摘要）"
    blocks: list[str] = []
    for s in summaries:
        y0 = format_year_label(s.year_start)
        y1 = format_year_label(s.year_end)
        blocks.append(
            f"（第{s.turn_start}–{s.turn_end}回合，{y0}—{y1}）\n{s.content.strip()}"
        )
    return "\n\n".join(blocks)
