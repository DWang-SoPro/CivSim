# 文明灵 (CivSim)

> **多智能体协作的文明演化模拟器**

一款深度策略模拟游戏，通过多智能体协作 (MAS) 与硬核数学模型，科学模拟文明演化过程中的阻力、技术溢出和社会变迁。

---

## 🎯 核心特性

| 特性 | 说明 |
|------|------|
| **多智能体协作** | 4 类 Agent 协同工作：意图拆解 → 阻力审计 → 动力学推演 → 叙事史官 |
| **硬核数学模型** | 社会摩擦模型、治理效率衰减模型、马尔萨斯承载力模型 |
| **双轨记忆系统** | 短期快照 (JSON) + 长期历史索引 (关键词检索) |
| **异步解耦** | 所有 AI 请求放入后台任务，界面渲染与逻辑演算互不干扰 |

---

## 🏗️ 技术架构  

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri Desktop App                    │
├─────────────────────────────────────────────────────────┤
│  Frontend (Svelte + TypeScript + Tailwind CSS)         │
│  ├── 复古 UI 组件                                       │
│  ├── Markdown 渲染 (svelte-markdown)                   │
│  ├── 图表 (Chart.js wrapper)                           │
│  └── 实时状态更新 (Svelte stores + Tauri IPC)          │
├─────────────────────────────────────────────────────────┤
│  Tauri Core (Rust)                                     │
│  ├── LLM 调用 (async-openai + DashScope API)           │
│  ├── 数学模型 (statrs + ndarray)                       │
│  ├── 状态管理 (serde JSON)                             │
│  ├── 本地存储 (SQLite via rusqlite)                    │
│  └── 异步运行时 (tokio)                                │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

**后端 (Rust)**
| 库 | 用途 |
|-----|------|
| `async-openai` | LLM API 调用 (DashScope) |
| `statrs` | 统计计算 |
| `ndarray` | 数值计算 |
| `rusqlite` | SQLite 数据库 |
| `serde` / `serde_json` | JSON 序列化 |
| `tokio` | 异步运行时 |
| `schemars` | JSON Schema 验证 |

**前端 (Svelte + TypeScript)**
| 库 | 用途 |
|-----|------|
| `svelte` | UI 框架 |
| `tailwindcss` | 样式 |
| `svelte-markdown` | Markdown 渲染 |
| `chart.js` | 图表 |
| `@tauri-apps/api` | Tauri IPC |

---

## 🤖 Agent 架构

### 流水线

```
玩家输入自然语言
       │
       ▼
┌──────────────────┐
│   Deconstructor  │ ── 四维影响矩阵 ──▶
└──────────────────┘                      │
       │                                  ▼
       │                         ┌──────────────┐
       │                         │   Auditor    │ ── 审计结果 ──▶
       │                         └──────────────┘
       │                                  │
       ▼                                  ▼
┌──────────────────┐              ┌──────────────┐
│   Chronicler     │ ◀── 数值变动 ──│  Simulator   │
└──────────────────┘              └──────────────┘
       │
       ▼
  UI 显示剧情日志
```

### Agent 职责

| Agent | 模型 | 职责 | 输出 |
|-------|------|------|------|
| **Deconstructor** | Qwen Plus | 解析玩家指令，转化为四维影响矩阵 | `{admin, economy, culture, military}` |
| **Auditor** | DeepSeek V3.2 | 对比指令与文明认知等级，计算成功率 | `{cognitive_gap, resistance, success_rate}` |
| **Simulator** | DeepSeek R1 | 基于数学模型计算 5 年内数值变动 | `{population_change, stability_change, events}` |
| **Chronicler** | Qwen Max | 将数值变动转化为文学叙事 | Markdown 格式剧情日志 |

---

## 📐 核心数学模型

### 1. 社会摩擦模型 (成功率计算)

$$P_{success} = B \times (1 - \frac{\Delta C \cdot R}{A})$$

| 参数 | 含义 | 范围 |
|------|------|------|
| $B$ | 基础成功率 | 默认 0.8 |
| $\Delta C$ | 认知代差 | 0-5 |
| $R$ | 社会惯性系数 | 0.0-1.0 |
| $A$ | 元首统治力 | 0-100 |

### 2. 治理效率衰减模型

$$E = C \times e^{-\frac{D}{V}}$$

| 参数 | 含义 |
|------|------|
| $E$ | 治理效率 |
| $C$ | 中央集权度 |
| $D$ | 领土距离 |
| $V$ | 交通/通讯技术等级 |

### 3. 马尔萨斯承载力模型

$$P_{limit} = f(Tech, Bio)$$

| 参数 | 含义 |
|------|------|
| $P_{limit}$ | 人口承载力上限 |
| $Tech$ | 科技水平 |
| $Bio$ | 生态肥力 |

