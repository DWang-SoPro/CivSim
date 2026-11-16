# 文明灵 CivSim v2

自然语言驱动的古代文明演化模拟器。

**万相单机版**可以从 OmniPhase 首页打开，在本机下令、结算和续玩。默认离线，模型可选。构建、启动和存档说明见[万相桌面版开发指南](omniphase-tools/README.md)。

玩家以**王朝 / 统治集团**视角下达政令；LLM 负责定性判断与史官叙事，数学引擎负责一切定量结算。核心约束：**不是意志决定社会存在，而是社会存在决定意志**——物质基底、生产关系与制度能力层层收紧政策空间。

| 项 | 内容 |
| --- | --- |
| 版本 | 0.1.0（第二阶段：LLM 管线 + 回合串联） |
| 后端 | Python 3.11+ · FastAPI · Pydantic v2 · uv |
| 前端 | Next.js 15 · React 19 · TypeScript · Tailwind（骨架） |
| LLM | DeepSeek V4 Flash（OpenAI 兼容接口） |
| 数据 | PostgreSQL（schema 已预留，存档 API 后续接入） |
| 设计文档 | [`civsim-v2-gdd.md`](./civsim-v2-gdd.md) |

---

## 设计原则

1. **防梦**：可行性由结构条件硬约束，不靠叙事开挂。
2. **分工**：LLM 不做数值；数学引擎不写故事。
3. **路径依赖**：积累值与近期历史影响后续潜力。
4. **层层约束**：物质 → 生产 → 上层建筑 → 政策空间。
5. **渐进演化**：连续变量，无硬性「时代切换」。

---

## 核心循环

```
玩家输入自然语言政令
        │
        ▼
TaskSplitter  →  子任务列表
        │
        ▼
IntentParser  →  结构化意图（域 / 规模 / 认知代差 / 前置条件 …）
        │
        ▼
Capacity 三层国力  →  dilution_factor（作用于数值，不作用于成功率）
        │
        ▼
Friction 成功率 → 掷骰 → 档位 → 数值汇总 → clamp
        │
        ▼
Narrator（流式白话史官叙事）
```

完整回合入口：`backend.engine.action_resolver.resolve_full_turn`。

---

## 仓库结构

```
.
├── civsim-v2-gdd.md          # 游戏设计文档（规范源）
├── pyproject.toml / uv.lock  # Python 依赖
├── backend/
│   ├── main.py               # FastAPI 入口（health + game/action/WS）
│   ├── config.py             # 环境配置
│   ├── models/schemas.py     # CivState 与枚举
│   ├── templates/            # 六个开局文明模板
│   ├── engine/               # 纯函数数学引擎
│   │   ├── friction.py       # 社会摩擦 / 成功率 / 档位
│   │   ├── capacity.py       # 国力池 · 传导 · 稀释（CapacityParams）
│   │   ├── food / population / stability / authority / …
│   │   └── action_resolver.py  # 假行动结算 + 全链路回合
│   ├── llm/                  # DeepSeek 管线
│   │   ├── client.py         # call_json / call_text_stream
│   │   ├── task_splitter.py
│   │   ├── intent_parser.py
│   │   ├── narrator.py
│   │   └── _manual_test.py   # 真实 API 手测脚手架
│   ├── memory/               # 记忆系统（占位）
│   ├── api/                  # HTTP / WS 路由（占位）
│   └── db/                   # PostgreSQL 迁移占位
├── tests/                    # pytest（不调用真实 LLM）
└── frontend/                 # Next.js 最小可玩页面
```

---

## 环境要求

