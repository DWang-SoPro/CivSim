# 命令行 → Web 接线清单

> 目标：把 `_manual_test.py` 里已跑通的完整回合，包装成 REST + WebSocket，供 Phase 4 前端使用。  
> 真相源：`backend/engine/action_resolver.resolve_full_turn`、`backend/memory/*`、`backend/llm/*`。

---

## 1. 当前完整回合流程（CLI 已跑通）

入口对照：

| 入口 | 文件 |
| --- | --- |
| 完整回合手测 | `uv run python -m backend.llm._manual_test --fullturn` |
| 记忆系统手测 | `uv run python -m backend.llm._manual_test --memory` |
| 纯数值假行动 | `resolve_turn` + `FakeActionInput`（pytest，无 LLM） |

### 1.1 逐步 → 内部函数

| 步 | 做什么 | 函数 / 模块 | 备注 |
| --- | --- | --- | --- |
| 0 | 加载文明状态 | `load_civ_state(template_id)` | `backend/templates/civilizations.py` |
| 1 | 任务拆分 | `split_tasks(player_input)` | `backend/llm/task_splitter.py`；&lt;10 字短路不调 LLM |
| 2 | 意图解析（每子任务） | `parse_intent(text, state)` | `backend/llm/intent_parser.py` → `IntentResult` |
| 2a | 模糊分支 | `IntentResult.is_too_vague` | **引擎内已接线**：全模糊则 `settlement_skipped=True`，返回 `vague_prompts`，不改状态。`intent_parser.parse_intent` 文档字符串里仍有过时 `TODO(管线)`，以 `resolve_full_turn` 为准 |
| 2b | 知识注入标志 | `is_knowledge_injection` / `knowledge_detail_level` | **仅判定**；`knowledge_evaluator.evaluate_knowledge_injection` 仍 `NotImplementedError`，全回合管线**未**切入评估支路 |
| 3 | 估算张力 | `estimate_class_tension` / `estimate_elite_cohesion` | `action_resolver.py` |
| 4 | 社会摩擦阻力 | `compute_resistance(...)` | `backend/engine/friction.py` |
| 5 | 三层国力 + 稀释 | `settle_from_state(state, [(scale, gap), ...])` | `backend/engine/capacity.py`；产出 `dilution_factor` |
| 6 | 成功率 | `compute_p_success_from_state(...)` | `friction.py`；含积累修正 |
| 7 | 掷骰档位 | `roll_result_tier(p_success, rng)` | `friction.py` |
| 8 | 效果倍率 | `effect_multiplier(tier)` | FAILURE=0，DISASTER=-1 |
| 9 | 域基础增量 × 规模 × 档位 × 稀释 | `_base_deltas_for_intent` → `_apply_tier_and_dilution` | `action_resolver.py`；**稀释只乘数值，不改 P_success** |
| 10 | 时间跨度 | `max(sub.time_estimate_years)`（前置失败钳 ≤2） | 可变时间；推进 `state.year` |
| 11 | 汇总写回状态 | `_apply_aggregated_to_state` | 内含 food / population / stability / authority / accumulation / tech 等 |
| 12 | 被动事件 | `check_passive_events` | **占位，恒 `[]`**，未接入 `resolve_full_turn` |
| 13 | 记忆检索 | `retrieve_history_context(store, domain_tags, state)` | **不在** `resolve_full_turn` 内；由调用方先取再传入 `history_context` |
| 14 | 组装叙事输入 | 构造 `NarrationInput` | `resolve_full_turn` 内；含 `history_context` |
| 15 | 叙事 | `narrate` 或 `narrate_stream` | CLI 默认同步 `narrate`；Web 应用 `narrate_stream` |
| 16 | 记忆落库 | `commit_turn_memory(...)` | `backend/memory/pipeline.py`：turns → landmarks → 每 5 回合 summary |
| 17 | Game Over | `check_game_over(state)` | **极简**：仅 `population <= 0`；未接文档第八节完整条件 |

`resolve_full_turn` 已串联 **1–11 + 14–15**（15 可选）。**13、16、17、12** 需 API 编排层补上。

---

## 2. 哪些内部函数要包成 API

