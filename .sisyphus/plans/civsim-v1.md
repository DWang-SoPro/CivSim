# 文明灵 (CivSim) - 开发计划

## 进度总览

### ✅ Wave 1: 项目基础 (Task 1-4) - 100%
- [x] Task 1: Tauri 项目骨架
- [x] Task 2: JSON Schema 规范定义
- [x] Task 3: 网络层基础（LLM 客户端）
- [x] Task 4: 存储层基础（SQLite schema）

### ✅ Wave 2: 核心 Agent (Task 5-8) - 100%
- [x] Task 5: Deconstructor Agent（意图拆解）
- [x] Task 6: Auditor Agent（阻力审计）
- [x] Task 7: Simulator Agent + 数学模型
- [x] Task 8: Chronicler Agent（叙事史官）

### ✅ Wave 3: 流水线与 UI (Task 9-12) - 100%
- [x] Task 9: Agent 流水线编排
- [x] Task 10: 前端 UI 框架
- [x] Task 11: 状态管理（Svelte stores）
- [x] Task 12: 存档/加载功能

### 🔄 Wave 4: 集成与完善 (Task 13-16) - 0%
- [ ] Task 13: UI 与后端集成 ⬅️ **当前任务**
- [ ] Task 14: 错误处理完善
- [ ] Task 15: 性能优化
- [ ] Task 16: 文档与打包

## Task 13: UI 与后端集成

### 目标
将前端 UI 与 Rust 后端连接，实现完整的用户交互流程。

### 子任务

#### 13.1 Tauri Commands 实现
- [ ] `process_player_input` - 处理玩家指令
- [ ] `get_current_state` - 获取当前游戏状态
- [ ] `save_game` - 保存游戏
- [ ] `load_game` - 加载游戏
- [ ] `list_saves` - 列出存档

#### 13.2 前端集成
- [ ] 连接 Tauri API 调用
- [ ] 实现状态同步
- [ ] 添加加载动画
- [ ] 错误提示 UI

#### 13.3 数据流验证
- [ ] 玩家输入 → 后端处理 → 前端显示
- [ ] 状态变更 → 后端更新 → 前端刷新
- [ ] 存档/读档 → 后端 IO → 前端反馈

### 技术实现

**后端 (Rust)**:
```rust
#[tauri::command]
async fn process_player_input(
    input: String,
    state: State<'_, GameState>,
) -> Result<TurnResult, String> {
    // 调用 Agent 流水线
    // 更新游戏状态
    // 返回叙事结果
}
```

**前端 (Svelte)**:
```typescript
import { invoke } from '@tauri-apps/api/tauri';

async function handleSubmit(command: string) {
  const result = await invoke('process_player_input', { input: command });
  // 更新 UI
}
```

### 验收标准
- [ ] 玩家输入指令后能看到 AI 生成的叙事
- [ ] 游戏状态正确更新并显示
- [ ] 存档/读档功能正常工作
- [ ] 错误有友好提示

