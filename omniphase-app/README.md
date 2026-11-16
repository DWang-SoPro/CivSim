# 文明灵 · 万相客户端

这是 CivSim 仓库内的独立 Vue 3 客户端。应用清单为 `wanxiang-app.json`，编译产物放在 `dist/`。首页可选择六种开局文明，按项目的本地运行配置加载已授权的对局服务。政令和存档通过宿主桥处理，页面无需访问网络或读取本地文件。

## 开发和预览

在本目录运行 `pnpm install --frozen-lockfile` 和 `pnpm build`，需 Node 22 与 pnpm 9。也可借用万相的 `gui/scripts/build-wanxiang-vue.mjs` 对本目录显式构建。更换构建器可能生成不同包摘要，本机安装应登记本次实际构建的产物。在普通浏览器预览时可查看开局文明与地图；真实对局需要在已配置本机游戏服务的万相内打开。

初次进入选择文明开局。再次打开会读取本机最近打开的存档；通过“文明与存档”可开新局或打开别局。进入游戏后可直接在万相底部下令，或者选用朝堂里的建议政令。遇到未知政令会保留草案并提示澄清。用“问史官：最近粮食怎样变化？”查看已结算记录，不推进回合。

游戏页的国家、政策与经济数值来自同一份服务端结算。开局示意图采用 Natural Earth 1:110m 公有领域海岸与陆地轮廓，按近似发源地标记文明；并不表示历史疆界。数据来源为 [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/) 的 [ne_110m_land](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson)。应用图标中的鼎形沿用 CivSim 原仓西周纹章的视觉语言。全部地图资源和界面字体可离线使用，页面字体使用设备上的系统字体。
