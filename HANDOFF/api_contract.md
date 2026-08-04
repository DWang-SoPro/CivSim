# CivSim v2 — API 契约（Phase 4 接线用）

> 状态：Phase 4 最小可玩闭环已接线；本文档记录当前的纯流式交互契约。
> 设计依据：`civsim-v2-gdd.md` §10.4–10.5；内部逻辑见 `backend/engine/action_resolver.py` 与 `HANDOFF/wiring_todo.md`。  
> 机器可读快照：同目录 `openapi.json`。WebSocket 帧不会出现在 OpenAPI 中，以本文档 §3 为准。

---

## 0. 通用约定

| 项 | 约定 |
| --- | --- |
| Base URL | `http://localhost:8000`（开发） |
| 路径前缀 | `/api/game/...`（健康检查除外） |
| ID 类型 | `game_id` / `save_id`：UUID 字符串 |
| 状态体 | `CivState`（`backend/models/schemas.py`），JSON 序列化用 `model_dump()` |
| 错误体 | `{ "detail": string \| object }`（FastAPI 默认）；业务码见各端点 |
| CORS | 已放行 `localhost:3000` 与 `127.0.0.1:3000` 的 Next.js 开发源 |
| 鉴权 | MVP 无鉴权；单机本地会话即可 |

**已挂载路由：**

- `backend/api/game.py` — prefix `/api/game`（new / menu / save / saves / load / delete save / debug/end）
- `backend/api/action.py` — prefix `/api/game`（action）
- `backend/api/websocket.py` — 无 prefix
- `backend/main.py` — 注册健康检查、游戏、行动与 WebSocket 路由
- 存档文件：`data/civsim.sqlite`（MVP，无需 PostgreSQL）

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

## 2. 游戏端点

下列 new/action 为当前已实现契约；其余端点仍是后续建议。

### 2.1 `POST /api/game/new` — 新建游戏

| | |
| --- | --- |
| 状态 | ✅ Phase 4 MVP 已实现（进程内会话） |
| 内部函数 | `load_civ_state(template_id)` → `generate_opening_narrative(state)` → 建立内存会话；开场生成成功后才注册会话 |

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
| `opening_narrative` | `str` | 基于完整初始状态生成的 150–250 字白话史官开场；前端作为第 0 回合叙事展示 |

**错误**

| HTTP | 条件 |
| --- | --- |
| 400 | `template_id` 非法 |
| 503 | 开场 LLM 调用失败，或两次输出均未满足字数要求；不会创建残留会话 |
| 500 | 其他未预期的模板加载 / 会话创建失败 |

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
| 状态 | ✅ Phase 4 MVP 已实现 |
| 内部编排 | 见 `wiring_todo.md`；核心结算 `resolve_full_turn`；记忆 `retrieve_history_context` + `commit_turn_memory` |
| 叙事 | REST **不**返回完整叙事正文；正文与最终状态走 WebSocket 纯流式序列 |

**请求 `SubmitActionRequest`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `input` | `str` | 玩家自然语言政令，非空 |
| `rng_seed` | `int \| null` | 可选覆盖本回合种子（调试用） |
| `stream_id` | `str (UUID) \| null` | 客户端建议在提交前生成；服务端从第一个 WS 帧起原样回传，未传则由服务端生成 |

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
| `game_over` | `bool` | state-ready 响应中为 `false`；最终结果以后续 WS `game_over` 帧为准 |
| `game_over_reason` | `str \| null` | state-ready 响应中为 `null` |
| `ws_stream_id` | `str \| null` | 本回合流 ID；与请求 `stream_id` 一致（模糊短路时为 `null`） |

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
| 422 | `stream_id` 不是合法 UUID，或其他请求 schema 错误 |
| 排队 | 上一回合正在提交记忆时，新回合在本局互斥锁上等待，不返回 409 |
| 502 / 503 | LLM 调用失败，或上一回合记忆收尾未知失败后会话被安全停止 |

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
    推 narrative_end
    推 state_update（玩家回合在此完成）
    check_game_over（命中则推 game_over）
    后台 commit_turn_memory(...)