| API | 包装方式 |
| --- | --- |
| `POST /api/game/new` | `load_civ_state` + 分配 `game_id` + 建 `MemoryStore`/DB 行 + 返回 `state` |
| `GET /api/game/{id}` | 读会话 `CivState` + `status` |
| `POST /api/game/{id}/action` | 见下一节主编排 |
| `GET /api/game/{id}/menu` | `generate_action_menu(state)`（需先实现菜单数据） |
| `GET /api/game/{id}/history` | 读 turns（`MemoryStore` 或 SQL） |
| `POST .../save` · `GET .../saves` · `POST .../load` | 序列化 state + memory；DB 或文件 |
| `WS .../ws` | 持有连接；在 action 编排里 `narrate_stream` 推帧 |

**不要**把 `split_tasks` / `parse_intent` / `settle_from_state` 各暴露成独立公开 API（除非做调试面板）。对外只暴露「一回合 action」。

---

## 3. `resolve_full_turn` → `POST /api/game/{id}/action`

### 3.1 推荐服务端编排（伪代码）

```python
async def handle_action(game_id, player_input, ws_hub):
    session = load_session(game_id)          # state, store, seed, status
    if session.status == "game_over":
        raise HTTPException(400, "game over")

    result = await resolve_full_turn(
        session.state,
        player_input,
        client=llm,
        rng_seed=session.next_seed(),
        generate_narrative=False,            # 关键：禁止内部同步 narrate
        history_context=None,                # 先结算，再检索
    )

    if result.settlement_skipped:
        return SubmitActionResponse(
            settlement_skipped=True,
            vague_prompts=result.vague_prompts,
            state=session.state,             # 未变
            ...
        )

    domain_tags = list({
        s.intent.action_domain.value
        for s in result.subtasks
        if not s.skipped_vague
    })
    history = retrieve_history_context(
        session.store,
        domain_tags=domain_tags,
        state=result.state_before,          # 积累值用行动前或后均可；现实现读传入 state
        landmark_limit=5,
        summary_limit=3,
    )
    assert result.narration_input is not None
    result.narration_input.history_context = history

    stream_id = new_stream_id()
    # 先返回 REST（含 state_after、dimension_changes），再异步推 WS
    asyncio.create_task(stream_narrative(ws_hub, game_id, stream_id, result.narration_input))

    session.state = result.state_after
    session.state.turn += 1                  # 若 resolve 内未自增 turn，在此对齐
    # 注意：核对 resolve / _apply_aggregated 是否已更新 turn/year —— 以代码为准

    await commit_turn_memory(
        session.store,
        turn=session.state.turn,
        year_start=result.state_before.year,
        state_before=result.state_before,
        state_after=result.state_after,
        player_input=player_input,
        action_description=result.narration_input.action_description,
        result_tier=result.overall_tier.value,
        dimension_changes=result.dimension_changes,
        narrative="",                        # 可先空，WS 结束后回填
        domain_tags=domain_tags,
        events=result.events,
        client=llm,
        full_result=result,
    )

    reason = check_game_over(session.state)
    if reason:
        session.status = "game_over"

    persist(session)
    return SubmitActionResponse(..., ws_stream_id=stream_id, state=session.state, ...)
```

### 3.2 回合号 / 年份注意点

- `CivState.year` 在 `_apply_aggregated_to_state` 中按 `turn_years` 推进。
- `CivState.turn`：确认 `resolve_full_turn` 是否递增；`--memory` 手测里有脚本化 `turn=`。接线时**统一**「先结算再 `turn += 1`」或「结算内递增」，并与 `commit_turn_memory(turn=...)` 一致。
- 建议在 Phase 4 开干前读一遍 `_apply_aggregated_to_state`（`action_resolver.py`）确认 turn 字段行为。

### 3.3 模糊输入（`is_too_vague`）

| 层 | 状态 |
| --- | --- |
| LLM 判定 | ✅ `IntentResult` 字段齐全 |
| `resolve_full_turn` | ✅ 全模糊跳过结算；部分模糊则跳过该子任务并可能把反问附在 narrative 后 |
| HTTP 契约 | ⬜ 应用 `settlement_skipped` + `vague_prompts` 明确返回，前端进入「待澄清」态 |
| 过时注释 | `parse_intent` 仍写 TODO — 接线时删掉以免误导 |

---

## 4. 流式叙事如何走 WebSocket

| 项 | 说明 |
| --- | --- |
| 流式源 | `narrate_stream(NarrationInput)` → `LLMClient.call_text_stream`（thinking 关闭） |
| 帧格式 | 见 `api_contract.md` §3：`narrative_start` / `narrative_delta` / `narrative_end` |
| 与 REST 分工 | REST：数值与状态；WS：叙事文本 |
| CLI 差异 | `--fullturn` 用同步 `narrate`；`--narrator` 可测流式时延 |

