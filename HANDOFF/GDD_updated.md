# 文明灵 CivSim v2 — 设计文档（交接更新版）

> **本文定位**：给 Phase 4 新工具/新同学的「设计意图 vs 当前实现」说明书。  
> **完整原始 GDD**：仓库根目录 [`civsim-v2-gdd.md`](../civsim-v2-gdd.md)（机制公式、模板叙事、UI 方向仍以原文为准）。  
> **版本锚点**：Phase 1–3 已落地；Phase 4 = 前端 + API 接线。  
> **图例**：✅ 完成 · ⏳ 部分 · ⬜ 未做

---

## 一、项目一句话与原则（未变）

玩家以**王朝/统治集团**视角用自然语言下达政令。LLM 做定性与史官叙事，数学引擎做一切定量。核心约束：社会存在约束意志（防梦、路径依赖、层层约束、渐进演化）。

原始循环见 GDD §1.4。实施后的真实循环见下文「模块完成度」与 `wiring_todo.md`。

---

## 二、模块完成度总表

| 模块 | 路径 | 完成度 | 说明 |
| --- | --- | --- | --- |
| CivState 数据模型 | `backend/models/schemas.py` | ✅ | 四层维度 + 积累 + `agricultural_modifier` |
| 六文明模板 | `backend/templates/civilizations.py` | ✅ | sumer/egypt/harappa/babylon/zhou/greece |
| 社会摩擦 / 掷骰 | `backend/engine/friction.py` | ✅ | 含 RESULT_TABLE、AUTHORITY_MOD |
| 治理效率 | `backend/engine/governance.py` | ✅ | |
| 粮食盈余 | `backend/engine/food.py` | ✅ | `YIELD_FACTOR` + 模板 modifier |
| 人口 | `backend/engine/population.py` | ✅ | |
| 稳定性 | `backend/engine/stability.py` | ✅ | |
| 统治力 | `backend/engine/authority.py` | ✅ | |
| 积累值 | `backend/engine/accumulation.py` | ✅ | 贡献 + 衰减；已进全回合 |
| **三层国力 capacity** | `backend/engine/capacity.py` | ✅ | **GDD 原稿无此独立章**；Phase 2 新增 |
| 假行动结算 | `resolve_turn` | ✅ | pytest 用 |
| TaskSplitter | `backend/llm/task_splitter.py` | ✅ | |
| IntentParser | `backend/llm/intent_parser.py` | ✅ | 含 scale / vague / 知识注入**判定** |
| Narrator | `backend/llm/narrator.py` | ✅ | 白话史官；history + 积累提示词已接 |
| LLM Client | `backend/llm/client.py` | ✅ | DeepSeek V4 Flash；json + stream |
| 全链路回合 | `resolve_full_turn` | ✅ | CLI/`--fullturn` 可跑；**无 HTTP** |
| 模糊输入反问 | `is_too_vague` | ⏳ | **引擎已跳过结算**；API/前端未接；`parse_intent` 残留过时 TODO 注释 |
| 知识注入评估 | `knowledge_evaluator.py` | ⬜ | 意图侧仅打标；评估函数 `NotImplementedError`；结算未走特殊管线 |
| 三层记忆 | `backend/memory/*` | ✅ | recent / summary / landmark + retriever；内存 `MemoryStore` |
| 向量检索 | `embed_text` / landmarks.embedding | ⏳ | **字段与接口预留**；实现推迟；现用关键词 tags |
| 行动菜单 | `templates/actions.py` | ⬜ | `generate_action_menu` → `[]` |
| 被动事件 | `passive_events.py` | ⬜ | 恒 `[]`，且未接入 `resolve_full_turn` |
| Game Over | `gameover.py` | ⏳ | 仅人口归零；文档第八节未做深 |
| 宗教**计算** | schemas + landmark 检测 | ⏳ | **数据结构齐全**；摩擦里 `religious_resistance` 默认 0；无改教/神权深度逻辑 |
| PostgreSQL schema | `db/migrations/*.sql` | ⏳ | SQL 已写；Repository/API 未接；手测走内存 |
| FastAPI 游戏 API | `backend/api/*` | ⬜ | 仅根 `GET /health` |
| WebSocket 叙事 | `api/websocket.py` | ⬜ | |
| 前端卷轴 UI | `frontend/` | ⬜ | Next.js 15 骨架页 |
| 存档读档 API | — | ⬜ | |

---

## 三、设计意图 vs 当前实现（关键变更）

### 3.1 三层国力模型（资源 × 权力 × 难度）— **新增于实现**

