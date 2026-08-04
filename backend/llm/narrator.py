"""LLM②：叙事生成 — 将数值结算结果转为中文史官叙事（流式）。

配置：关 thinking、开 temperature（默认 0.8）、纯文本非 JSON、流式输出。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from backend.llm.client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

# 叙事默认采样温度（多样性）
NARRATOR_TEMPERATURE = 0.8

# 按重要性预估的 max_tokens 上限（中文约 1 字≈1–2 token）。
# 旧值 normal=280 / major=600 会在 major 长叙事上触发 finish_reason=length，
# 句子半截戛然而止；给足余量覆盖目标字数 + 标点 + 模型偶发超写。
_MAX_TOKENS_BY_IMPORTANCE = {
    "normal": 800,
    "major": 2000,
}

# 撞上 max_tokens 时最多再续写一次，避免前端展示未完成句子。
_CONTINUE_MAX_TOKENS = 800
_CONTINUE_USER_PROMPT = (
    "上文因篇幅限制中断，请从断句处自然续写，完成本段史官叙事。"
    "不要重复已写出的内容，不要加标题或说明，只输出续写正文。"
)

NARRATOR_SYSTEM_PROMPT = """\
你是一位文明史书的史官旁白。根据结构化结算结果，写一段白话叙事，供玩家阅读。

【文体——以现代白话为主干】
- 目标定位：句子结构、语法、连接词都用现代汉语；只在词汇和语气上保留少量古意。
- 像一部面向大众的历史纪录片旁白（如《大明王朝》解说风格），而不是《史记》原文。
- 不是文言文，不是半文半白，不是网络小说，不要网络梗，不要夸张武侠腔。
- 只输出叙事正文，不要标题、不要 Markdown、不要解释、不要引号包裹全文。

【白话原则——一句话】
如果一个受过普通教育的现代人需要停下来想这个词是什么意思，就换一个更好懂的说法。宁可朴实，不要难懂。

【禁止的文言句式（比生僻词更危险）】
不要写成半文半白的判断句、反问句或套话，例如：
「然兵者，凶器也」「岂能轻言必胜」「政令既出，四方响应」「灌溉之利初显」
「祸不单行」「形同虚设」「鞭长莫及」「不忍卒闻」「尚待后世评说」「隐然可见……之绪」。
改成现代说法：用「可是」「然而」「于是」「没过多久」「表面上……背地里……」来连接。

【慎用 / 推荐对照】
慎用（过于文言，现代读者有门槛）：生齿日繁、耆老拊掌、死伤枕藉、荷锸而出、畿甸、持节四出、拊掌相告、瞠目结舌、仓廪、岁稔、萧疏、宁靖、敛迹、如仪、枕藉、田畴、端倪、徭役、萧索……
推荐（有古意但好懂）：粮仓渐满、老人们奔走相告、伤亡惨重、百姓扛着农具、王城周边、四处派出使者、面面相觑、府库、政令、诸侯、王廷、民心不稳、街谈巷议……
厚重感靠叙事节奏、因果铺陈和适度古意词（王廷、政令、诸侯、府库），不靠生僻字。

【改写示范——对齐目标文言浓度】
改写前（过重）：「畿甸之外，使者持节四出，所过城邑皆悬新令。诸侯闻命，莫不肃然。」
改写后（目标）：「王城之外，使者四处奔走，每到一处城邑都张贴新令。各地诸侯接到命令，无不肃然听从。」
再例：改写前「然兵者，凶器也，岂能轻言必胜。」→ 改写后「打仗本就危险，哪能轻易说一定打得赢。」

【纪年——必须遵守】
- 开头时间交代必须使用输入给出的「纪年 year_label」，一字不改地沿用其说法。
- 禁止自造年号、庙号、朝代纪年（如「成王元年」「周某王某年」）。
- 禁止含糊的「这一年」「是年」替代正式纪年；开篇应用 year_label 点明时间。

【忠实数值——反复强调，最高优先级】
- 叙事的方向与程度必须严格匹配 result_tier 与 dimension_changes。
- 部分成功（partial）必须写出「有成有阻」的分寸，绝不能写成大获全胜。
- 失败（failure）就是失败，灾难（disaster）更要写出崩坏与代价，不可粉饰。
- 大成功（great_success）可以写得开阔，但仍须对应给出的变化维度，不得凭空加戏。
- 不得发明结构化输入中没有的重大情节（如额外战争、宫廷政变），除非 events 已列出。
- 绝不直接报出任何具体数字、百分比或分数（禁止「人口增百分之二」「稳定下降八」之类）。

【长度——严格遵守】
- importance=normal：约 80–150 字，必须只有一段，写完即止，不要写到两百字以上。
- importance=major：约 250–450 字，可分 2–3 段，有起承转合；写完收束，不要明显超过 450 字。

