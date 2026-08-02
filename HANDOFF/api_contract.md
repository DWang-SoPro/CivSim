# CivSim v2 — API 契约（Phase 4 接线用）

> 状态：截至 Phase 3 结束。FastAPI 仅挂载 `GET /health`；其余端点均为**待接线**契约，供前端与 API 层对齐。  
> 设计依据：`civsim-v2-gdd.md` §10.4–10.5；内部逻辑见 `backend/engine/action_resolver.py` 与 `HANDOFF/wiring_todo.md`。  
> 机器可读快照：同目录 `openapi.json`（当前仅含 `/health`）。

---

## 0. 通用约定

| 项 | 约定 |
| --- | --- |
| Base URL | `http://localhost:8000`（开发） |
| 路径前缀 | `/api/game/...`（健康检查除外） |
| ID 类型 | `game_id` / `save_id`：UUID 字符串 |
| 状态体 | `CivState`（`backend/models/schemas.py`），JSON 序列化用 `model_dump()` |
| 错误体 | `{ "detail": string \| object }`（FastAPI 默认）；业务码见各端点 |
| CORS | 待接线时需对 Next.js 开发源放行 |
| 鉴权 | MVP 无鉴权；单机本地会话即可 |

**路由模块占位（未 `include_router`）：**

- `backend/api/game.py` — prefix `/api/game`
- `backend/api/action.py` — prefix `/api/game`
- `backend/api/websocket.py` — 无 prefix
- `backend/main.py` — 仅注册 `GET /health`

---

## 1. 已实现

### `GET /health`

| | |
| --- | --- |
| 状态 | ✅ 已实现（`backend/main.py`） |
| 输入 | 无 |
| 输出 | `{ "status": "ok" }` |
| 错误 | 无 |

---

## 2. 待接线端点

下列 schema 为**推荐契约**（Phase 4 可微调字段名，但建议与下表对齐，减少前端返工）。

### 2.1 `POST /api/game/new` — 新建游戏

| | |
| --- | --- |
| 状态 | ⬜ 待接线 |
| 内部函数 | `backend.templates.civilizations.load_civ_state(template_id)`；写入 `games` + `game_states`（DB 读写待做，可先内存 `dict[game_id, session]`） |

**请求 `NewGameRequest`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `template_id` | `str` | 开局模板：`sumer` \| `egypt` \| `harappa` \| `babylon` \| `zhou` \| `greece` |
| `seed` | `int \| null` | 可选；本局掷骰默认种子（未传则服务端生成） |

**响应 `NewGameResponse`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `game_id` | `str` (UUID) | 新局 ID |
| `state` | `CivState` | 初始完整状态 |
| `seed` | `int` | 实际使用的 RNG 种子 |

**错误**

| HTTP | 条件 |
| --- | --- |
| 400 | `template_id` 非法 |
| 500 | 模板加载 / DB 失败 |

---

### 2.2 `GET /api/game/{id}` — 获取游戏状态

| | |
| --- | --- |
| 状态 | ⬜ 待接线 |
| 内部 | 从 `game_states` / 内存会话读取 `CivState` |

**路径参数：** `id: UUID`

**响应 `GameStateResponse`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `game_id` | `str` | |
| `status` | `str` | `active` \| `game_over` \| `awaiting_clarification`（建议） |
| `state` | `CivState` | 当前状态 |
| `game_over_reason` | `str \| null` | 见 `check_game_over` |
| `pending_clarification` | `list[str] \| null` | 上一回合模糊反问尚未被新输入覆盖时可选返回 |

**错误：** `404` 局不存在

---

### 2.3 `POST /api/game/{id}/action` — 提交行动

| | |
| --- | --- |
| 状态 | ⬜ 待接线（核心） |
| 内部编排 | 见 `wiring_todo.md`；核心结算 `resolve_full_turn`；记忆 `retrieve_history_context` + `commit_turn_memory` |
| 叙事 | REST **不**返回完整叙事正文（或只返回摘要）；正文走 WebSocket 流式 |

