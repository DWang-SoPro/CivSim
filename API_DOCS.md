# 文明灵 (CivSim) - API 文档

## 后端 API (Tauri Commands)

### `process_player_input`

处理玩家指令并返回结果。

**签名**:
```rust
#[tauri::command]
pub async fn process_player_input(
    input: String,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<TurnResultDto, String>
```

**参数**:
- `input`: 玩家输入的自然语言指令

**返回**:
```typescript
{
  narrative: string;      // AI 生成的叙事文本
  summary: string;        // 简短摘要
  new_state: CivState;    // 更新后的游戏状态
}
```

**错误**:
- `VALIDATION_ERROR`: 输入为空或超长
- `API_ERROR`: LLM API 调用失败
- `UNKNOWN`: 其他错误

---

### `get_current_state`

获取当前游戏状态。

**签名**:
```rust
#[tauri::command]
pub async fn get_current_state(
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<CivState, String>
```

**返回**:
```typescript
{
  year: number;              // 当前年份
  civ_name: string;          // 文明名称
  population: number;        // 人口
  stability: number;         // 稳定性 (0-100)
  authority: number;         // 统治力 (0-100)
  centralization: number;    // 中央集权 (0-100)
  territory_size: number;    // 领土面积
  tech_level: number;        // 科技水平
  biome_fertility: number;   // 生态肥力
}
```

---

### `save_game`

保存当前游戏。

**签名**:
```rust
#[tauri::command]
pub async fn save_game(
    name: String,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<i64, String>
```

**参数**:
- `name`: 存档名称

**返回**:
- `i64`: 存档 ID

**错误**:
- `VALIDATION_ERROR`: 名称为空或超长
- `DATABASE_ERROR`: 数据库操作失败

---

### `load_game`

加载指定存档。

**签名**:
```rust
#[tauri::command]
pub async fn load_game(
    id: i64,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<CivState, String>
```

**参数**:
- `id`: 存档 ID

**返回**:
- `CivState`: 加载的游戏状态

**错误**:
- `NOT_FOUND`: 存档不存在
- `PARSE_ERROR`: 存档数据损坏

---

### `list_saves`

列出所有存档。

**签名**:
```rust
#[tauri::command]
pub async fn list_saves(
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<Vec<SaveMetadata>, String>
```

**返回**:
```typescript
Array<{
  id: number;
  name: string;
  created_at: string;
}>
```

---

## 前端 API (TypeScript)

### `processPlayerInput`

**位置**: `frontend/src/lib/tauri/api.ts`

```typescript
export async function processPlayerInput(input: string): Promise<TurnResult>
```

**功能**:
- 输入验证 (非空，长度≤1000)
- 调用后端 API
- 自动重试 (最多 2 次)
- 错误处理

**示例**:
```typescript
try {
  const result = await processPlayerInput("修建粮仓");
  console.log(result.narrative);
} catch (error) {
  console.error(error.message);
}
```

---

### `getCurrentState` / `getCurrentStateCached`

```typescript
export async function getCurrentState(): Promise<CivState>
export async function getCurrentStateCached(): Promise<CivState>
```

**区别**:
- `getCurrentState`: 总是从后端获取
- `getCurrentStateCached`: 优先从缓存获取 (TTL: 1 分钟)

---

### `saveGame`

```typescript
export async function saveGame(name: string): Promise<number>
```

**示例**:
```typescript
const id = await saveGame("我的存档");
```

---

### `loadGame`

```typescript
export async function loadGame(id: number): Promise<CivState>
```

**示例**:
```typescript
const state = await loadGame(1);
civState.set(state);
```

---

### `listSaves` / `listSavesCached`

```typescript
export async function listSaves(): Promise<SaveMetadata[]>
export async function listSavesCached(): Promise<SaveMetadata[]>
```

**区别**:
- `listSaves`: 总是从后端获取
- `listSavesCached`: 优先从缓存获取 (TTL: 2 分钟)

---

## 状态管理

### CivState Store

**位置**: `frontend/src/lib/stores/civState.ts`

