# 文明灵 (CivSim) 绿色便携版构建指南

## 🚀 快速开始

### 方法1: 使用自动打包脚本（推荐）

1. **确保前置条件满足**:
   - 已安装 Rust + Cargo
   - 已安装 Node.js + pnpm (或 npm/yarn)
   - 已构建前端或使用自动构建
   - 已安装 Rust + Cargo
   - 已安装 Node.js + npm
   - 已构建前端: `cd frontend && npm run build`

2. **运行打包脚本**:
   ```bash
   # Windows CMD/Batch
   build-portable.bat
   
   # 或者使用 PowerShell
   .\build-portable.ps1
   ```

3. **获取输出**:
   - 输出目录: `CivSim-便携版/`
   - 将文件夹复制到任意位置即可使用

---

### 方法2: 手动构建

#### 步骤1: 构建前端
```bash
cd frontend

# 如果你用 pnpm
pnpm install
pnpm run build

# 如果你用 npm
npm install
npm run build

cd ..
```
```bash
cd frontend
npm run build
cd ..
```

#### 步骤2: 构建 Rust 后端
```bash
cargo build --release
```

#### 步骤3: 创建便携版目录
```bash
mkdir CivSim-便携版
mkdir CivSim-便携版\data
```

#### 步骤4: 复制必要文件
```bash
# 主程序
copy target\release\CivSim.exe CivSim-便携版\

# 所有 DLL 依赖
copy target\release\*.dll CivSim-便携版\
```

#### 步骤5: 配置 API 密钥
在 `CivSim-便携版/` 文件夹中创建 `.env` 文件:
```
DASHSCOPE_API_KEY=sk-your-api-key-here
```

---

## 📦 最终目录结构

```
CivSim-便携版/
├── CivSim.exe              # 主程序
├── WebView2Loader.dll      # WebView2 运行时
├── D3DCompiler_47.dll      # 图形渲染 (可能有)
├── libEGL.dll              # OpenGL (可能有)
├── libGLESv2.dll           # OpenGL (可能有)
├── msvcp140.dll            # MSVC 运行时 (可能有)
├── vcruntime140.dll        # MSVC 运行时 (可能有)
├── vcruntime140_1.dll      # MSVC 运行时 (可能有)
├── .env                    # API 密钥配置文件
├── 启动游戏.bat            # 中文启动器
├── 使用说明.txt            # 使用说明文档
└── data/                   # 游戏存档目录
    └── civsim.db           # SQLite 数据库
```

---

## 🎯 使用方法

### 首次使用

1. **复制文件夹**到任意位置（桌面、D盘、U盘均可）

2. **配置 API 密钥**:
   - 在 `CivSim-便携版/` 文件夹中创建 `.env` 文件
   - 添加: `DASHSCOPE_API_KEY=你的密钥`
   - 获取密钥: https://dashscope.console.aliyun.com/

3. **启动游戏**:
   - 双击 `启动游戏.bat` 或 `CivSim.exe`

### 日常使用

- **启动**: 双击 `启动游戏.bat`
- **存档**: 自动保存在 `data/` 文件夹
- **迁移**: 复制整个 `CivSim-便携版` 文件夹到新电脑，存档跟着走

---

## 💾 便携特性

✅ **无需安装** - 解压即用  
✅ **不写注册表** - 系统纯净  
✅ **无残留文件** - 删除即卸载  
✅ **U盘运行** - 随身携带  
✅ **存档同步** - 数据在 data/ 文件夹中  

---

## 🔧 故障排除

### 问题1: 提示缺少 DLL
**解决**: 安装 [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### 问题2: 提示缺少 WebView2
**解决**: 安装 [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)

### 问题3: 无法连接 AI
**解决**: 检查 `.env` 文件中的 API 密钥是否正确

---

## 📋 系统要求

- **操作系统**: Windows 10/11 (64位)
- **运行时**: WebView2 (通常已预装)
- **网络**: 需要联网调用 DashScope API
- **存储**: 约 50MB 空间

---

## 🎮 游戏操作

1. 启动后选择「新游戏」
2. 选择时代和地点
3. 在底部输入框输入指令（如：发展农业、建造宫殿）
4. 等待 AI 生成叙事
5. 查看历史日志和文明数据变化

---

## 📞 技术支持

- 项目文档: AGENTS.md
- API 文档: https://help.aliyun.com/zh/dashscope/
- 问题反馈: GitHub Issues

---

**版本**: v0.1.0  
**最后更新**: 2026-03-06  
**状态**: ✅ 可玩
