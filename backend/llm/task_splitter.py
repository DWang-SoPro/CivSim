"""任务拆分器：将玩家自然语言输入拆成最多 4 个子任务。

规则：
- 输入 < 10 字符：直接当单任务，不调 LLM
- 含明确「；」/「;」或换行分隔的并列政令：确定性拆分，不调 LLM
- 含「和/并/同时/然后」等连接词，或跨越多个行动域才拆
- 同一领域的细化描述不拆
- 最多 4 个子任务
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from backend.llm.client import LLMClient, get_llm_client

# 短输入阈值：低于此长度不调用 LLM
SHORT_INPUT_THRESHOLD = 10
MAX_SUBTASKS = 4

# 行动菜单多选组合使用的确定性分隔符（与前端 ACTION_MENU_SEP 对齐）
# 支持「；」/「;」与换行，便于多行输入框按行组合政令
EXPLICIT_SEP_RE = re.compile(r"(?:[；;]+|\r?\n)+")

TASK_SPLITTER_SYSTEM_PROMPT = """\
你是文明模拟游戏「文明灵」的任务拆分器。玩家（统治集团）用自然语言下达政令。
你的职责是判断这条输入是一个任务还是多个任务，必要时拆成子任务。

拆分规则（严格遵守）：
1. 仅在下列情况拆分：
   - 输入含有明确连接词或分隔符，如「和」「并」「同时」「然后」「接着」「另外」「以及」「；」等，且连接的是不同行动；
   - 或输入明显跨越多个行动域（经济/政治/军事/文化/科技）。
2. 同一领域的细化描述、手段说明、目的补充——不要拆。
   例：「兴修水利以灌溉农田」→ 单任务；「扩建城墙并加高箭楼」→ 单任务（同属军事/防御）。
3. 最多拆成 4 个子任务；若更多，合并相近项，保留最重要的至多 4 个。
4. priority：1 最高，数字越大优先级越低。按玩家表述顺序与紧迫性赋值。
5. original_fragment 尽量截取玩家原文中对应片段。
6. description 可简洁，但必须保留玩家给出的方法步骤/工序/关键参数等可执行细节，
   不可把「分层装料、鼓风、出铁口」这类操作信息压缩掉（下游意图解析依赖这些细节判断知识注入档位）。

你只返回 JSON，不要 Markdown 代码块，不要解释文字。

确切 JSON 结构示例：
{
    "is_multi_task": true,
    "subtasks": [
        {
            "id": "t1",
            "description": "兴修水利工程",
            "original_fragment": "兴修水利",
            "priority": 1
        },
        {
            "id": "t2",
            "description": "扩建军队",
            "original_fragment": "扩建军队",
            "priority": 2
        }
    ],
    "split_reason": "输入用「同时」「并」连接了经济与军事两类行动"
}

单任务示例：
{
    "is_multi_task": false,
    "subtasks": [
        {
            "id": "t1",
            "description": "设立学宫培养人才",
            "original_fragment": "设立学宫",
            "priority": 1
        }
    ],
    "split_reason": "单一文化/教育行动，无需拆分"
}
"""


class SubTask(BaseModel):
    """单个子任务。"""

    id: str = Field(..., description="子任务标识，如 t1")
    description: str = Field(..., description="子任务简洁描述")
    original_fragment: str = Field(..., description="对应的玩家原文片段")
    priority: int = Field(..., ge=1, description="优先级，1 最高")


class TaskSplitResult(BaseModel):
    """任务拆分结果。"""

    is_multi_task: bool = Field(..., description="是否为多任务")
    subtasks: list[SubTask] = Field(..., min_length=1, max_length=MAX_SUBTASKS)
    split_reason: str = Field(..., description="拆分或不拆分的理由")

    @field_validator("subtasks")
    @classmethod
    def cap_subtasks(cls, v: list[SubTask]) -> list[SubTask]:
        """硬性截断至最多 4 个（按 priority 升序保留）。"""
        if len(v) <= MAX_SUBTASKS:
            return v
        return sorted(v, key=lambda s: s.priority)[:MAX_SUBTASKS]


def _single_task_result(player_input: str, reason: str) -> TaskSplitResult:
    """构造不拆分的单任务结果。"""
    text = player_input.strip()
    return TaskSplitResult(
        is_multi_task=False,
        subtasks=[
            SubTask(
                id="t1",
                description=text,
                original_fragment=text,
                priority=1,
            )
        ],
        split_reason=reason,
    )


def _split_by_explicit_separator(text: str) -> TaskSplitResult | None:
    """若输入含「；」/「;」或换行并列分隔，按片段确定性拆分（不调 LLM）。"""
    if not EXPLICIT_SEP_RE.search(text):
        return None
    parts = [p.strip() for p in EXPLICIT_SEP_RE.split(text) if p.strip()]
    if len(parts) <= 1:
        return None
    capped = parts[:MAX_SUBTASKS]
    sep_label = "换行" if "\n" in text or "\r" in text else "「；」"
    return TaskSplitResult(
        is_multi_task=True,
        subtasks=[
            SubTask(
                id=f"t{i}",
                description=part,
                original_fragment=part,
                priority=i,
            )
            for i, part in enumerate(capped, start=1)
        ],
        split_reason=(
            f"输入以{sep_label}分隔为 {len(parts)} 段政令"
            + (f"，已保留前 {MAX_SUBTASKS} 段" if len(parts) > MAX_SUBTASKS else "")
        ),
    )


async def split_tasks(
    player_input: str,
    client: LLMClient | None = None,
) -> TaskSplitResult:
    """将玩家输入拆分为子任务列表。

    输入去除首尾空白后长度 < 10 时直接返回单任务，不调用 LLM。
    含明确「；」或换行分隔时确定性拆分，不调用 LLM。
    """
    text = player_input.strip()
    if not text:
        return _single_task_result("", "空输入，视为单任务")

    # 明确分隔优先于短输入短路，保证菜单多选组合总能拆开
    explicit = _split_by_explicit_separator(text)
    if explicit is not None:
        return explicit

    if len(text) < SHORT_INPUT_THRESHOLD:
        return _single_task_result(text, f"输入不足 {SHORT_INPUT_THRESHOLD} 字符，直接视为单任务")

    llm = client or get_llm_client()
    messages = [
        {"role": "system", "content": TASK_SPLITTER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"请拆分以下玩家政令输入：\n\n{text}",
        },
    ]
    result = await llm.call_json(messages, TaskSplitResult)

    # 保证至少有一条；若模型误标多任务但只有一条，纠正标志
    if len(result.subtasks) == 1:
        return result.model_copy(update={"is_multi_task": False})
    return result.model_copy(update={"is_multi_task": True})