**请求 `SubmitActionRequest`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `input` | `str` | 玩家自然语言政令，非空 |
| `rng_seed` | `int \| null` | 可选覆盖本回合种子（调试用） |

**响应 `SubmitActionResponse`（同步返回的数值侧结果）**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `game_id` | `str` | |
| `turn` | `int` | 结算后的回合号 |
| `settlement_skipped` | `bool` | `true` = 全模糊，未改状态（见 `FullTurnResult.settlement_skipped`） |
| `vague_prompts` | `list[str]` | 史官反问；非空时应打断常规 UI 流程 |
| `overall_tier` | `str \| null` | `great_success`…`disaster`；跳过时 `null` |
| `turn_years` | `float` | 本回合推进年数 |
| `dimension_changes` | `dict[str, str]` | 如 `{"stability": "+3.2", "population": "+1%"}` |
| `events` | `list[str]` | 引擎生成的事件简述 |
| `importance` | `str` | `normal` \| `major` |
| `state` | `CivState \| null` | 结算后状态；跳过时为原状态或 `null` |
| `intents` | `list[IntentResult]` | 各子任务意图（调试/面板可用；生产可裁剪） |
| `capacity` | `object \| null` | 国力结算摘要（`dilution_factor` 等，可选） |
| `game_over` | `bool` | |
| `game_over_reason` | `str \| null` | |
| `ws_stream_id` | `str \| null` | 建议：本回合叙事流关联 ID；客户端用 WS 收叙事 |

**关键内部类型（已存在，可直接序列化）**

`IntentResult`（`backend/llm/intent_parser.py`）：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `action_domain` | enum | `economic/political/military/cultural/technology/composite` |
| `action_type` | `str` | 短标签 |
| `action_description` | `str` | 行动描述 |
| `cognitive_gap` | `int` 0–5 | 认知代差 |
| `resistance_sources` | `list[str]` | 阻力来源 |
| `beneficiaries` | `list[str]` | 受益方 |
| `prerequisites` | `{met, details, nearest_alternative}` | 前置条件 |
| `is_knowledge_injection` | `bool` | 是否知识注入（仅判定） |
| `knowledge_detail_level` | enum\|null | `concept/direction/operational/detailed` |
| `is_too_vague` | `bool` | 过于模糊 |
| `clarification_prompt` | `str\|null` | 反问文案 |
| `scale` | enum | `small/medium/large` |
| `time_estimate_years` | `float` | 0.1–20 |
| `time_estimate_reasoning` | `str` | 时间估计理由 |

`FullTurnResult`：`backend/engine/action_resolver.py`（勿直接当 HTTP 响应；按上表裁剪）。

**错误**

| HTTP / 业务 | 条件 |
| --- | --- |
| 400 | `input` 空；局已 `game_over` |
| 404 | 局不存在 |
| 409 | 建议：上一回合叙事流未结束又提交（可选） |
| 502 / 503 | LLM 调用失败（DeepSeek） |

**与 `resolve_full_turn` 的关系**

```
# 伪代码（推荐 Phase 4 编排，勿在 resolve 内写死流式）
split+intent 已在 resolve_full_turn 内完成
→ 先 resolve_full_turn(..., generate_narrative=False, history_context=None)
  拿到 intents / state_after / narration_input
→ 若 settlement_skipped: 直接返回 vague_prompts，不推 WS 叙事
→ else:
    history = retrieve_history_context(store, domain_tags=..., state=state_before)
    narration_input.history_context = history
    通过 WS 调用 narrate_stream(narration_input)
    commit_turn_memory(...); check_game_over; 持久化
```

说明：当前 `resolve_full_turn` 接受外部传入的 `history_context`，并在 `generate_narrative=True` 时**同步**调用 `narrate()`（非流式）。Web 接线应设 `generate_narrative=False`，叙事改走 WS。