【数值→意象（方向锚点；好懂优先，灵活轮换用词）】
粮食/人口↑ → 粮仓渐满、收成好转、人口略增、炊烟更密……
粮食/人口↓ → 百姓面黄肌瘦、饥荒迹象出现、村落冷清……
稳定↑ → 街上平静、盗贼减少、四方安宁……
稳定↓ → 民心不稳、街谈巷议、盗贼渐多……
统治力↑ → 政令畅通、威望上升、令行禁止……
统治力↓ → 号令难行、诸侯观望、表面顺从暗里拖延……
技术↑ → 工匠有了收获、器物做得更精……
阶级矛盾↑ → 怨声渐起、贫富冲突加剧……
按变化方向与幅度选用相近意象；变化小则轻写，变化大则加重。

【意象去重】
- 同一段叙事内，不要反复使用同一个意象词。
- 避免使用 recent_imagery 列表中已列出的词（跨回合去重预留）。
- 同一方向应轮换多种表达，不要每次都写「粮仓」「阳奉阴违」「流言四起」。

【result_tier 分寸】
- great_success：成效出人意料地好，但仍只写已给维度
- success：顺利达成目标
- partial：有成有阻，得失并存
- failure：受挫、未达预期
- disaster：严重后果、创伤与震荡

【不可执行 / 无事发生】
当 is_unexecutable=true：命令虽已下达，但实质几乎无事发生。
要写出历史况味——朝堂茫然、群臣面面相觑、诏令石沉大海的荒诞感；
可参考 unexecutable_reason（若有）。不要干巴巴说「失败」或「技术不够」。用白话写，不要堆砌生僻典故。

【历史因果】
当 history_context 非空时，在叙事中自然体现「往事如何导致今日」的因果链，
不生硬回顾、不做编年罗列。若当前事件与【相关史事】或【近期历程】有关联，
要让读者感受到「因为当年做了某事，所以今天才会如此」，而不是开中药铺式点名。
若 history_context 为空或未提供，则忽略本条。

【路径积累——如何运用】
history_context 中若含【路径积累】段落，说明该文明在各领域的长期底蕴深浅。
当某领域积累深厚、且当前行动恰属该领域时，叙事应自然写出底蕴带来的顺畅感，
例如「赖数十年兴学之功，新法一点即透」「军伍素有训练，征发并不慌乱」；
若积累尚浅，则可略写根基不足、推行吃力。不要报出积累数值本身。

【events】
若提供了 events，把它们自然织进叙事，不要做成清单。若事件原文偏文言，改写成白话后再写入。
"""


class ResultTier(str, Enum):
    """行动结果档位（与引擎 ActionResultTier 对齐）。"""

    GREAT_SUCCESS = "great_success"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    DISASTER = "disaster"


class Importance(str, Enum):
    """叙事重要性，驱动篇幅。"""

    NORMAL = "normal"
    MAJOR = "major"


def format_year_label(year: float) -> str:
    """将游戏年份数值格式化为统一纪年字符串，供提示词直接使用。

    规则：负数为公元前，正数为公元，零为公元元年；一律用阿拉伯数字，禁止模型自造。
    例：-1046 →「公元前1046年」；100 →「公元100年」。
    """
    y = int(round(year))
    if y < 0:
        return f"公元前{abs(y)}年"
    if y == 0:
        return "公元元年"
    return f"公元{y}年"


class NarrationInput(BaseModel):
    """喂给史官的结构化结算摘要。"""

    civ_name: str = Field(..., description="文明名称")
    year: float = Field(..., description="当前年份（游戏内数值，如 -1046）")
    action_description: str = Field(..., description="做了什么（来自意图解析）")
    result_tier: ResultTier = Field(..., description="结果档位")
    dimension_changes: dict[str, str] = Field(
        default_factory=dict,
        description="各维度变化方向与程度，如 population: '+2%'",
    )
    events: list[str] = Field(default_factory=list, description="触发的事件简述")
    is_unexecutable: bool = Field(
        default=False, description="是否为不可执行的超前行动"
    )
    importance: Importance = Field(
        default=Importance.NORMAL, description="重要性：normal|major"
    )
    history_context: Optional[str] = Field(
        default=None,
        description="历史上下文（近期+中期摘要+相关 landmark+积累值）",
    )
    unexecutable_reason: Optional[str] = Field(
        default=None,
        description="不可执行时的补充说明（如意图解析的 time_estimate_reasoning）",
    )
    recent_imagery: list[str] = Field(
        default_factory=list,
        description="近期用过的意象词；当前可传空列表，供跨回合去重",
    )


def build_narrator_user_prompt(payload: NarrationInput) -> str:
    """将结构化输入格式化为史官可读的中文说明。"""
    year_label = format_year_label(payload.year)
    changes_lines = (
        "\n".join(f"  - {k}: {v}" for k, v in payload.dimension_changes.items())
        or "  （无显著维度变化）"
    )
    events_block = (
        "、".join(payload.events) if payload.events else "（无特殊事件）"
    )
    history = (
        payload.history_context.strip()
        if payload.history_context and payload.history_context.strip()
        else "（无）"
    )
    reason = (
        payload.unexecutable_reason.strip()
        if payload.unexecutable_reason and payload.unexecutable_reason.strip()
        else "（无）"
    )
    recent = (
        "、".join(payload.recent_imagery)
        if payload.recent_imagery
        else "（无，可自由选用意象）"
    )

    return f"""\
