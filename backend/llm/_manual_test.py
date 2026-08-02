"""LLM 管线手动测试脚本（非 pytest）。

用法：
  1. 在项目根目录创建 .env，写入：DEEPSEEK_API_KEY=sk-...
  2. 运行：
       uv run python -m backend.llm._manual_test              # 意图管线
       uv run python -m backend.llm._manual_test --narrator  # 叙事生成
       uv run python -m backend.llm._manual_test --fullturn  # 端到端完整回合
       uv run python -m backend.llm._manual_test --all       # 意图+叙事
       uv run python -m backend.llm._manual_test --narrator 灾难  # 过滤叙事用例

默认使用西周模板作为文明状态；--fullturn 固定随机种子 42。
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from typing import Any

from backend.config import settings
from backend.engine.action_resolver import full_turn_to_debug_dict, resolve_full_turn
from backend.llm.client import LLMClient, LLMError
from backend.llm.intent_parser import parse_intent
from backend.llm.narrator import Importance, NarrationInput, ResultTier, narrate_stream
from backend.llm.task_splitter import split_tasks
from backend.templates.civilizations import load_civ_state

FULLTURN_RNG_SEED = 42

# 覆盖：合理 / 超前 / 知识注入 / 荒谬 / 模糊 / 多任务
TEST_CASES: list[tuple[str, str]] = [
    ("合理-水利", "兴修水利"),
    ("合理-学宫", "设立学宫"),
    ("合理-城墙", "扩建城墙"),
    ("超前-科举", "推行科举"),
    ("超前-央行", "建立中央银行"),
    (
        "知识注入-高炉",
        "我教工匠用高炉鼓风炼铁，先把铁矿石和木炭分层装入炉中，"
        "再从炉底鼓风升温，铁水从出铁口放出后铸成农具与兵器",
    ),
    ("荒谬-核武", "发明核武器"),
    ("荒谬-飞船", "建造宇宙飞船"),
    ("模糊-发展", "发展"),
    ("模糊-变强", "变强"),
    (
        "多任务",
        "兴修水利，同时扩建军队，并派使者与邻国结盟",
    ),
]


# 端到端完整回合用例（西周初始状态 + 固定种子）
FULLTURN_CASES: list[tuple[str, str]] = [
    ("完整回合-单一中等", "兴修水利"),
    (
        "完整回合-多任务",
        "兴修水利，同时扩建军队，并派使者与邻国结盟",
    ),
    (
        "完整回合-三大规模",
        "迁都，并推行均田变法，同时发兵灭掉邻国",
    ),
    ("完整回合-超前科举", "推行科举"),
    ("完整回合-模糊", "发展"),
    (
        "完整回合-知识注入高炉",
        "我教工匠用高炉鼓风炼铁，先把铁矿石和木炭分层装入炉中，"
        "再从炉底鼓风升温，铁水从出铁口放出后铸成农具与兵器",
    ),
]


# 叙事测试：直接构造结构化输入，不依赖真实数学引擎
NARRATOR_CASES: list[tuple[str, NarrationInput]] = [
    (
        "叙事-常规部分成功",
        NarrationInput(
            civ_name="西周",
            year=-1046.0,
            action_description="兴修水利，疏通沟渠以利农耕",
            result_tier=ResultTier.PARTIAL,
            dimension_changes={
                "food": "+小幅",
                "population": "+1%",
                "stability": "-3",
            },
            events=["部分郡国征发劳役过重，民有怨言"],
            is_unexecutable=False,
            importance=Importance.NORMAL,
            history_context=None,
            recent_imagery=[],
        ),
    ),
    (
        "叙事-重大成功",
        NarrationInput(
            civ_name="西周",
            year=-1040.0,
            action_description="改革分封与朝贡秩序，厘定诸侯职贡",
            result_tier=ResultTier.GREAT_SUCCESS,
            dimension_changes={
                "authority": "+12",
                "stability": "+8",
                "bureaucratization": "+小幅",
                "elite_cohesion": "+中幅",
                "class_tension": "-小幅",
            },
            events=["诸侯依礼前来朝见", "王城一带盗贼明显减少"],
            is_unexecutable=False,
            importance=Importance.MAJOR,
            history_context=None,
            recent_imagery=[],
        ),
    ),
    (
        "叙事-灾难性失败",
        NarrationInput(
            civ_name="西周",
            year=-1035.0,
            action_description="冒进远征西北戎狄，以求拓土扬威",
            result_tier=ResultTier.DISASTER,
            dimension_changes={
                "population": "-8%",
                "stability": "-15",
                "authority": "-10",
                "military_accumulation": "-中幅",
            },
            events=["先头部队在峡谷全军覆没", "三郡贵族抗命，拒绝补充兵员"],
            is_unexecutable=False,
            importance=Importance.MAJOR,
            history_context=None,
            recent_imagery=[],
        ),
    ),
    (
        "叙事-不可执行",
        NarrationInput(
            civ_name="西周",
            year=-1046.0,
            action_description="发明核武器",
            result_tier=ResultTier.FAILURE,
            dimension_changes={},
            events=[],
            is_unexecutable=True,
            importance=Importance.NORMAL,
            history_context=None,
            unexecutable_reason="朝野茫然无措，无人知此为何物，诏令空悬而实质无事发生",
            recent_imagery=[],
        ),
    ),
    (
        "叙事-多维度混合",
        NarrationInput(
            civ_name="西周",
            year=-1042.0,
            action_description="整顿田制与赋役，强化王畿征敛",
            result_tier=ResultTier.PARTIAL,
            dimension_changes={
                "authority": "+6",
                "class_tension": "+中幅",
                "stability": "-4",
                "food": "+小幅",
            },
            events=["王城一带粮仓略有充实", "部分卿大夫暗中阻挠"],
            is_unexecutable=False,
            importance=Importance.NORMAL,
            history_context=None,
            recent_imagery=[],
        ),
    ),
]


def _dump(obj: Any) -> str:
    """Pydantic / dict → 缩进 JSON。"""
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
    else:
        data = obj
    return json.dumps(data, ensure_ascii=False, indent=2)


def _filter_by_keywords(
    items: list[tuple[str, Any]], keywords: list[str]
) -> list[tuple[str, Any]]:
    """按标签/文本子串过滤；无关键词则原样返回。"""
    if not keywords:
        return items
    matched = [
        (label, payload)
        for label, payload in items
        if any(k in label or (isinstance(payload, str) and k in payload) for k in keywords)
    ]
    return matched


async def run_one(client: LLMClient, label: str, text: str, state: Any) -> None:
    """跑一条意图管线用例并打印。"""
    bar = "=" * 72
    print(f"\n{bar}")
    print(f"[{label}]")
    print(f"输入: {text}")
    print("-" * 72)

    try:
        split = await split_tasks(text, client=client)
        print("【TaskSplitter】")
        print(_dump(split))

        for sub in split.subtasks:
            if not split.is_multi_task:
                intent_text = text
            else:
                intent_text = sub.description
                if sub.original_fragment and sub.original_fragment not in sub.description:
                    intent_text = f"{sub.description}\n（原文片段：{sub.original_fragment}）"
            print("-" * 72)
            print(f"【IntentParser】子任务 {sub.id}: {intent_text}")
            intent = await parse_intent(intent_text, state, client=client)
            print(_dump(intent))
    except Exception as exc:  # noqa: BLE001 — 手动脚本要看完整错误
        print(f"!! 失败: {type(exc).__name__}: {exc}")
        traceback.print_exc()


async def run_fullturn_one(
    client: LLMClient, label: str, text: str, state: Any
) -> None:
    """跑一条完整回合：打印意图→国力→掷骰→数值→叙事全链路。"""
    bar = "=" * 72
    print(f"\n{bar}")
    print(f"[{label}]")
    print(f"输入: {text}")
    print(f"rng_seed: {FULLTURN_RNG_SEED}")
    print("-" * 72)

    try:
        t0 = time.perf_counter()
        result = await resolve_full_turn(
            state,
            text,
            client=client,
            rng_seed=FULLTURN_RNG_SEED,
            generate_narrative=True,
        )
        elapsed = time.perf_counter() - t0
        debug = full_turn_to_debug_dict(result)

        print("【TaskSplitter】")
        print(_dump(debug["split"]))

        print("-" * 72)
        print("【各子任务意图 Intent JSON】")
        for sub in debug["subtasks"]:
            print(f"--- 子任务 {sub['subtask_id']} ---")
            print(_dump(sub["intent"]))

        if debug["vague_prompts"]:
            print("-" * 72)
            print("【模糊反问】")
            for p in debug["vague_prompts"]:
                print(p)

        if debug["settlement_skipped"]:
            print("-" * 72)
            print("【结算】已跳过（整回合均为模糊任务）")
            print(f"返回: {debug['narrative']}")
            print(f"总耗时={elapsed * 1000:.0f}ms")
            return

        print("-" * 72)
        print("【Capacity / Transmission / Dilution】")
        print(_dump(debug["capacity"]))

        print("-" * 72)
        print("【成功率 / 掷骰 / 档位 / 数值变动】")
        for sub in debug["subtasks"]:
            if sub["skipped_vague"]:
                continue
            print(
                f"子任务 {sub['subtask_id']}: "
                f"P={sub['p_success']:.4f} | tier={sub['result_tier']} | "
                f"mult={sub['effect_mult']} | demand={sub['demand']:.3f} | "
                f"dilution={sub['dilution_factor']:.4f} | "
                f"unexec={sub['is_unexecutable']}"
            )
            print(f"  base_deltas: {_dump(sub['base_deltas'])}")
            print(f"  diluted_deltas: {_dump(sub['diluted_deltas'])}")
            if sub["events"]:
                print(f"  events: {sub['events']}")

        print("-" * 72)
        print("【汇总】")
        print(
            f"overall_tier={debug['overall_tier']} | "
            f"importance={debug['importance']} | "
            f"turn_years={debug['turn_years']}"
        )
        print("aggregated_deltas:")
        print(_dump(debug["aggregated_deltas"]))
        print("dimension_changes:")
        print(_dump(debug["dimension_changes"]))
        print("state_after:")
        print(_dump(debug["state_after"]))

        print("-" * 72)
        print("【叙事输入】")
        print(_dump(debug["narration_input"]))
        print("-" * 72)
        print("【史官叙事】")
        print(debug["narrative"] or "（无）")
        print("-" * 72)
        print(f"总耗时={elapsed * 1000:.0f}ms")
    except Exception as exc:  # noqa: BLE001
        print(f"!! 失败: {type(exc).__name__}: {exc}")
        traceback.print_exc()


async def run_narrator_one(
    client: LLMClient, label: str, payload: NarrationInput
) -> None:
    """跑一条叙事用例：收集流式输出后并排打印，并标注首字延迟。"""
    bar = "=" * 72
    print(f"\n{bar}")
    print(f"[{label}]")
    print("【结构化输入】")
    print(_dump(payload))
    print("-" * 72)
    print("【史官叙事】")

    try:
        t0 = time.perf_counter()
        first_token_ms: float | None = None
        parts: list[str] = []
        async for chunk in narrate_stream(payload, client=client):
            if first_token_ms is None:
                first_token_ms = (time.perf_counter() - t0) * 1000
            parts.append(chunk)
        text = "".join(parts)
        total_ms = (time.perf_counter() - t0) * 1000
        print(text)
        print("-" * 72)
        if first_token_ms is not None:
            print(
                f"字数≈{len(text)} | 首字延迟={first_token_ms:.0f}ms | "
                f"总耗时={total_ms:.0f}ms"
            )
        else:
            print(f"字数=0 | 总耗时={total_ms:.0f}ms（无输出）")
    except Exception as exc:  # noqa: BLE001
        print(f"!! 失败: {type(exc).__name__}: {exc}")
        traceback.print_exc()


async def main() -> int:
    """入口。"""
    if not settings.deepseek_api_key:
        print(
            "错误：未检测到 DEEPSEEK_API_KEY。\n"
            "请在项目根目录创建 .env，例如：\n"
            "  DEEPSEEK_API_KEY=sk-xxxxxxxx\n"
            "可选：\n"
            "  LLM_MODEL=deepseek-v4-flash\n"
            "  LLM_BASE_URL=https://api.deepseek.com\n",
            file=sys.stderr,
        )
        return 1

    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    filters = [a for a in sys.argv[1:] if not a.startswith("-")]

    run_fullturn = "--fullturn" in flags
    run_intent = "--all" in flags or "--intent" in flags
    run_narrator = "--narrator" in flags or "--all" in flags
    # 默认无标志：只跑意图（兼容旧用法）
    if not flags:
        run_intent = True
        run_narrator = False
        run_fullturn = False
    if run_fullturn and flags == {"--fullturn"}:
        run_intent = False
        run_narrator = False

    print(f"模型: {settings.llm_model}")
    print(f"Base URL: {settings.llm_base_url}")
    print(f"API Key: {settings.deepseek_api_key[:8]}…")

    try:
        client = LLMClient()
    except LLMError as exc:
        print(f"初始化客户端失败: {exc}", file=sys.stderr)
        return 1

    if run_fullturn:
        state = load_civ_state("zhou")
        print(
            f"完整回合测试文明: {state.civ_name}（{state.template_id}），"
            f"年={state.year}，seed={FULLTURN_RNG_SEED}"
        )
        cases = _filter_by_keywords(FULLTURN_CASES, filters)  # type: ignore[arg-type]
        if filters and not cases:
            print(f"没有匹配过滤器 {filters!r} 的完整回合用例", file=sys.stderr)
            return 1
        for label, text in cases:
            # 每条从同一初始状态独立开跑，互不污染
            await run_fullturn_one(client, label, text, load_civ_state("zhou"))
        print("\n" + "=" * 72)
        print(f"完整回合完成：共 {len(cases)} 条用例。")

    if run_intent:
        state = load_civ_state("zhou")
        print(f"测试文明: {state.civ_name}（{state.template_id}），年={state.year}")
        cases = _filter_by_keywords(TEST_CASES, filters)  # type: ignore[arg-type]
        if filters and not cases and not run_narrator and not run_fullturn:
            print(f"没有匹配过滤器 {filters!r} 的意图用例", file=sys.stderr)
            return 1
        if not filters or cases:
            for label, text in cases:
                await run_one(client, label, text, state)
            print("\n" + "=" * 72)
            print(f"意图管线完成：共 {len(cases)} 条用例。")

    if run_narrator:
        n_cases = _filter_by_keywords(NARRATOR_CASES, filters)  # type: ignore[arg-type]
        if filters and not n_cases:
            # 过滤器只命中意图时，叙事仍跑全量
            n_cases = list(NARRATOR_CASES)
        for label, payload in n_cases:
            await run_narrator_one(client, label, payload)
        print("\n" + "=" * 72)
        print(f"叙事生成完成：共 {len(n_cases)} 条用例。")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
