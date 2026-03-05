# 文明灵 (CivSim)

> **多智能体协作的文明演化模拟器**

一款深度策略模拟游戏，通过多智能体协作 (MAS) 与硬核数学模型，科学模拟文明演化过程中的阻力、技术溢出和社会变迁。

![版本](https://img.shields.io/badge/版本 -0.1.0-blue)
![语言](https://img.shields.io/badge/语言-Rust%20%2B%20TypeScript-orange)
![框架](https://img.shields.io/badge/框架-Tauri%20v2-green)
![AI](https://img.shields.io/badge/AI-DashScope%20LLM-purple)

---

## 🎯 核心特性

| 特性 | 说明 |
|------|------|
| **多智能体协作** | 4 类 Agent 协同工作：意图拆解 → 阻力审计 → 动力学推演 → 叙事史官 |
| **AI 驱动叙事** | 基于 Qwen3.5-Plus 和 DeepSeek-V3.2 的自然语言处理 |
| **硬核数学模型** | 社会摩擦模型、治理效率衰减模型、马尔萨斯承载力模型 |
| **双轨记忆系统** | 短期快照 (JSON) + 长期历史索引 (关键词检索) |
| **双语支持** | 中文/英文实时切换 |
| **沉浸式 UI** | 复古未来主义控制台风格 |
| **Markdown 渲染** | 游戏日志支持完整的 Markdown 格式 |

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri Desktop App                    │
├─────────────────────────────────────────────────────────┤
│  Frontend (Svelte + TypeScript + Tailwind CSS)         │
│  ├── 复古 UI 组件                                       │
│  ├── Markdown 渲染 (svelte-markdown)                   │
│  └── 实时状态更新 (Svelte stores + Tauri IPC)          │
├─────────────────────────────────────────────────────────┤
│  Tauri Core (Rust)                                     │
│  ├── LLM 调用 (DashScope API via async-openai)         │
│  ├── 数学模型 (statrs + ndarray)                       │
│  ├── SQLite 存储                                       │
│  └── 异步运行时 (tokio)                                │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

**后端 (Rust)**
- `tauri` v2 - 桌面应用框架
- `async-openai` - LLM API 调用 (DashScope 兼容模式)
- `tokio` - 异步运行时
- `rusqlite` - SQLite 数据库
- `serde` / `serde_json` - JSON 序列化

**前端 (Svelte + TypeScript)**
- `svelte` - UI 框架
- `tailwindcss` - 样式
- `svelte-markdown` - Markdown 渲染
- `@tauri-apps/api` v2 - Tauri IPC

**AI 模型 (DashScope)**
- `qwen3.5-plus` - 意图拆解与叙事生成
- `deepseek-v3.2` - 深度推理与阻力审计

---

## 🚀 快速开始

### 环境要求

| 工具 | 版本 |
|------|------|
| Rust | 1.70+ |
| Node.js | 18+ |
| 包管理器 | cargo + npm |

### 1. 克隆项目

```bash
git clone <repository-url>
cd civsim
```

### 2. 配置 API 密钥

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 DashScope API 密钥
# 获取地址：https://dashscope.console.aliyun.com/
DASHSCOPE_API_KEY=sk-your-actual-api-key-here
```

### 3. 安装依赖

```bash
# 安装 Tauri CLI (如果未安装)
cargo install --force cargo-tauri

# 安装 Rust 依赖
cargo install

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 4. 启动开发服务器

```bash
# 开发模式 (支持热重载)
cargo tauri dev
```

应用会自动打开窗口，前端开发服务器运行在 `http://localhost:5173`

### 5. 构建生产版本

```bash
# 构建安装包
cargo tauri build
```

构建产物位于 `target/release/bundle/`

---

## 🎮 游戏指南

### 开始新游戏

1. 启动应用后，点击 **"新游戏"**
2. 选择时代（部落纪元 → 古典时代 → 中世纪 → 近代）
3. 选择地点（5 个文明发源地）
4. 确认文明信息，开始游戏

### 预置文明模板

当前支持 6 个史实文明模板：

| 地点 | 文明 | 时代 |
|------|------|------|
| **印度河流域** | 哈拉帕联盟 | 部落纪元 |
| **美索不达米亚** | 苏美尔城邦 | 古典时代 |
| **黄河流域** | 华夏部落 | 部落纪元 |
| **尼罗河流域** | 古埃及 | 古典时代 |
| **爱琴海地区** | 希腊城邦 | 古典时代 |
| **中美洲** | 奥尔梅克 | 部落纪元 |

### 游戏交互

1. **输入指令** - 在底部输入框输入自然语言指令
   - 示例："精进农具制造"、"推行共和制"、"发展贸易"
2. **AI 处理** - 系统调用 LLM 分析指令并生成叙事
3. **查看结果** - 叙事以 Markdown 格式显示，数值自动更新
4. **继续游戏** - 继续输入指令或加载存档

### 加载存档

1. 点击主界面的 **"加载游戏"**
2. 选择之前的存档
3. 点击 **"加载"** 继续游戏

---

## 📁 项目结构

```
文明灵/
├── .env.example              # 环境变量模板
├── Cargo.toml                # Rust 依赖配置
├── tauri.conf.json           # Tauri v2 配置
├── src/
│   ├── main.rs               # 应用入口
│   ├── commands.rs           # Tauri 命令处理
│   ├── agents/               # 4 个 Agent 实现
│   │   ├── deconstructor.rs  # 意图拆解
│   │   ├── auditor.rs        # 阻力审计
│   │   ├── simulator.rs      # 动力学推演
│   │   └── chronicler.rs     # 叙事史官
│   ├── math/                 # 数学模型
│   ├── storage/              # SQLite 存储
│   ├── templates/            # 文明模板
│   └── llm/                  # LLM 客户端 (DashScope)
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.svelte        # 主应用组件
│       ├── lib/
│       │   ├── components/   # UI 组件
│       │   ├── stores/       # Svelte stores
│       │   └── tauri/        # Tauri API 封装
│       └── app.css           # 全局样式
└── data/                     # 运行时数据 (自动生成)
    └── civsim.db             # SQLite 数据库
```

---

## 🤖 Agent 架构

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
  UI 显示剧情日志 (Markdown)
```

| Agent | 模型 | 职责 |
|-------|------|------|
| **Deconstructor** | Qwen3.5-Plus | 解析玩家指令，转化为四维影响矩阵 |
| **Auditor** | DeepSeek-V3.2 | 对比文明认知等级，计算成功率 |
| **Simulator** | Qwen3.5-Plus | 基于数学模型计算数值变动 |
| **Chronicler** | Qwen3.5-Plus | 将数值变动转化为文学叙事 |

---

## 📐 核心数学模型

### 1. 社会摩擦模型 (成功率计算)

```
P_success = B × (1 - (ΔC × R) / A)
```

| 参数 | 含义 | 范围 |
|------|------|------|
| B | 基础成功率 | 默认 0.8 |
| ΔC | 认知代差 | 0-5 |
| R | 社会惯性系数 | 0.0-1.0 |
| A | 元首统治力 | 0-100 |

### 2. 治理效率衰减模型

```
E = C × e^(-D/V)
```

| 参数 | 含义 |
|------|------|
| E | 治理效率 |
| C | 中央集权度 |
| D | 领土距离 |
| V | 交通/通讯技术等级 |

### 3. 马尔萨斯承载力模型

当实际人口 > 承载力上限时，强制触发"动乱"、"饥荒"或"瘟疫"事件。

---

## 🔧 开发规范

### 代码格式化

```bash
# Rust
cargo fmt
cargo clippy --all-targets --all-features -- -D warnings

# TypeScript/Svelte
cd frontend
npm run lint
npm run format
```

### 测试

```bash
# Rust 单元测试
cargo test

# 前端测试
cd frontend
npm test
```

---

## ⚠️ 常见问题

### 数据库错误 "no such table: saves"

确保应用正常启动，数据库会在首次运行时自动初始化。如果仍然报错，删除 `data/civsim.db` 后重启应用。

### API 调用失败

1. 检查 `.env` 文件是否存在且包含有效的 `DASHSCOPE_API_KEY`
2. 确保网络连接正常
3. 检查 DashScope API 额度是否充足
4. 查看控制台日志，确认模型名称正确 (`qwen3.5-plus`, `deepseek-v3.2`)

### LLM 响应慢

- 首次调用可能需要 10-30 秒（模型冷启动）
- 复杂指令处理时间更长
- 控制台会显示 "AI 思考中..." 提示

### 前端端口冲突

如果 5173 端口被占用，修改 `frontend/vite.config.js` 中的 `server.port` 配置。

---

## 📄 许可证

MIT License

---

## 📞 联系方式

- **项目主页**: [GitHub Repository]
- **问题反馈**: [Issues]
- **DashScope 文档**: https://help.aliyun.com/zh/dashscope/

---

**版本**: v0.1.0 | **最后更新**: 2026-03-01 | **状态**: ✅ 可玩
