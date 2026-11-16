# 在万相中运行文明灵单机版

玩家从万相首页进入「文明灵」，选择一个古代文明，在底部输入框下达政令。默认玩法使用本机规则解释与数学引擎，SQLite 自动存档。**无需多人服务器、云端数据库或模型密钥。** 游戏进程由桌面宿主在本机按需启动。联网仅在首次取得构建依赖，或显式使用远程模型等相应功能时需要。

## 两个源码仓的分工

| 仓库 | 内容 |
| --- | --- |
| CivSim | [Vue 应用与资源](../omniphase-app)、[本机游戏服务](../backend/singleplayer)、原有数值引擎、启动和验证脚本。网页客户端继续位于 `frontend/`。 |
| [万相 OmniAgent](https://github.com/SoProStars/omniagent) | Electron 宿主、Go 平台服务、应用安装与摘要校验、统一输入框和按项目隔离的游戏调用。 |

### 从安装到一次政令

1. 启动器为游戏源码目录建立万相项目，从平台读取应用预览摘要，随后以摘要登记 `civsim`。Electron 只把本机游戏接口交给这个已登记版本。源码、历史版本预览和其他应用各自使用独立视图。
2. 玩家从万相首页打开应用。Vue 页面通过 `window.wanxiang.gameRequest` 读取可选文明和已有对局，并通过 `publishContext` 将当前对局 ID 告诉宿主。页面端的游戏操作共有 `catalog`、`list`、`new`、`get`、`turn` 五种。
3. 玩家在万相底部输入框下令。宿主把文本连同当前对局 ID 发给活动页面，页面提交政令、预期回合和请求编号。Electron 按项目启动 Python 回合引擎，通过仅本机可达的临时端口和进程专用令牌转交请求。
4. 引擎在一笔 SQLite 事务中保存新回合、国势、纪事和请求回执。重复请求可读回原结果。页面收到回复后更新朝堂与国史；输入「问史官」会直接查阅已有回合。默认流程中的数值、掷骰和国史纪要均在本机产生。

当前可运行版本由两个源码仓共同构建。游戏前端、规则与资源可以在 CivSim 仓独立维护。万相仓维护应用包的安装校验、左栏和输入框材质，桌面更新后文明灵会使用同一套交互。

以下是源码开发版的 macOS 命令，要求两个仓库都包含本次单机接入改动。先准备 Python 3.11 及以上版本和 uv，以及万相源码对应的 Go、Node 和 pnpm 工具链（本次 macOS 环境使用 Python 3.12、Go 1.24、Node 22 和 pnpm 9）。首次构建需下载各自的依赖。

## 构建

从 **CivSim 仓库根目录**执行。将第二个路径替换为本机带有文明灵桥接代码的万相源码检出目录。

```sh
CIVSIM_REPO="$PWD"
OMNIPHASE_REPO="/path/to/OmniAgent"

uv sync --frozen --no-install-project
pnpm --dir "$CIVSIM_REPO/omniphase-app" install --frozen-lockfile
pnpm --dir "$CIVSIM_REPO/omniphase-app" run build

(
  cd "$OMNIPHASE_REPO" &&
  mkdir -p bin/dev &&
  go build -o bin/dev/omniagent-server ./cmd/omniagent-server &&
  pnpm --dir gui install --frozen-lockfile &&
  pnpm --dir gui run electron:build
)
```

第一组产生 CivSim 的 `.venv` 和应用包 `omniphase-app/dist/`。第二组产生万相的 `bin/dev/omniagent-server` 和 `gui/out/`。只改 CivSim 界面时可以单独构建游戏包。发布新的包内容时同步递增清单及应用包版本，避免与已经登记的同版本内容冲突。

## 启动与续玩

```sh
node omniphase-tools/desktop.mjs "$OMNIPHASE_REPO"
```

启动器在专用的本机平台资料目录预览并登记应用包，然后打开万相。从首页点击「文明灵」，选择西周等六种文明之一开局。可以点「兴修水利」等建议、修改后颁令，也可直接从万相底部输入框提交。说「问史官：粮食有什么变化？」会查询已结算的记录，回合数保持不变。本地模式无法识别的政令会提示澄清，继续编辑即可。

启动器的默认资料目录为 `~/.civsim-omniphase`，其中 `desktop/` 和 `platform/` 分别保存专用桌面资料和应用安装登记；`campaigns/` 保存按运行项目隔离的 SQLite 对局。也可显式指定同一资料目录来持续游玩：

```sh
node omniphase-tools/desktop.mjs "$OMNIPHASE_REPO" "$HOME/.civsim-omniphase"
```

每次打开会按当前作用域读取最近打开的存档，点击「文明与存档」可切换对局。完整退出万相会结束本机服务。更换资料目录或运行项目会得到单独的对局列表。

## 模型可选

默认不配置 `CIVSIM_MODEL_MODE`。本地模式支持收录的政令、常用同义表达和组合行动，史官根据真实结算生成纪要。「问史官」是查阅游戏已有国史的本地功能。

若需要模型解释更自由的政令和执笔回合叙事，在启动器所在进程中显式设置 `CIVSIM_MODEL_MODE=enabled`、`CIVSIM_MODEL_URL` 和 `CIVSIM_MODEL_NAME`。远程 OpenAI 兼容端点仅使用 HTTPS，并通过 `CIVSIM_MODEL_API_KEY` 注入该服务的密钥。本机回环模型端点允许 HTTP。启用后，政令、必要国势与近期历史可能发往所选模型服务，数值与掷骰仍在本机结算。网页前端无需取得密钥。关闭模型模式后重新启动即可恢复规则模式。

## 验证

[macOS 实机验收与截图](../docs/verification/omniphase-singleplayer-macos/README.md)记录了完整窗口下令、国史透过玻璃、悬停左栏应用图标关闭，以及关闭或退出后如何续玩。

```sh
uv run --frozen --no-sync python -m pytest tests
node omniphase-tools/check-desktop.mjs "$OMNIPHASE_REPO"
```

桌面验证使用临时资料和存档；可在末尾追加截图目录，例如 `./local-evidence`。它覆盖安装、选西周、经万相底栏颁令、切换应用、重启后读回同一回合与继续下令。macOS 上已验证 Vue 独立构建、游戏本机服务和界面的真实数值结算、澄清与只读问史。真实 Electron 窗口也已通过上述两回合流程，第一次下令后切走并重启，能读回同一段史文，第二次下令会进入下一回合。正式账号与付费模型并非默认验收条件。