当 $P_{actual} > P_{limit}$ 时，强制触发"动乱"、"饥荒"或"瘟疫"事件。

---

## 📁 目录结构

```
文明灵/
├── .sisyphus/                    # 开发计划与证据
│   ├── plans/
│   │   └── civsim-v1.md         # 主开发计划
│   └── evidence/                 # QA 证据
├── src/
│   ├── tauri.conf.json          # Tauri 配置
│   ├── Cargo.toml               # Rust 依赖
│   ├── src/
│   │   ├── main.rs              # 入口
│   │   ├── llm/
│   │   │   └── client.rs        # LLM 客户端封装
│   │   ├── agents/
│   │   │   ├── mod.rs
│   │   │   ├── deconstructor.rs
│   │   │   ├── auditor.rs
│   │   │   ├── simulator.rs
│   │   │   └── chronicler.rs
│   │   ├── math/
│   │   │   └── models.rs        # 数学模型实现
│   │   ├── storage/
│   │   │   └── mod.rs           # SQLite 存储
│   │   ├── schemas/
│   │   │   └── mod.rs           # JSON Schema 定义
│   │   └── pipeline/
│   │       └── mod.rs           # Agent 流水线编排
│   └── frontend/
│       ├── src/
│       │   ├── app.svelte
│       │   ├── lib/
│       │   │   ├── components/
│       │   │   │   ├── Header.svelte
│       │   │   │   ├── Sidebar.svelte
│       │   │   │   ├── Main.svelte
│       │   │   │   └── Footer.svelte
│       │   │   ├── stores/
│       │   │   │   └── civState.ts
│       │   │   └── utils/
│       │   └── app.css
│       ├── package.json
│       └── vite.config.js
├── tests/                        # 集成测试
├── .gitignore
├── README.md
└── AGENTS.md                    # 本文件
```

---

## 🛠️ 开发规范

### 代码风格

**Rust**
```rust
// 使用 rustfmt 格式化
cargo fmt

// 严格 lint
cargo clippy --all-targets --all-features -- -D warnings
```

**TypeScript/Svelte**
```typescript
// 使用 ESLint + Prettier
npm run lint
npm run format
```

### 测试策略

**TDD 流程**: RED → GREEN → REFACTOR

```rust
// 1. 先写测试 (RED)
#[test]
fn test_governance_efficiency() {
    let efficiency = governance_efficiency(50.0, 1000.0);
    assert_eq!(efficiency, 18.39); // e^(-1000/1000) * 50
}

// 2. 实现最小功能 (GREEN)
pub fn governance_efficiency(centralization: f64, territory: f64) -> f64 {
    centralization * (-territory / 1000.0).exp()
}

// 3. 重构 (REFACTOR)
```

### 提交规范

```bash
# Wave 1 完成
git commit -m "feat: add project scaffolding and base infrastructure"

# Wave 2 完成
git commit -m "feat: implement 4-agent pipeline with math models"

# Wave 3 完成
git commit -m "feat: add UI and storage system"

# Wave 4 完成
git commit -m "feat: integration, error handling, and build"
```

---

## 🚀 快速开始

### 环境要求

| 工具 | 版本 |
|------|------|
| Rust | 1.70+ |
| Node.js | 18+ |
| Tauri CLI | 1.5+ |

### 安装依赖

```bash
# 后端
cargo install --force cargo-tauri
cargo install

# 前端
cd frontend
npm install
```

### 开发模式

```bash
# 启动开发服务器
cargo tauri dev
```

### 构建发布

```bash
# 构建安装包
cargo tauri build
```

---

## 📋 状态 Schema

每一回合的状态以结构化 JSON 维护，作为所有 Agent 的全局上下文。

```json
{
  "civilization": {
    "basics": {
      "year": -2000,
      "location": "Indus Valley",
      "population": 50000,
      "territory_size": 1200
    },
    "polity": {
      "name": "Harappan League",
      "structure": "Theocratic Confederacy",
      "centralization": 35,
      "stability": 82
    },
    "tech_tree": {
      "level": "Bronze Age",
      "cognitive_unlocks": ["Basic Geometry", "Irrigation Consciousness"]
    }
  },
  "geopolitics": {
    "trade_surplus": 150,
    "border_threats": "Low"
  }
}
```

---

## 📞 LLM 模型配置

本项目全部使用**中国国产大模型 API**（DashScope 平台）。

| Agent | 模型 | 说明 |
|-------|------|------|
| **意图拆解 (Deconstructor)** | Qwen Plus | 擅长指令理解与结构化输出 |
| **阻力审计 (Auditor)** | DeepSeek V3.2 (Chat) | 逻辑推理与风险评估 |
| **动力学推演 (Simulator)** | DeepSeek R1 | 阿里云深度推理模型，擅长数学与逻辑推演 |
| **叙事史官 (Chronicler)** | Qwen Max | 顶级叙事能力，文学表达最优 |