```

说明：当前 `resolve_full_turn` 接受外部传入的 `history_context`，并在 `generate_narrative=True` 时**同步**调用 `narrate()`（非流式）。Web 接线应设 `generate_narrative=False`，叙事改走 WS。

---

### 2.4 `GET /api/game/{id}/menu` — 行动菜单

| | |
| --- | --- |
| 状态 | ✅ 已实现 |
| 内部 | `backend.templates.actions.generate_action_menu(state)` — 按前置条件筛选行动库 |

**响应 `ActionMenuResponse`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `game_id` | `str` | |
| `items` | `list[ActionMenuItem]` | 当前可用行动；点击后填入输入框，仍走自然语言 action |

`ActionMenuItem`

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `id` | `str` | 行动 ID |
| `name` / `label` | `str` | 展示名 |
| `domain` | `str` | `economic` \| `political` \| `military` \| `cultural` \| `technology` \| `composite` |
| `domain_label` | `str` | 中文域名 |
| `description` | `str` | 一句话说明 |
| `difficulty_hint` | `str` | `容易` \| `中等` \| `困难` \| `极难` |
| `suggested_input` | `str` | 填入输入栏的文本 |
| `disabled` | `bool` | 当前实现仅返回可用项，恒为 `false` |
| `reason` | `str\|null` | 禁用理由（预留） |

**错误：** `404` 局不存在

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
| 状态 | ✅ 已实现（SQLite：`data/civsim.sqlite`） |
| 内部 | 序列化 `CivState` + turns/summaries/landmarks + 会话峰值元数据 → `saves` 表 |

**请求 `SaveGameRequest`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `slot_name` | `str\|null` | 可选存档名；空则自动命名 |
| `autosave` | `bool` | `true` 时覆盖本局自动档 |

**响应 `SaveGameResponse`**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `save_id` | `str` | |
| `saved_at` | `str` (ISO8601) | |
| `slot_name` | `str\|null` | |

说明：每回合结算完成后会自动覆盖同一自动档；开局也会创建自动档。

**错误：** `404` / `500`

---

### 2.7 `GET /api/game/saves` — 列出存档

| | |
| --- | --- |
| 状态 | ✅ 已实现 |

**响应：** `{ "saves": [ { "save_id", "slot_name", "civ_name", "template_id", "turn", "year", "saved_at", "is_autosave" } ] }`

---

### 2.7.1 `DELETE /api/game/saves/{save_id}` — 删除存档

| | |
| --- | --- |
| 状态 | ✅ 已实现 |

**响应：** `{ "ok": true, "save_id": "<uuid>" }`

若内存会话的 `autosave_id` 指向被删档，会清空该引用。

**错误：** `404` 存档不存在

---

### 2.8 `POST /api/game/load/{save_id}` — 读档

| | |
| --- | --- |
| 状态 | ✅ 已实现 |

**响应：** 同 `NewGameResponse`，并额外可选：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `history` | `list[{turn,year,text}]\|null` | 叙事卷轴历史 |
| `status` | `str\|null` | |
| `game_over_reason` | `str\|null` | |
| `autosave_id` | `str\|null` | |

读档会创建**新的** `game_id` 活跃会话，避免并发写冲突。

**错误：** `404` 存档不存在

### 2.9 `POST /api/game/{id}/debug/end` — 强制终局（开发验收）

| | |
| --- | --- |
| 状态 | ✅ 开发用 |
| 说明 | 广播完整 `game_over` 帧（含历史教训），便于 UI 截图验收 |

---

## 3. WebSocket — 流式叙事

### `WS /api/game/{id}/ws`

| | |
| --- | --- |
| 状态 | ✅ Phase 4 MVP 已实现 |
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
  "type": "narrative_start | narrative_delta | narrative_end | state_update | game_over | narrative_error | ping",
  "turn": 8,
  "stream_id": "与 action 请求/响应对齐的 UUID",
  "payload": {}
}
```

| `type` | `payload` | 含义 |
| --- | --- | --- |
| `narrative_start` | `{ "action_description", "result_tier", "importance" }` | 本回合叙事开始；前端清空「进行中」缓冲 |
| `narrative_delta` | `{ "text": "……" }` | 增量文本块（模型 token/片段，非固定字数） |
| `narrative_end` | `{ "full_text": "……", "dimension_changes": {} }` | 结束信号；可用 `full_text` 做校验拼接 |
| `state_update` | `{ "state": CivState, "dimension_changes": {} }` | 紧跟 `narrative_end`；最终数值已提交，客户端更新面板并立即解锁下一回合 |
| `game_over` | 见下表 | 仅终局检查命中时，在 `state_update` 之后发送 |
| `narrative_error` | `{ "message": "…" }` | 流式失败；前端展示错误并允许重试（若实现） |
| `ping` | `{}` | 心跳（可选） |

`game_over.payload`：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `reason` | `str` | `rebellion_out_of_control` \| `elite_collapse` \| `civilization_collapse` |
| `reason_label` | `str` | 叛乱失控 / 精英瓦解 / 文明崩溃 |
| `civ_name` | `str` | |
| `total_turns` | `int` | |
| `year_start` / `year_end` | `float` | |
| `peak_population` / `peak_territory` | `int` | |
| `achievements` | `list[{turn,year,title,summary}]` | 来自 landmarks |
| `historical_lesson` | `str` | LLM 生成的 2–3 句反思（失败时回退固定文案） |

**开始/结束硬性约定**

1. 每个成功结算且需叙事的回合：**恰好一组** `narrative_start` → 若干 `narrative_delta` → `narrative_end` → `state_update`。
2. `settlement_skipped`（模糊反问）：**不**发叙事流；反问在 REST `vague_prompts` 中返回。
3. 客户端以 `state_update` 为「玩家的本回合完成」信号；`narrative_end` 只表示文本已结束。
4. 服务端在 `state_update` 之后才做 Game Over 检查和记忆提交；记忆提交不阻塞前端解锁。
5. 所有帧均带同一 `turn` 与 `stream_id`，客户端必须据此拒绝迟到旧帧。

#### 3.3 客户端 → 服务端（可选）

MVP 可不需要客户端发消息。若需要：

```json
{ "type": "subscribe", "stream_id": "..." }
```

#### 3.4 纯流式时序（当前实现）

```
Client                    REST                         WS
  |-- POST /action ------->|                            |
  |                        |-- settle (no narrate) ---> |
  |                        |-- retrieve history ------->|
  |                        |-- narrative_start -------->|
  |                        |-- narrative_delta* -------->|
  |                        |-- narrative_end ----------->|
  |                        |-- state_update ------------>|
  |<-- SubmitActionResponse-|                            |
  |                        |-- game_over? -------------->|
  |                        |-- commit memory / summary  |
  |-- next POST /action -->|-- wait same-game lock ---->|
```

`state_update` 一经到达，玩家即可提交下一道政令。若上一回合的记忆收尾
仍在进行（尤其第 5、10… 回合的 LLM 摘要），新请求会在每局互斥锁上等待，
确保记忆严格按回合顺序写入。

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

- 当前导出：`HANDOFF/openapi.json`（`/health`、`/api/game/new`、`/api/game/{game_id}/action`）。
- HTTP schema 变更后重新导出：

```bash
uv run python -c "from backend.main import app; import json; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" > HANDOFF/openapi.json
```

或访问：`http://localhost:8000/docs` / `/openapi.json`。