```python
async def stream_narrative(hub, game_id, stream_id, payload: NarrationInput):
    await hub.send(game_id, {"type": "narrative_start", "stream_id": stream_id, ...})
    parts = []
    try:
        async for chunk in narrate_stream(payload, client=llm):
            parts.append(chunk)
            await hub.send(game_id, {
                "type": "narrative_delta",
                "stream_id": stream_id,
                "payload": {"text": chunk},
            })
        full = "".join(parts)
        await hub.send(game_id, {
            "type": "narrative_end",
            "stream_id": stream_id,
            "payload": {"full_text": full},
        })
        # 回填 turns.narrative
    except Exception as e:
        await hub.send(game_id, {"type": "narrative_error", "payload": {"message": str(e)}})
```

---

## 5. 记忆系统（retriever）何时调用

```
时间线（单回合）:
  split → intent → capacity → dice → apply state
       → 【这里】retrieve_history_context(domain_tags from intents, accumulations from state)
       → narrate_stream(history_context=...)
       → commit_turn_memory  # 写 turn；检测 landmark；turn%5==0 时 LLM 摘要
```

| 函数 | 时机 |
| --- | --- |
| `retrieve_history_context` | **叙事前**；需要已有 `domain_tags`（来自本回合 intent） |
| `commit_turn_memory` | **叙事后**（或 REST 返回后异步）；依赖 `state_before/after` |
| `maybe_create_summary` | 在 `commit_turn_memory` 内，`current_turn % 5 == 0` |
| `create_landmarks_from_turn` | 在 `commit_turn_memory` 内，对比 before/after |

**存储：** Phase 3 默认 `MemoryStore`（内存）。Phase 4 需 PostgreSQL 实现同接口，或先把 `MemoryStore` 挂在进程内会话（单机可玩，重启丢档）。

**向量：** `embed_text` 返回 `None`；`query_landmarks_vector` 抛 `NotImplementedError`。检索策略参数 `landmark_strategy=` 可替换，默认 `keyword_landmark_strategy`。

---

## 6. 存档 / 读档接入点

| 时机 | 动作 |
| --- | --- |
| `POST /save` | 序列化：`CivState` + `MemoryStore` 中 turns/summaries/landmarks + `status` + `seed` |
| `POST /load` | 反序列化 → 新会话；**不要**在 action 中途读档 |
| 每回合结束 | 可选 autosave 当前 `game_states`（GDD 时序 2.g–h） |
| DB | 迁移已有：`001_initial.sql`、`002_landmarks_embedding.sql`；`database.py` 池子占位；**无** Repository 层 |

建议最小持久化顺序：

1. MVP：进程内 dict + JSON 文件存档  
2. 再接 `asyncpg` 读写 `games` / `game_states` / `turns` / …

---

## 7. Game Over 接入点

```
resolve_full_turn 成功且 state_after 已写出
  → check_game_over(state_after)
  → 若非 None：session.status = "game_over"；响应带 reason；拒绝后续 action
```

当前实现（`backend/engine/gameover.py`）：

```python
if state.population <= 0: return "civilization_collapse"
return None
```

文档第八节（叛乱失控、精英瓦解等）**未实现** — Phase 4/5 补条件时只改 `check_game_over`，接入点不变。

---

## 8. FastAPI 接线 TODO 清单（可当看板）

- [ ] `main.py`：`include_router` game/action/websocket；CORS
- [ ] 会话容器：`game_id → {state, store, status, seed}`
- [ ] `POST /new` / `GET /{id}`
- [ ] `POST /{id}/action` 编排（§3.1）
- [ ] WS hub + 帧协议
- [ ] `generate_narrative=False` + `narrate_stream` 替换同步叙事
- [ ] `retrieve_history_context` + `commit_turn_memory` 接入 action
- [ ] `check_game_over` 接入
- [ ] history / menu / save / load
- [ ]（可选）回合结束后回填 `turns.narrative`
- [ ] 删除/更正 `parse_intent` 过时 TODO 注释
- [ ] 导出更新后的 `HANDOFF/openapi.json`

---

## 9. 前端最小对接顺序建议

1. `POST /new`（`zhou`）→ 渲染状态面板  
2. 连 WS  
3. `POST /action` → 更新数值；WS 打字机叙事  
4. 处理 `vague_prompts` UI  
5. history 卷轴  
6. save/load  
7. menu（等后端菜单数据）