---

### 2.4 `GET /api/game/{id}/menu` — 行动菜单

| | |
| --- | --- |
| 状态 | ⬜ 待接线 |
| 内部 | `backend.templates.actions.generate_action_menu(state)` — **当前恒返回 `[]`** |

**响应 `ActionMenuResponse`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `items` | `list[ActionMenuItem]` | 参考行动；点击后填入输入框，仍走自然语言 action |

`ActionMenuItem`（建议）

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `id` | `str` | |
| `label` | `str` | 展示名 |
| `suggested_input` | `str` | 填入输入栏的文本 |
| `domain` | `str` | 领域标签 |
| `disabled` | `bool` | 前置不满足时可灰显 |
| `reason` | `str\|null` | 禁用理由 |

**错误：** `404`

---

### 2.5 `GET /api/game/{id}/history` — 历史日志（分页）

| | |
| --- | --- |
| 状态 | ⬜ 待接线 |
| 内部 | 读 `turns` 表 / `MemoryStore.get_recent_turns` / 全量分页 |

**查询参数**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `offset` | `int` | 默认 0 |
| `limit` | `int` | 默认 20，上限建议 50 |

**响应 `HistoryResponse`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `total` | `int` | |
| `items` | `list[TurnHistoryItem]` | 按 turn 降序或升序（建议升序给卷轴） |

`TurnHistoryItem`

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `turn` | `int` | |
| `year_start` / `year_end` | `float` | |
| `player_input` | `str` | |
| `action_description` | `str` | |
| `result_tier` | `str` | |
| `narrative` | `str` | |
| `summary` | `str` | 一句话摘要 |
| `dimension_changes` | `dict[str,str]` | |
| `domain_tags` | `list[str]` | |

**错误：** `404`

---

### 2.6 `POST /api/game/{id}/save` — 存档

| | |
| --- | --- |
| 状态 | ⬜ 待接线 |
| 内部 | 序列化 `CivState` + 记忆（turns/summaries/landmarks）→ `saves` 或复用 `games` 快照表（schema 见迁移；独立 saves 表 GDD 未单独建，Phase 4 可新增或用 JSON 文件） |

**请求 `SaveGameRequest`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `slot_name` | `str\|null` | 可选存档名 |

**响应 `SaveGameResponse`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `save_id` | `str` | |
| `saved_at` | `str` (ISO8601) | |
| `slot_name` | `str\|null` | |

**错误：** `404` / `500`

---

### 2.7 `GET /api/game/saves` — 列出存档

| | |
| --- | --- |
| 状态 | ⬜ 待接线 |

**响应：** `{ "saves": [ { "save_id", "slot_name", "civ_name", "template_id", "turn", "year", "saved_at" } ] }`

---

### 2.8 `POST /api/game/load/{save_id}` — 读档

| | |
| --- | --- |
| 状态 | ⬜ 待接线 |

**响应：** 同 `NewGameResponse`（新的或恢复的 `game_id` + `state`），或直接恢复原 `game_id`（二选一，建议：**恢复为新活跃会话并返回新 `game_id`**，避免并发写冲突）。

**错误：** `404` 存档不存在

---

## 3. WebSocket — 流式叙事

### `WS /api/game/{id}/ws`

| | |
| --- | --- |
| 状态 | ⬜ 待接线（`backend/api/websocket.py` 空壳） |
| 内部 | `backend.llm.narrator.narrate_stream(NarrationInput)` → `LLMClient.call_text_stream` |

#### 3.1 连接

- URL：`ws://localhost:8000/api/game/{id}/ws`
- 建议查询参数：`?client_id=`（可选）
- 连接时机：进入游戏页即连；断线自动重连
- 一局一个 WS；多标签页需约定（MVP 单连接）

#### 3.2 服务端 → 客户端消息（JSON 文本帧）