| | |
| --- | --- |
| 设计意图（演进后） | 行动不是「想做多大就做多大」。先算国力池，再算权力能传导多少，再按行动规模与认知难度算需求；超支则**稀释数值效果**。 |
| 当前实现 | `CapacityParams` + `settle_from_state`（`backend/engine/capacity.py`） |
| 公式摘要 | `capacity = BASE × food_factor × bureau_factor × gov_factor`<br>`available = capacity × transmission`<br>`demand = SCALE_COST[scale] × (1 + cognitive_gap × resistance)`<br>`dilution = max((available/total_demand)^EXP, FLOOR)` |
| 硬约定 | **`dilution_factor` 只乘数值，不改 `P_success`** |
| GDD 原文 | 无独立「国力池」章节；Phase 2 联调引入，以代码与 `tunable_params.md` 为准 |

### 3.2 `dilution_floor = 0.28`

| | |
| --- | --- |
| 设计意图 | 严重超支时仍保留「办成半拉子」的可见痕迹，避免效果≈0 导致叙事与面板无感。 |
| 当前实现 | `CapacityParams.DILUTION_FLOOR = 0.28`，`DILUTION_EXPONENT = 1.5` |
| 调参 | 第五阶段平衡主旋钮之一 |

### 3.3 意图解析 `scale` 字段

| | |
| --- | --- |
| 设计意图 | LLM 判定行动牵动人力物力与结构深度：`small` / `medium` / `large`。 |
| 当前实现 | `IntentResult.scale`；喂入国力 `SCALE_COST`；并乘 `_SCALE_EFFECT`（0.5/1/2）放大基础数值 |
| 锚点 | 小：遣使/小政令；中：水利/学宫；大：迁都/变法/灭国之战 |

### 3.4 可变时间跨度

| | |
| --- | --- |
| 设计意图（GDD） | 不同行动消耗不同年数，而非固定 1 年/回合。 |
| 当前实现 | `time_estimate_years`（钳制 0.1–20）；多子任务取 **max**；前置失败/不可执行时实质推进钳 **≤2**；用于人口增长与 `year` 推进 |
| 未做 | 被动时间事件随跨度触发（依赖被动事件系统） |

### 3.5 模糊输入 `is_too_vague` 反问

| | |
| --- | --- |
| 设计意图 | 空洞口号（「发展」「变强」）不结算，史官反问具体化。 |
| 当前实现 | LLM 输出 `is_too_vague` + `clarification_prompt`；`resolve_full_turn`：无可结算子任务则 `settlement_skipped=True` |
| 仍 TODO | **HTTP/WS/前端**未定义「待澄清」态；`parse_intent`  docstring 残留过时 TODO（实现已进 resolver） |
| 交接建议 | Phase 4 按 `api_contract.md` 返回 `vague_prompts`，勿再进数学引擎 |

### 3.6 知识注入 — 仅判定

| | |
| --- | --- |
| 设计意图（GDD §5） | `is_knowledge_injection` 为真时走独立评估管线（可执行度、社会吸收等）。 |
| 当前实现 | Intent 侧完整判定 `knowledge_detail_level` 四档；**全回合仍走常规 friction/capacity**；`evaluate_knowledge_injection` 未实现 |
| Phase 4+ | 在 `resolve_full_turn` 或 action 编排中分支；在接评估前勿假装已支持「传授火药就变工业」 |

### 3.7 向量检索推迟

| | |
| --- | --- |
| 设计意图 | landmark 语义检索。 |
| 当前实现 | `landmarks.embedding` / `embedding_model` 列；`embed_text()` → `None`；`query_landmarks_vector` → `NotImplementedError`；检索 = **tags 数组重叠 + turn/importance** |
| 策略抽象 | `retriever.LandmarkSearchFn` / `keyword_landmark_strategy` 可热替换 |

### 3.8 宗教系统 — 仅数据结构

| | |
| --- | --- |
| 设计意图（GDD） | 覆盖、国教关系、组织化、知识载体、经济力参与摩擦与事件。 |
| 当前实现 | `Religion` 模型 + 模板填充；landmark 可检测宗教变动；`religious_resistance` 参数位存在但全回合默认 **0.0** |
| 未做 | 改教、镇压、宗教战争、神权合法性联动的完整规则 |

### 3.9 被动事件系统 — 未做

| | |
| --- | --- |
| 设计意图 | 按时间跨度触发天灾、疫病、边境冲突、继承等。 |
| 当前实现 | `check_passive_events` → `[]`；**未**在 `resolve_full_turn` 调用 |
| 接入点 | 数值汇总之后、叙事之前（或之后写入 events 再叙事）— 见 GDD §10.5 |

### 3.10 记忆系统（Phase 3，相对 GDD §7 的落地）

