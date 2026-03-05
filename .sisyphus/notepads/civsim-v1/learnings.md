# CivSim 学习笔记

## Task 1: Tauri 项目骨架

### 遇到的问题

1. **npm create tauri-app 失败**
   - 原因：目录不为空
   - 解决：手动创建项目结构

2. **Svelte 构建错误："Identifier '.default' has already been declared"**
   - 根本原因：svelte.config.js 重复的 `export default config;`
   - 附加问题：缺少必要的 import 语句
   - 解决方案：
     ```javascript
     import adapter from '@sveltejs/adapter-auto';
     import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
     
     const config = { ... };
     
     export default config;  // 只保留一个
     ```

3. **SvelteKit 与原生 Svelte 结构冲突**
   - 问题：同时存在 `+page.svelte`（SvelteKit）和 `main.ts + app.svelte`（原生 Svelte）
   - 解决：选择 SvelteKit 架构，删除原生 Svelte 文件

4. **tsconfig.json 路径别名配置不完整**
   - 修复：添加 `$lib` 和 `$lib/*` 两个别名
   ```json
   "paths": {
     "$lib": ["./src/lib"],
     "$lib/*": ["./src/lib/*"]
   }
   ```

5. **缺失依赖**
   - `svelte-markdown` 未安装但被导入
   - 安装：`npm install svelte-markdown`

### 成功构建的关键

1. 修复 svelte.config.js 的重复导出
2. 添加必要的 import 语句
3. 统一使用 SvelteKit 架构
4. 正确配置 tsconfig.json 路径别名
5. 安装所有必要的依赖

### 最终构建输出

```
✓ built in 3.49s
Run npm run preview to preview your production build locally.
✔ done
```

### 教训

- Svelte 组件导入/导出必须一致
- 不要混用 SvelteKit 和原生 Svelte
- 仔细检查配置文件的重复语句
- 确保所有导入的依赖都已安装