统一信封：

```json
{
  "type": "narrative_start | narrative_delta | narrative_end | narrative_error | ping | state_patch",
  "turn": 8,
  "stream_id": "可选，与 action 响应的 ws_stream_id 对齐",
  "payload": {}
}
```

| `type` | `payload` | 含义 |
| --- | --- | --- |
| `narrative_start` | `{ "action_description", "result_tier", "importance" }` | 本回合叙事开始；前端清空「进行中」缓冲 |
| `narrative_delta` | `{ "text": "……" }` | 增量文本块（模型 token/片段，非固定字数） |
| `narrative_end` | `{ "full_text": "……", "dimension_changes": {} }` | 结束信号；可用 `full_text` 做校验拼接 |
| `narrative_error` | `{ "message": "…" }` | 流式失败；前端展示错误并允许重试（若实现） |
| `state_patch` | `{ "state": CivState }` | 可选：叙事结束后再推一次状态（若 REST 已含 state 可省略） |
| `ping` | `{}` | 心跳（可选） |

**开始/结束硬性约定**

1. 每个成功结算且需叙事的回合：**恰好一对** `narrative_start` → 若干 `narrative_delta` → `narrative_end`。
2. `settlement_skipped`（模糊反问）：**不**发叙事流；反问在 REST `vague_prompts` 中返回。
3. 客户端以 `narrative_end` 为「本回合叙事完成」信号，再解锁下一轮输入（可与 REST 返回并行：REST 先到、WS 后到）。

#### 3.3 客户端 → 服务端（可选）

MVP 可不需要客户端发消息。若需要：

```json
{ "type": "subscribe", "stream_id": "..." }
```

#### 3.4 与 REST 时序（推荐）

```
Client                    REST                         WS
  |-- POST /action ------->|                            |
  |                        |-- settle (no narrate) ---> |
  |                        |-- retrieve history ------->|
  |<-- SubmitActionResponse-|                            |
  |                        |-- narrative_start -------->|
  |                        |-- narrative_delta* -------->|
  |                        |-- narrative_end ----------->|
  |                        |-- commit memory / save --->|
```

---

## 4. CivState 字段速查（响应中的 `state`）

完整定义：`backend/models/schemas.py`。顶层字段：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `civ_name` / `template_id` | str | 文明名 / 模板 ID |
| `turn` / `year` | int / float | 回合、年份（负=公元前） |
| `population` | int | 人口 |
| `tech_agriculture` / `tech_engineering` / `tech_knowledge` | float | 三技术线 |
| `territory_core` / `territory_frontier` | int | 核心/边疆 km² |
| `biome_fertility` | float 0–1 | 生态肥力 |
| `agricultural_modifier` | float | 模板农业禀赋 |
| `land_system` | enum | 土地制度 |
| `labor_distribution` | 四比例和=1 | 劳动形态 |
| `surplus_extraction` | list[enum] | 剩余提取 |
| `polity` | 三子枚举 | 权力来源×决策×继承 |
| `bureaucratization` | float 0–1 | 官僚化 |
| `legitimacy` | 四浮点 | 合法性结构 |
| `religions` | list | 宗教实体（结构有，深度逻辑未做） |
| `stability` / `authority` | float 0–100 | 稳定 / 统治力 |
| `class_tension` / `elite_cohesion` | float\|null | 社会张力 |
| `accumulations` | 五域 float | 路径积累 |
| `knowledge_institution_coverage` | float | 知识机构覆盖 |

派生方法（不一定序列化）：`legitimacy_total()`、`literacy_rate()`。

---

## 5. OpenAPI

- 当前导出：`HANDOFF/openapi.json`（仅 `/health`）。
- Phase 4 实现端点后，重新导出：

```bash
uv run python -c "from backend.main import app; import json; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" > HANDOFF/openapi.json
```

或访问：`http://localhost:8000/docs` / `/openapi.json`。