| 层 | 设计意图 | 实现 |
| --- | --- | --- |
| 近期 | 最近回合原文脉 | `recent.py`：最近 5 回合格式化 |
| 中期 | 每 5 回合压缩 | `summary.py`：V4 Flash + thinking；`summaries` 表字段对齐 |
| 长期 | 关键转折索引 | `landmark.py`：制度/科技/领土/合法性/稳定极端/宗教 |
| 检索 | 叙事前组装 | `retriever.py`：近期 + 2–3 摘要 + 3–5 landmark + **accumulations 段** |
| 叙事 | 体现历史因果 | `narrator` 提示词已写；`--memory` 手测验证过跨回合提及 |

### 3.11 叙事风格（相对早期半文半白）

| | |
| --- | --- |
| 当前决策 | **现代白话 + 少量古意**；禁止堆砌半文半白；开篇用统一 `year_label`（公元前/公元） |
| 文件 | `backend/llm/narrator.py` |

### 3.12 农业标定

| | |
| --- | --- |
| 决策 | 引入全局 `YIELD_FACTOR`（西周盈余 1.2 反推）+ 每模板 `agricultural_modifier`（苏美尔/希腊等校准开局盈余，不改领土） |
| GDD | 原文肥力公式未含 modifier；以 `food.py` 为准 |

### 3.13 API / 前端（GDD §10–11）

| | |
| --- | --- |
| 设计意图 | REST + WS 流式叙事；古典卷轴 UI |
| 当前实现 | 后端逻辑在 CLI；`frontend` 为 Next 骨架；契约见 `HANDOFF/api_contract.md` |

---

## 四、核心循环（实现版）

```
玩家输入
  → TaskSplitter
  → IntentParser（scale / vague / knowledge 标志）
  → [全模糊? → 返回反问，停]
  → Capacity（dilution）+ Friction（P_success）+ 掷骰
  → 数值汇总写回 CivState（含积累衰减）
  → retrieve_history_context（关键词 landmark + 积累）
  → Narrator（同步 CLI / 流式 Web）
  → commit_turn_memory（turn / landmark / 每5回合摘要）
  → check_game_over（极简）
```

与 GDD §10.5 差异：被动事件与知识注入支路尚未插入；记忆检索在实现上由**编排层**调用而非写死在 resolver 内。

---

## 五、开局模板（✅）

| `template_id` | 文明 | `agricultural_modifier` |
| --- | --- | --- |
| `sumer` | 苏美尔城邦联盟 | ≈1.212（校准） |
| `egypt` | 早王朝埃及 | 1.0（默认） |
| `harappa` | 哈拉帕联盟 | 1.0 |
| `babylon` | 古巴比伦王国 | 1.0 |
| `zhou` | 西周王朝 | 1.0（`YIELD_FACTOR` 锚点） |
| `greece` | 古希腊城邦 | ≈1.455（校准） |

手测默认：`zhou`。

---

## 六、数据与持久化

| 项 | 状态 |
| --- | --- |
| 表结构 games/game_states/turns/summaries/landmarks/accumulations | ✅ SQL |
| landmarks.embedding / embedding_model / importance_score | ✅ |
| 迁移运行器 `python -m backend.db.migrations.migrate` | ✅ 脚本有 |
| 应用内读写 | ⬜；Phase 3 用 `MemoryStore` |
| 独立 saves 表 | ⬜（存档 API 设计时补） |

---

## 七、测试与验收锚点

| 套件 | 内容 |
| --- | --- |
| `uv run pytest` | 引擎 + memory 等（无真实 LLM） |
| `--fullturn` | 真实 LLM 全链路 |
| `--memory` | 摘要压缩输出、landmark、retriever、带因果叙事 |
| `--intent` / `--narrator` | 分组件手测 |

---

## 八、Phase 4 范围建议（非绑定）

1. 按 `api_contract.md` 挂齐 REST + WS  
2. 按 `wiring_todo.md` 编排 `resolve_full_turn` + memory + gameover  
3. 前端：状态面板 + 叙事卷轴 + 输入栏（GDD §11 视觉方向）  
4. 存档最小可用  
5. **不要**在 Phase 4 同时深挖知识注入/被动事件/宗教计算（除非排期明确）— 留给后续并保持接口点位

---

## 九、原文索引

详细公式、阶级张力设计、知识注入三维、Game Over 完整条件、UI 配色等：**直接读** [`civsim-v2-gdd.md`](../civsim-v2-gdd.md)。若原文与本文「当前实现」冲突，**以代码与本文第三节为准**，并在实现中回头改 GDD 或改代码（二选一写进 commit）。