请根据以下结算结果撰写史官叙事。只输出叙事正文。
开篇必须用给定的纪年 year_label 交代时间，禁止自造年号。

文明：{payload.civ_name}
年份数值 year：{payload.year}
纪年 year_label：{year_label}
行动：{payload.action_description}
结果档位 result_tier：{payload.result_tier.value}
重要性 importance：{payload.importance.value}
不可执行 is_unexecutable：{"是" if payload.is_unexecutable else "否"}
不可执行补充理由：{reason}

维度变化 dimension_changes：
{changes_lines}

事件 events：{events_block}

近期已用意象 recent_imagery（请避免再用这些词）：{recent}

历史背景 history_context：
{history}
"""


async def narrate_stream(
    payload: NarrationInput,
    *,
    client: LLMClient | None = None,
    temperature: float = NARRATOR_TEMPERATURE,
) -> AsyncIterator[str]:
    """流式生成史官叙事文本块。

    若首次生成因 max_tokens 截断（finish_reason=length），自动追加一次续写，
    把续写增量继续以流式块 yield 出去。
    """
    llm = client or get_llm_client()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": NARRATOR_SYSTEM_PROMPT},
        {"role": "user", "content": build_narrator_user_prompt(payload)},
    ]
    max_tokens = _MAX_TOKENS_BY_IMPORTANCE.get(payload.importance.value, 800)
    finish_reason_out: list[str | None] = []
    parts: list[str] = []
    async for chunk in llm.call_text_stream(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        finish_reason_out=finish_reason_out,
    ):
        parts.append(chunk)
        yield chunk

    finish_reason = finish_reason_out[0] if finish_reason_out else None
    if finish_reason != "length":
        return

    partial = "".join(parts)
    logger.warning(
        "叙事被截断，尝试续写 (importance=%s, chars=%s, finish_reason=%s)",
        payload.importance.value,
        len(partial),
        finish_reason,
    )
    continue_messages = [
        *messages,
        {"role": "assistant", "content": partial},
        {"role": "user", "content": _CONTINUE_USER_PROMPT},
    ]
    continue_finish: list[str | None] = []
    async for chunk in llm.call_text_stream(
        continue_messages,
        temperature=temperature,
        max_tokens=_CONTINUE_MAX_TOKENS,
        finish_reason_out=continue_finish,
    ):
        yield chunk

    continue_reason = continue_finish[0] if continue_finish else None
    if continue_reason == "length":
        logger.warning(
            "叙事续写仍被截断 (importance=%s, finish_reason=length)；"
            "前端可能仍会看到未完成句子",
            payload.importance.value,
        )


async def narrate(
    payload: NarrationInput,
    *,
    client: LLMClient | None = None,
    temperature: float = NARRATOR_TEMPERATURE,
) -> str:
    """收集完整叙事文本（测试与非流式场景）。"""
    parts: list[str] = []
    async for piece in narrate_stream(
        payload, client=client, temperature=temperature
    ):
        parts.append(piece)
    return "".join(parts)


async def generate_narrative(
    state: object,
    action_result: dict,
    history_context: str,
) -> AsyncIterator[str]:
    """兼容旧占位签名：从粗字典拼装 NarrationInput 后流式生成。

    正式管线请直接使用 narrate_stream(NarrationInput(...))。
    """
    payload = NarrationInput(
        civ_name=str(getattr(state, "civ_name", "未知文明")),
        year=float(getattr(state, "year", 0.0)),
        action_description=str(
            action_result.get("action_description")
            or action_result.get("description")
            or "（未命名行动）"
        ),
        result_tier=action_result.get("result_tier", "success"),
        dimension_changes=dict(action_result.get("dimension_changes") or {}),
        events=list(action_result.get("events") or []),
        is_unexecutable=bool(action_result.get("is_unexecutable", False)),
        importance=action_result.get("importance", "normal"),
        history_context=history_context or None,
        unexecutable_reason=action_result.get("unexecutable_reason"),
        recent_imagery=list(action_result.get("recent_imagery") or []),
    )
    async for chunk in narrate_stream(payload):
        yield chunk