```typescript
import { civState } from '$lib/stores/civState';

// 订阅状态
$: currentState = $civState;

// 更新状态
civState.update(state => ({
  ...state,
  stability: state.stability + 10,
}));

// 批量更新
updateState({
  stability: 90,
  authority: 85,
});
```

---

### Toast Store

**位置**: `frontend/src/lib/stores/toast.ts`

```typescript
import { toast } from '$lib/stores/toast';

// 成功提示
toast.success("指令已执行");

// 错误提示
toast.error("处理失败：网络错误", 5000);

// 警告提示
toast.warning("稳定性较低");

// 信息提示
toast.info("游戏已保存");
```

---

### 日志 Store

**位置**: `frontend/src/lib/stores/gameLog.ts`

```typescript
import { gameLog, log } from '$lib/stores/gameLog';

// 添加日志
log("**COMMAND**: 修建粮仓");

// 订阅日志
$: entries = $gameLog;
```

---

## 缓存系统

### 后端缓存

**位置**: `src/agents/cache.rs`

```rust
use crate::agents::ResultCache;

let cache = ResultCache::new(300); // 5 分钟 TTL

// 获取或设置缓存
let result = cache
    .get_or_set_deconstructor(&key, || async {
        deconstructor.process(input, state).await
    })
    .await?;
```

---

### 前端缓存

**位置**: `frontend/src/lib/stores/cache.ts`

```typescript
import { cache } from '$lib/stores/cache';

// 设置缓存
cache.set('key', value, 300); // 5 分钟 TTL

// 获取缓存
const value = cache.get('key');

// 使缓存失效
cache.invalidate('key');

// 清空缓存
cache.clear();
```

---

## 错误处理

### APIError 类

**位置**: `frontend/src/lib/tauri/api.ts`

```typescript
export class APIError extends Error {
  constructor(
    message: string,
    public code: string = 'UNKNOWN',
    public retryable: boolean = false
  ) {}
}
```

**错误码**:
- `VALIDATION_ERROR`: 输入验证失败
- `API_ERROR`: API 调用失败
- `NETWORK_ERROR`: 网络错误
- `UNKNOWN`: 未知错误

**重试逻辑**:
```typescript
// 自动重试可恢复的错误
const isRetryable = 
  errorMsg.includes('network') ||
  errorMsg.includes('timeout') ||
  errorMsg.includes('connection');

if (isRetryable && retries < MAX_RETRIES) {
  // 重试
}
```

---

## 数学模型 API

### `calculate_success_rate`

**位置**: `src/math/models.rs`

```rust
pub fn calculate_success_rate(
    cognitive_gap: i32,
    resistance: f64,
    authority: i32,
) -> f64
```

**公式**: `P = B × (1 - (ΔC × R) / A)`

---

### `governance_efficiency`

```rust
pub fn governance_efficiency(
    centralization: f64,
    territory: f64,
    tech_level: f64,
) -> f64
```

**公式**: `E = C × e^(-D/V)`

---

### `malthus_limit`

```rust
pub fn malthus_limit(
    tech_level: f64,
    biome_fertility: f64,
) -> f64
```

**用途**: 计算人口承载力上限

---

## 国际化 (i18n)

**位置**: `frontend/src/lib/stores/i18n.js`

```typescript
import { currentLang, t, toggleLanguage } from '$lib/stores/i18n';

// 获取当前语言
$: lang = $currentLang;

// 翻译文本
const text = t('sidebar.metrics');

// 切换语言
toggleLanguage();
```

**翻译字典**:
- `zh`: 中文
- `en`: English

---

## 测试 API

### Rust 测试

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_success_rate() {
        let rate = calculate_success_rate(2, 0.5, 50);
        assert!((0.0..=1.0).contains(&rate));
    }
}
```

运行测试:
```bash
cargo test
```

---

### TypeScript 测试

```typescript
import { processPlayerInput } from '$lib/tauri/api';

describe('API', () => {
  it('should reject empty input', async () => {
    await expect(processPlayerInput(''))
      .rejects
      .toThrow('VALIDATION_ERROR');
  });
});
```

运行测试:
```bash
cd frontend && npm test
```

---

**最后更新**: 2026-02-28  
**版本**: v0.1.0