- Python **≥ 3.11**
- [uv](https://github.com/astral-sh/uv)
- Node.js **≥ 18**（仅前端）
- DeepSeek API Key（跑 LLM 手测 / 完整回合时需要）

---

## 快速开始

### 1. 后端依赖

```bash
cd /path/to/CivSim
uv sync
```

### 2. 环境变量

```bash
cp .env.example .env
# 编辑 .env，填入：
# DEEPSEEK_API_KEY=sk-...
```

可选：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | （空） | DeepSeek API 密钥 |
| `LLM_BASE_URL` | `https://api.deepseek.com` | API Base URL |
| `LLM_MODEL` | `deepseek-v4-flash` | 模型名 |
| `LLM_MAX_RETRIES` | `3` | JSON / API 重试次数 |
| `DATABASE_URL` | `postgresql://localhost/civsim` | 后续阶段使用 |

**切勿将 `.env` 提交到版本库。**

### 3. 单元测试（无网络、无 LLM）

```bash
uv run pytest
```

### 4. 启动 API

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

已挂载 `/health`、`POST /api/game/new`、`POST /api/game/{id}/action`
与 `WS /api/game/{id}/ws`。

### 5. LLM 手测脚手架

```bash
# 意图管线（TaskSplitter → IntentParser）
uv run python -m backend.llm._manual_test

# 叙事生成
uv run python -m backend.llm._manual_test --narrator

# 端到端完整回合（西周模板，固定随机种子 42）
uv run python -m backend.llm._manual_test --fullturn

# 过滤用例（子串匹配标签）
uv run python -m backend.llm._manual_test --fullturn 三大规模
```

### 6. 前端（最小可玩页）

```bash
cd frontend
pnpm install
pnpm dev
```

打开 `http://localhost:3000`，默认以西周模板新建游戏。新局会先生成一段
基于完整模板状态的第 0 回合史官开场；政令结算后，状态面板会用箭头、
差值和颜色标出本回合变化，叙事正文仍保持文学化表达。

---

## 数学引擎要点

| 模块 | 职责 |
| --- | --- |
| `friction` | \(P_\text{success}\) · 结果档位 · 效果倍率 |
| `capacity` | 国力池 × 权力传导 → 可调动量；超支则非线性稀释，带 `DILUTION_FLOOR` |
| `food` | 粮食盈余率（含 `agricultural_modifier`、标定 `YIELD_FACTOR`） |
| `governance` | 边疆治理效率衰减 |
| `stability` / `authority` / `population` / `accumulation` | 各维回合结算 |

国力联调参数集中在 `backend.engine.capacity.CapacityParams`（`BASE_CAPACITY`、`SCALE_COST`、`DILUTION_EXPONENT`、`DILUTION_FLOOR` 等）。

**约定**：`dilution_factor` 只缩放数值效果，不改变成功率掷骰。

---

## 开局文明模板

`sumer` · `egypt` · `harappa` · `babylon` · `zhou` · `greece`

加载：`load_civ_state("zhou")`（见 `backend.templates.civilizations`）。手测默认西周。

---

## 当前进度

| 阶段 | 状态 |
| --- | --- |
| Phase 1：骨架 · CivState · 数学引擎 · 六模板 | 完成 |
| Phase 2：LLM 客户端 · 拆分 · 意图 · 叙事 · capacity · 全链路回合 | 完成 |
| Phase 3：三层记忆（近期 / 中期摘要 / 长期 landmark）+ 关键词检索注入叙事 | 已完成 |
| Phase 4：最小 FastAPI + WebSocket + Next.js 可玩闭环 | 已完成 |
| Phase 4+：知识注入完整评估 · 前端卷轴 UI · PostgreSQL 存档接通 | 待做 |

---

## 开发约定

- 引擎模块保持**纯函数**、可单测、固定种子可复现。
- LLM 输出一律经 **Pydantic** 校验；校验失败触发客户端重试。
- 意图 / 叙事提示词使用中文；叙事目标为「现代白话 + 少量古意」，禁止半文半白堆砌。
- 改动粮食 / 国力标定后，更新 `tests/` 中对应锚点测试。

---

## 许可

项目文档与代码默认仅供本仓库协作者使用；对外分发条款待定。
