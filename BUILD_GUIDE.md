# 文明灵 (CivSim) 应用打包指南

本文档介绍如何将文明灵打包为桌面应用程序。

## 前置要求

### 通用要求
- **Rust**: 1.70+ (`rustc --version`)
- **Node.js**: 18+ (`node --version`)
- **Tauri CLI**: `cargo install tauri-cli`

### Windows 特定要求
- **Visual Studio 2022** 或 **Build Tools for Visual Studio 2022**
  - 安装"使用 C++ 的桌面开发"工作负载
  - 或至少安装：MSVC v143 - VS 2022 C++ x64/x86 生成工具
- **WebView2 Runtime**: Windows 10/11 通常已预装

### macOS 特定要求
- **Xcode**: 最新版本 (`xcode-select --install`)
- **Apple Developer Account** (可选，用于签名和公证)

## 环境准备

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/civsim.git
cd civsim
```

### 2. 安装 Rust 依赖

```bash
cd src
cargo build
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# DashScope API Key (必需)
DASHSCOPE_API_KEY=your-api-key-here

# 可选：模型配置
QWEN_PLUS_MODEL=qwen3.5-plus
QWEN_MAX_MODEL=qwen3-max-2026-01-23
```

## 开发模式运行

```bash
# 在项目根目录
cargo tauri dev
```

这将启动开发服务器，前端会热重载。

## 打包发布

### Windows 打包

#### 方法一：使用 Tauri CLI

```bash
# 在项目根目录
cargo tauri build
```

输出位置：`src/target/release/bundle/msi/*.msi`

#### 方法二：使用 PowerShell 脚本

创建 `build-windows.ps1`:

```powershell
# build-windows.ps1
Write-Host "Building CivSim for Windows..." -ForegroundColor Green

# 检查依赖
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Write-Error "Rust/Cargo not found. Please install from https://rustup.rs/"
    exit 1
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js not found. Please install from https://nodejs.org/"
    exit 1
}

# 安装前端依赖
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
cd frontend
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install frontend dependencies"
    exit 1
}
cd ..

# 构建应用
Write-Host "Building Tauri application..." -ForegroundColor Yellow
cargo tauri build

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host "Installer location: src\target\release\bundle\msi\" -ForegroundColor Cyan
} else {
    Write-Error "Build failed"
    exit 1
}
```

运行：
```powershell
.\build-windows.ps1
```

### macOS 打包

#### 方法一：使用 Tauri CLI

```bash
# 在项目根目录
cargo tauri build
```

输出位置：
- DMG: `src/target/release/bundle/dmg/*.dmg`
- APP: `src/target/release/bundle/macos/*.app`

#### 方法二：使用 Shell 脚本

创建 `build-macos.sh`:

```bash
#!/bin/bash

set -e

echo -e "\033[32mBuilding CivSim for macOS...\033[0m"

# 检查依赖
if ! command -v cargo &> /dev/null; then
    echo -e "\033[31mError: Rust/Cargo not found. Please install from https://rustup.rs/\033[0m"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "\033[31mError: Node.js not found. Please install from https://nodejs.org/\033[0m"
    exit 1
fi

# 安装前端依赖
echo -e "\033[33mInstalling frontend dependencies...\033[0m"
cd frontend
npm install
if [ $? -ne 0 ]; then
    echo -e "\033[31mError: Failed to install frontend dependencies\033[0m"
    exit 1
fi
cd ..

# 构建应用
echo -e "\033[33mBuilding Tauri application...\033[0m"
cargo tauri build

if [ $? -eq 0 ]; then
    echo -e "\033[32mBuild successful!\033[0m"
    echo -e "\033[36mDMG location: src/target/release/bundle/dmg/\033[0m"
    echo -e "\033[36mAPP location: src/target/release/bundle/macos/\033[0m"
else
    echo -e "\033[31mError: Build failed\033[0m"
    exit 1
fi
```

运行：
```bash
chmod +x build-macos.sh
./build-macos.sh
```

## 高级配置

### Windows MSI 安装程序配置

编辑 `src/tauri.conf.json`:

```json
{
  "bundle": {
    "windows": {
      "msi": {
        "license": "../LICENSE",
        "installMode": "both",
        "upgradeCode": "your-uuid-here"
      }
    }
  }
}
```

### macOS 签名和公证

#### 1. 配置签名

编辑 `src/tauri.conf.json`:

```json
{
  "bundle": {
    "macOS": {
      "signingIdentity": "Developer ID Application: Your Name (TEAM_ID)",
      "entitlements": "../entitlements.plist"
    }
  }
}
```

#### 2. 创建 entitlements.plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
</dict>
</plist>
```

#### 3. 公证配置

在构建后使用 `notarytool` 进行公证：

```bash
# 创建 zip 文件用于公证
ditto -c -k --keepParent "src/target/release/bundle/macos/CivSim.app" "CivSim.zip"

# 提交公证
xcrun notarytool submit "CivSim.zip" \
  --apple-id "your-email@example.com" \
  --team-id "YOUR_TEAM_ID" \
  --password "app-specific-password" \
  --wait

# 装订公证结果
xcrun stapler staple "src/target/release/bundle/macos/CivSim.app"
```

## 发布检查清单

### 发布前检查

- [ ] 版本号在 `Cargo.toml` 中已更新
- [ ] 版本号在 `tauri.conf.json` 中已更新
- [ ] `CHANGELOG.md` 已更新
- [ ] 所有功能测试通过
- [ ] API Key 已从代码中移除（使用环境变量）

### Windows 检查

- [ ] MSI 安装程序可以正常安装
- [ ] 应用程序可以正常启动
- [ ] 卸载程序工作正常
- [ ] 在 Windows 10/11 上测试

### macOS 检查

- [ ] DMG 可以正常挂载
- [ ] 应用程序可以拖到 Applications 文件夹
- [ ] 应用程序可以正常启动（可能需要右键打开）
- [ ] 签名有效（`codesign -dv --verbose=4 CivSim.app`）
- [ ] 在 Intel 和 Apple Silicon Mac 上测试

## 故障排除

### Windows 常见问题

#### 错误："linker link.exe not found"

**解决方案**: 安装 Visual Studio Build Tools

```powershell
# 使用 winget
winget install Microsoft.VisualStudio.2022.BuildTools --override "--wait --add Microsoft.VisualStudio.Workload.VCTools"
```

#### 错误："WebView2 not found"

**解决方案**: 下载并安装 WebView2 Runtime
https://developer.microsoft.com/en-us/microsoft-edge/webview2/

### macOS 常见问题

#### 错误："xcrun: error: invalid active developer path"

**解决方案**: 安装 Xcode 命令行工具

```bash
xcode-select --install
```

#### 错误："failed to bundle" (签名问题)

**解决方案**: 暂时禁用签名用于测试

编辑 `src/tauri.conf.json`:

```json
{
  "bundle": {
    "macOS": {
      "signingIdentity": null
    }
  }
}
```

### 通用问题

#### 前端构建失败

```bash
# 清理并重新安装
cd frontend
rm -rf node_modules package-lock.json
npm install
```

#### Rust 依赖问题

```bash
# 清理并重新构建
cargo clean
cargo build
```

## 自动化 CI/CD

### GitHub Actions 配置

创建 `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Rust
        uses: dtolnay/rust-action@stable
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      
      - name: Build
        run: cargo tauri build
        env:
          DASHSCOPE_API_KEY: ${{ secrets.DASHSCOPE_API_KEY }}
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: windows-installer
          path: src/target/release/bundle/msi/*.msi

  release-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Rust
        uses: dtolnay/rust-action@stable
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      
      - name: Build
        run: cargo tauri build
        env:
          DASHSCOPE_API_KEY: ${{ secrets.DASHSCOPE_API_KEY }}
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: macos-dmg
          path: src/target/release/bundle/dmg/*.dmg
```

## 版本号管理

项目使用语义化版本号 (SemVer)：

- **主版本号**: 重大更新，不兼容的 API 变更
- **次版本号**: 新功能，向后兼容
- **修订号**: 问题修复，向后兼容

更新版本号时需要修改：
1. `Cargo.toml` - `[package]` 部分的 `version`
2. `src/tauri.conf.json` - `version` 字段
3. `frontend/package.json` - `version` 字段

## 联系支持

如有打包问题，请：
1. 查看 [Tauri 官方文档](https://tauri.app/v1/guides/)
2. 提交 Issue 到项目仓库
3. 联系开发团队

---

**注意**: 首次打包可能需要较长时间（10-30分钟），因为需要下载和编译所有依赖。后续打包会使用缓存，速度会快很多。
