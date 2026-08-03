# CivSim v2 — 运行说明（交接）

面向 Phase 4 及后续开发：如何装依赖、配环境、跑测试、启动最小 Web 闭环与手测。

---

## 1. 技术栈版本

| 层 | 版本 / 选型 |
| --- | --- |
| Python | **≥ 3.11**（`pyproject.toml`） |
| 包管理 | [uv](https://github.com/astral-sh/uv) |
| Web | FastAPI ≥0.115 · Uvicorn |
| 校验 | Pydantic v2 |
| LLM SDK | `openai`（DeepSeek OpenAI 兼容） |
| DB 驱动 | `asyncpg`（schema 有，业务读写未接） |
| 前端 | Next.js **15.1.0** · React **19** · TypeScript · Tailwind 3.4 |
| 模型 | DeepSeek **V4 Flash**（`deepseek-v4-flash`） |
| 游戏版本号 | `0.1.0` |

---

## 2. 目录结构总览

```
.
├── civsim-v2-gdd.md          # 原始设计文档（长篇）
├── README.md                 # 仓库简要说明
├── HANDOFF/                  # ← 本交接包（Phase 4 从这里读）
├── pyproject.toml / uv.lock
├── .env.example
├── backend/
│   ├── main.py               # FastAPI：health + game/action/WS 路由
│   ├── config.py
│   ├── models/schemas.py     # CivState
│   ├── templates/            # 六文明 + actions 占位
│   ├── engine/               # 数学引擎 + resolve_full_turn + orchestrator
│   ├── llm/                  # DeepSeek 管线 + _manual_test.py
│   ├── memory/               # 三层记忆 + MemoryStore
│   ├── api/                  # 进程内会话 + HTTP/WS 接线层
│   └── db/                   # migrations + pool 占位
├── tests/                    # pytest（不调真实 LLM）
└── frontend/                 # Next.js 最小可玩页面
```

**完整回合入口（逻辑）：** `backend.engine.action_resolver.resolve_full_turn`  
**完整回合入口（编排）：** `backend.engine.orchestrator.run_game_turn`
**记忆提交入口：** `backend.memory.pipeline.commit_turn_memory`  
**检索入口：** `backend.memory.retriever.retrieve_history_context`

---

## 3. 安装依赖

### 后端

```bash
cd /path/to/CivSim
uv sync
```

### 前端（Phase 4 UI）

```bash
cd frontend
pnpm install
```

### PostgreSQL（可选，Phase 4 存档前可先不装）

本地起一个空库，URL 与 `.env` 中 `DATABASE_URL` 一致即可。

---

## 4. 环境变量

```bash
cp .env.example .env
# 编辑：
# DEEPSEEK_API_KEY=sk-...
```

| 变量 | 默认 | 必需？ |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 空 | 跑任何真实 LLM 手测时必需 |
| `LLM_BASE_URL` | `https://api.deepseek.com` | 否 |
| `LLM_MODEL` | `deepseek-v4-flash` | 否 |
| `LLM_MAX_RETRIES` | `3` | 否 |
| `DATABASE_URL` | `postgresql://localhost/civsim` | 跑迁移时需要 |

**勿提交 `.env`。** 兼容旧名 `LLM_API_KEY`（见 `config.py`）。

---

## 5. 初始化数据库

```bash
# 需本机 PostgreSQL 已创建数据库 civsim（或改 URL）
DATABASE_URL=postgresql://localhost/civsim uv run python -m backend.db.migrations.migrate
```

会按文件名顺序应用：

1. `001_initial.sql` — 六表  
2. `002_landmarks_embedding.sql` — embedding 列（若 001 已含则 IF NOT EXISTS 跳过）

应用层目前**不会**在回合中写库；记忆默认 `MemoryStore` 内存。

---

## 6. 测试

```bash
uv run pytest
```

- 不访问网络、不调 DeepSeek  
- 覆盖 friction / capacity / food / memory / templates 等  

---

## 7. 启动最小 Web 闭环

终端 1（仓库根目录）：

```bash
uv run uvicorn backend.main:app --reload --port 8000
# GET http://localhost:8000/health → {"status":"ok"}
# Swagger: http://localhost:8000/docs
```

终端 2：

```bash
cd frontend
pnpm dev
```

打开 `http://localhost:3000`：新建游戏默认使用西周模板。执行政令后，
WebSocket 按 `narrative_start → narrative_delta* → narrative_end → state_update`
推送；数值更新后立即可下达下一道政令。`POST /api/game/new` 会先调用
V4 Flash（thinking 关闭），根据完整初始 `CivState` 返回
`opening_narrative`，前端将其显示为第 0 回合背景。`state_update` 中的
`dimension_changes` 仅在状态面板显示箭头、差值与颜色，不写入叙事正文。

---

## 8. `_manual_test.py` 各模式

需已配置 `DEEPSEEK_API_KEY`。

```bash
# 默认：意图管线（TaskSplitter → IntentParser）用例
uv run python -m backend.llm._manual_test

# 仅意图
uv run python -m backend.llm._manual_test --intent

# 叙事流式样例
uv run python -m backend.llm._manual_test --narrator

# 意图 + 叙事
uv run python -m backend.llm._manual_test --all

# 端到端完整回合（西周，固定 seed 42）
uv run python -m backend.llm._manual_test --fullturn

# 过滤 fullturn / intent 用例标签（子串）
uv run python -m backend.llm._manual_test --fullturn 三大规模

# Phase 3 记忆系统演示（摘要打印 + landmark + 带因果叙事）
uv run python -m backend.llm._manual_test --memory
```

---

## 9. 已知 TODO / 技术债

| 项 | 说明 |
| --- | --- |
| DB 无 Repository | 有 SQL 与 `asyncpg` 池占位，无读写封装 |
| 会话/记忆仅内存 | 必须单 worker 运行；多进程不共享，重启丢历史 |
| 知识注入 | 仅意图打标；`knowledge_evaluator` 未实现；管线无分支 |
| 被动事件 | 占位空列表，未接入 resolver |
| Game Over | 仅 `population <= 0` |
| 行动菜单 | `generate_action_menu` → `[]` |
| 宗教深度 | 有结构，无计算闭环 |
| 向量检索 | 接口预留，未实现 |
| 过时注释 | `intent_parser.parse_intent` 仍写 vague 管线 TODO — **resolver 已接线** |
| `resolve_full_turn` 默认同步叙事 | Web 已由 `run_game_turn` 传 `generate_narrative=False` 并改走 `narrate_stream` |
| retriever 在 resolver 外 | 已由 `run_game_turn` 显式编排（见 `wiring_todo.md`） |
| README 进度表 | 根 `README.md` 已标 Phase 3 完成；细节以 HANDOFF 为准 |
| 前端 | 只有最小可玩页；卷轴 UI、菜单、存读档等仍未做 |

---

## 10. 交接阅读顺序（推荐）

1. `HANDOFF/GDD_updated.md` — 完成度与设计变更  
2. `HANDOFF/wiring_todo.md` — 如何把 CLI 回合变成 API  
3. `HANDOFF/api_contract.md` + `openapi.json` — 前后端契约  
4. `HANDOFF/tunable_params.md` — 日后平衡  
5. 代码：`action_resolver.resolve_full_turn` → `memory/pipeline.py` → `llm/narrator.py`  
6. 需要公式细节时回看 `civsim-v2-gdd.md`

---

## 11. 常用代码锚点

| 用途 | 符号 |
| --- | --- |
| 全回合 | `backend.engine.action_resolver.resolve_full_turn` |
| 完整编排 | `backend.engine.orchestrator.run_game_turn` |
| 国力 | `backend.engine.capacity.CapacityParams` |
| 意图 schema | `backend.llm.intent_parser.IntentResult` |
| 叙事输入 | `backend.llm.narrator.NarrationInput` |
| 流式 | `narrate_stream` / `LLMClient.call_text_stream` |
| 记忆检索 | `retrieve_history_context` |
| 模板加载 | `load_civ_state("zhou")` |