### API 配置

```rust
// DashScope API endpoint
let config = OpenAIConfig::new()
    .with_api_base("https://dashscope.aliyuncs.com/compatible-mode/v1")
    .with_api_key("your-api-key");
```

---

## 🔒 核心约束

### 逻辑护栏 (Logic Guardrail)

在 AI 给出最终剧情前，系统通过 Rust 脚本进行"硬校验"。

**示例**: 若 AI 判定人口增加了 200%，但脚本计算其粮食产量无法支撑，系统将强制干预逻辑，并让叙事 Agent 改写为：

> "由于粮食不足，虽然行政指令下达了，但发生了大规模饥荒"

### Must NOT Have

- ❌ 向量数据库 RAG（改用简单 JSON 索引）
- ❌ 复杂的 UI 动画/过渡效果
- ❌ 多层抽象（Agent → 直接实现，不要 Factory/Manager）
- ❌ 热重载配置系统
- ❌ 分布式追踪日志
- ❌ 离线运行模式

---

## 📖 参考资料

- [Tauri 官方文档](https://tauri.app/v1/guides/)
- [async-openai](https://docs.rs/async-openai/)
- [DashScope API 文档](https://help.aliyun.com/zh/dashscope/)
- [statrs](https://docs.rs/statrs/)
- [Svelte 教程](https://svelte.dev/tutorial)

---

## 📄 许可证

MIT License

---

## 🔧 技术偏好

### Tauri 版本
- **使用 Tauri v2** (非 v1)
- 配置文件：`tauri.conf.json` (v2 格式)
- Rust crate: `tauri = "2.0"`
- NPM package: `@tauri-apps/api = "^2.0.0"`
- Build: `tauri-build = "2.0"`

### 配置说明
- tauri.conf.json 使用 v2 schema
- `build.frontendDist` 替代 `build.distDir`
- `build.devUrl` 替代 `build.devPath`
- `app` 配置项替代 `tauri` 配置项

---

## ✅ Tauri v2 配置验证

根据 Tauri 官方文档和示例，当前配置已按 v2 标准编写：

### 正确的 v2 配置

**tauri.conf.json**:
```json
{
  "$schema": "https://schema.tauri.app/config",
  "productName": "CivSim",
  "version": "0.1.0",
  "identifier": "com.civsim.app",
  "build": {
    "frontendDist": "../frontend/dist",  // v2: 不是 distDir
    "devUrl": "http://localhost:5173"    // v2: 不是 devPath
  },
  "app": {                               // v2: 不是 tauri
    "withGlobalTauri": true,
    "windows": [...],
    "security": {...}
  },
  "bundle": {...}
}
```

**Cargo.toml**:
```toml
[dependencies]
tauri = { version = "2.0", features = ["api-all"] }

[build-dependencies]
tauri-build = { version = "2.0", features = [] }
```

**package.json**:
```json
{
  "dependencies": {
    "@tauri-apps/api": "^2.0.0"
  }
}
```

### v1 vs v2 关键区别

| 配置项 | Tauri v1 | Tauri v2 |
|--------|----------|----------|
| Schema | `tauri.conf.json` v1 | `tauri.conf.json` v2 |
| 前端目录 | `build.distDir` | `build.frontendDist` |
| 开发路径 | `build.devPath` | `build.devUrl` |
| 应用配置 | `tauri` | `app` |
| Rust crate | `tauri = "1.x"` | `tauri = "2.0"` |
| NPM package | `@tauri-apps/api@^1.x` | `@tauri-apps/api@^2.0` |


### v1 vs v2 关键区别

| 配置项 | Tauri v1 | Tauri v2 |
|--------|----------|----------|
| Schema | `tauri.conf.json` v1 | `tauri.conf.json` v2 |
| 前端目录 | `build.distDir` | `build.frontendDist` |
| 开发路径 | `build.devPath` | `build.devUrl` |
| 应用配置 | `tauri` | `app` |
| Rust crate | `tauri = "1.x"` | `tauri = "2.0"` |
| NPM package | `@tauri-apps/api@^1.x` | `@tauri-apps/api@^2.0` |

---

## 📖 参考资料

### Tauri v2 官方文档
- [Tauri 官方文档](https://tauri.app/v1/guides/) — 官方指南与 API 参考
- [Tauri v2 配置参考](https://tauri.app/reference/config/) — 配置文件完整说明
- [Tauri v2 Rust API](https://docs.rs/tauri/2.0.0/tauri/) — Rust 后端 API 文档
- [Tauri v2 JavaScript API](https://tauri.app/v1/api/) — 前端 API 参考
- [Tauri GitHub](https://github.com/tauri-apps/tauri) — 开源仓库与问题反馈