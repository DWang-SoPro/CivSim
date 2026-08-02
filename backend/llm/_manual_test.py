"""LLM 管线手动测试脚本（非 pytest）。

用法：
  1. 在项目根目录创建 .env，写入：DEEPSEEK_API_KEY=sk-...
  2. 运行：
       uv run python -m backend.llm._manual_test              # 意图管线
       uv run python -m backend.llm._manual_test --narrator  # 叙事生成
       uv run python -m backend.llm._manual_test --fullturn  # 端到端完整回合
       uv run python -m backend.llm._manual_test --memory    # 三层记忆系统
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
from backend.llm.narrator import Importance, NarrationInput, ResultTier, narrate, narrate_stream
from backend.llm.task_splitter import split_tasks
from backend.memory.landmark import create_landmarks_from_turn
from backend.memory.recent import build_recent_context, load_recent_turns
from backend.memory.retriever import retrieve_history_context
from backend.memory.store import MemoryStore, TurnRecord
from backend.memory.summary import maybe_create_summary, should_trigger_summary
from backend.models.schemas import Accumulations, LandSystem
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


def _make_scripted_turn(
    store: MemoryStore,
    turn: int,
    *,
    year_base: float,
    player_input: str,
    action_description: str,
    result_tier: str,
    domain_tags: list[str],
    dimension_changes: dict[str, str],
    narrative: str,
    summary: str | None = None,
) -> TurnRecord:
    """手工构造一轮历史（不调结算引擎）。"""
    return store.add_turn(
        TurnRecord(
            game_id=store.game_id,
            turn=turn,
            year_start=year_base + (turn - 1) * 2,
            year_end=year_base + turn * 2,
            player_input=player_input,
            action_description=action_description,
            result_tier=result_tier,
            dimension_changes=dimension_changes,
            narrative=narrative,
            summary=summary or f"{action_description} → {result_tier}",
            domain_tags=domain_tags,
        )
    )


async def run_memory_demo(client: LLMClient) -> None:
    """三层记忆手动验收：脚本历史 → 摘要压缩 → landmark → 检索 → 带因果叙事。"""
    bar = "=" * 72
    print(f"\n{bar}")
    print("[记忆系统 --memory]")
    print("文明：西周模板；构造 10 回合脚本历史，真实调用摘要 LLM + 叙事 LLM")
    print(bar)

    state0 = load_civ_state("zhou")
    # 抬高行政积累，便于叙事体现「底蕴」
    state0 = state0.model_copy(
        update={
            "accumulations": Accumulations(
                academic=0.4,
                military=0.5,
                commercial=0.3,
                administrative=1.35,
                cultural=0.6,
            )
        }
    )
    store = MemoryStore(game_id="manual-memory-demo")
    year_base = float(state0.year)

    scripted: list[dict[str, Any]] = [
        {
            "turn": 1,
            "input": "兴修水利",
            "desc": "疏通沟渠、兴修水利以利农耕",
            "tier": "partial",
            "tags": ["economic"],
            "changes": {"food": "+小幅", "stability": "-2"},
            "narrative": (
                "公元前1046年，王廷下令疏通王畿沟渠。百姓扛着农具出工，"
                "部分渠段当年见效，也有郡国征发过重、民有怨言。"
            ),
        },
        {
            "turn": 2,
            "input": "扩建军队",
            "desc": "扩充甲士、整备车马",
            "tier": "success",
            "tags": ["military"],
            "changes": {"authority": "+4", "stability": "-1"},
            "narrative": (
                "公元前1044年，王室扩军整训。军伍人数增加，边地诸侯对王命更加忌惮，"
                "民间略感征发之苦。"
            ),
        },
        {
            "turn": 3,
            "input": "设立学宫",
            "desc": "于王城设立学宫传授典籍",
            "tier": "success",
            "tags": ["cultural"],
            "changes": {"tech_knowledge": "+小幅", "stability": "+2"},
            "narrative": (
                "公元前1042年，学宫落成。贵族子弟入学诵读，典籍传抄渐广，"
                "朝中议论时也多了些引经据典的口气。"
            ),
        },
        {
            "turn": 4,
            "input": "派使者与邻国结盟",
            "desc": "遣使与东方诸侯缔结盟约",
            "tier": "success",
            "tags": ["political"],
            "changes": {"authority": "+3", "stability": "+1"},
            "narrative": (
                "公元前1040年，使者持礼币东行，与两家邻国定盟。边境摩擦暂息，"
                "王廷威望小有回升。"
            ),
        },
        {
            "turn": 5,
            "input": "迁都洛邑，并更改田制",
            "desc": "迁都洛邑并推行新田制",
            "tier": "great_success",
            "tags": ["political", "institutional"],
            "changes": {"authority": "+12", "stability": "-5", "bureaucratization": "+小幅"},
            "narrative": (
                "公元前1038年，王室迁都洛邑，并更张田制。旧贵族有人观望，有人抵制，"
                "但新都落成、田籍重定，政令从此更易到达东方。此事震动朝野，成为一代转折。"
            ),
        },
        {
            "turn": 6,
            "input": "练兵于西陲",
            "desc": "于西陲校阅车骑",
            "tier": "partial",
            "tags": ["military"],
            "changes": {"authority": "+2", "stability": "-1"},
            "narrative": (
                "公元前1036年，西陲校场点兵。甲士阵形可观，粮秣转运却跟不上，"
                "只能算小有成效。"
            ),
        },
        {
            "turn": 7,
            "input": "开市通商",
            "desc": "开放关市、鼓励商旅往来",
            "tier": "success",
            "tags": ["economic"],
            "changes": {"food": "+小幅", "stability": "+1"},
            "narrative": (
                "公元前1034年，关市放宽。商旅渐多，王城市井热闹了些，府库也略有进项。"
            ),
        },
        {
            "turn": 8,
            "input": "整饬吏治，颁布考绩之法",
            "desc": "整饬吏治并颁布地方官考绩之法",
            "tier": "success",
            "tags": ["political"],
            "changes": {"authority": "+6", "stability": "+3", "bureaucratization": "+小幅"},
            "narrative": "",  # 本回合将用检索后的叙事覆盖
        },
        {
            "turn": 9,
            "input": "修补城墙",
            "desc": "加固王城与要隘城墙",
            "tier": "success",
            "tags": ["military"],
            "changes": {"authority": "+2", "stability": "+1"},
            "narrative": "公元前1030年，城墙加高加厚，守军信心稍增。",
        },
        {
            "turn": 10,
            "input": "推广铁农具",
            "desc": "在王畿推广铁制农具",
            "tier": "partial",
            "tags": ["technology", "economic"],
            "changes": {"tech_agriculture": "+小幅", "tech_engineering": "+小幅"},
            "narrative": (
                "公元前1028年，铁农具开始下发到部分乡邑。工匠跟得上的地方收成好转，"
                "偏远处仍多用旧器。"
            ),
        },
    ]

    summary_at_5 = None
    summary_at_10 = None
    landmarks_turn5: list[Any] = []

    # ---- 写入 1–7，并在第 5 回合触发 landmark + 摘要 ----
    for item in scripted:
        t = int(item["turn"])
        if t == 8:
            break  # 第 8 回合单独做检索+叙事
        _make_scripted_turn(
            store,
            t,
            year_base=year_base,
            player_input=item["input"],
            action_description=item["desc"],
            result_tier=item["tier"],
            domain_tags=item["tags"],
            dimension_changes=item["changes"],
            narrative=item["narrative"],
        )

        if t == 5:
            before = state0.model_copy(deep=True)
            after = before.model_copy(deep=True)
            after.turn = 5
            after.year = year_base + 10
            # 西周模板本身已是 state_grant，须改成不同制度才能触发 landmark
            after.land_system = LandSystem.YEOMAN_SMALLHOLD
            after.authority = min(100.0, before.authority + 12)
            after.stability = max(0.0, before.stability - 5)
            landmarks_turn5 = create_landmarks_from_turn(
                store,
                turn=5,
                year=float(after.year),
                state_before=before,
                state_after=after,
                domain_tags=["political"],
                action_description=item["desc"],
                result_tier=item["tier"],
                narrative=item["narrative"],
            )
            print(f"\n{'-' * 72}")
            print("【Landmark 触发 — 第5回合迁都+改田制】")
            for lm in landmarks_turn5:
                print(
                    f"- title={lm.title}\n"
                    f"  tags={lm.tags}\n"
                    f"  importance={lm.importance_score}\n"
                    f"  summary={lm.summary}\n"
                    f"  embedding={lm.embedding!r} (预留未实现)"
                )

        if should_trigger_summary(t):
            print(f"\n{'-' * 72}")
            print(f"【中期摘要触发】current_turn={t}（% 5 == 0）")
            rec = await maybe_create_summary(
                store,
                current_turn=t,
                civ_name=state0.civ_name,
                client=client,
            )
            if t == 5:
                summary_at_5 = rec
            elif t == 10:
                summary_at_10 = rec
            if rec is None:
                print("!! 摘要未生成")
            else:
                print(
                    f"turn_start={rec.turn_start} turn_end={rec.turn_end}\n"
                    f"domain_frequencies={rec.domain_frequencies}\n"
                    f"--- content ---\n{rec.content}"
                )

    # ---- 检查近期记忆（写入 1–7 后最近 5 = 3–7）----
    print(f"\n{'-' * 72}")
    print("【第一层 近期记忆】写入 1–7 后最近 5 回合")
    recent = load_recent_turns(store, limit=5)
    print(f"回合号: {[t.turn for t in recent]}")
    print(build_recent_context(store, limit=5))
    assert [t.turn for t in recent] == [3, 4, 5, 6, 7], recent

    # ---- 第 8 回合：政治行动 + 检索 + 叙事 ----
    print(f"\n{'-' * 72}")
    print("【检索】第8回合政治域行动 → 应命中迁都等 political landmark")
    history_ctx = retrieve_history_context(
        store,
        domain_tags=["political"],
        state=state0,
        recent_limit=5,
        summary_limit=3,
        landmark_limit=5,
    )
    print(history_ctx)
    assert "迁都" in history_ctx or "制度" in history_ctx, "应检索到迁都/制度 landmark"
    assert "【路径积累】" in history_ctx
    assert "行政经验" in history_ctx

    turn8 = scripted[7]
    narration_input = NarrationInput(
        civ_name=state0.civ_name,
        year=year_base + 16,
        action_description=turn8["desc"],
        result_tier=ResultTier.SUCCESS,
        dimension_changes=turn8["changes"],
        events=["部分旧族对新考绩法阳奉阴违，旋即被王廷点名申饬"],
        is_unexecutable=False,
        importance=Importance.MAJOR,
        history_context=history_ctx,
        recent_imagery=[],
    )
    print(f"\n{'-' * 72}")
    print("【带 history_context 的史官叙事】第8回合整饬吏治")
    t0 = time.perf_counter()
    narrative8 = await narrate(narration_input, client=client)
    print(narrative8)
    print(f"耗时={(time.perf_counter() - t0) * 1000:.0f}ms | 字数≈{len(narrative8)}")

    # 写入第 8 回合（含生成叙事）
    _make_scripted_turn(
        store,
        8,
        year_base=year_base,
        player_input=turn8["input"],
        action_description=turn8["desc"],
        result_tier=turn8["tier"],
        domain_tags=turn8["tags"],
        dimension_changes=turn8["changes"],
        narrative=narrative8,
    )

    # ---- 补写 9–10，第 10 回合再压一次摘要 ----
    for item in scripted:
        t = int(item["turn"])
        if t < 9:
            continue
        _make_scripted_turn(
            store,
            t,
            year_base=year_base,
            player_input=item["input"],
            action_description=item["desc"],
            result_tier=item["tier"],
            domain_tags=item["tags"],
            dimension_changes=item["changes"],
            narrative=item["narrative"],
        )
        if should_trigger_summary(t):
            print(f"\n{'-' * 72}")
            print(f"【中期摘要触发】current_turn={t}")
            rec = await maybe_create_summary(
                store,
                current_turn=t,
                civ_name=state0.civ_name,
                client=client,
            )
            summary_at_10 = rec
            if rec is None:
                print("!! 摘要未生成")
            else:
                print(
                    f"turn_start={rec.turn_start} turn_end={rec.turn_end}\n"
                    f"domain_frequencies={rec.domain_frequencies}\n"
                    f"--- content ---\n{rec.content}"
                )

    print(f"\n{bar}")
    print("【记忆系统验收摘要】")
    print(f"- 近期记忆最近5回合: {[t.turn for t in load_recent_turns(store)]}")
    print(f"- 第5回合摘要: {'OK' if summary_at_5 else 'MISSING'}")
    print(f"- 第10回合摘要: {'OK' if summary_at_10 else 'MISSING'}")
    print(f"- 第5回合 landmarks: {len(landmarks_turn5)} 条")
    print(f"- 全库 landmarks: {len(store.get_all_landmarks())} 条")
    print(f"- 全库 summaries: {len(store.get_recent_summaries(limit=10))} 条")
    print(f"- 第8回合叙事是否含历史回响: 请人工阅读上方叙事（应提及迁都/洛邑/田制等）")
    print(bar)


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
    run_memory = "--memory" in flags
    run_intent = "--all" in flags or "--intent" in flags
    run_narrator = "--narrator" in flags or "--all" in flags
    # 默认无标志：只跑意图（兼容旧用法）
    if not flags:
        run_intent = True
        run_narrator = False
        run_fullturn = False
        run_memory = False
    if run_fullturn and flags == {"--fullturn"}:
        run_intent = False
        run_narrator = False
    if run_memory and flags == {"--memory"}:
        run_intent = False
        run_narrator = False
        run_fullturn = False

    print(f"模型: {settings.llm_model}")
    print(f"Base URL: {settings.llm_base_url}")
    print(f"API Key: {settings.deepseek_api_key[:8]}…")

    try:
        client = LLMClient()
    except LLMError as exc:
        print(f"初始化客户端失败: {exc}", file=sys.stderr)
        return 1

    if run_memory:
        await run_memory_demo(client)
        print("\n" + "=" * 72)
        print("记忆系统手动测试完成。")

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
