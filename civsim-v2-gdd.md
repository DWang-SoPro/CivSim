# 文明灵 CivSim v2 — 游戏设计文档

> **版本**: 0.1 草案  
> **日期**: 2026-08-02  
> **定位**: 自然语言驱动的古代文明演化模拟器  
> **核心理念**: 不是人的意志决定社会存在，而是社会存在决定人的意志。物质基础约束一切上层行动。

---

## 一、设计总纲

### 1.1 一句话描述

玩家以王朝统治集团的视角，用自然语言下达政令，在物质基础、生产关系和上层建筑的层层约束下推动文明演化。LLM 负责定性判断和文学叙事，数学引擎负责一切定量计算。

### 1.2 核心设计原则

**防梦原则。** 不是玩家想干什么就能干什么，而是文明的结构条件决定了此刻能干什么。行动可行性由物质基底、生产关系和制度能力硬约束，LLM 不碰数值，数学引擎不编故事。

**路径依赖。** 文明的当前状态不足以预测行动结果——"你是怎么走到这里的"同样重要。十轮持续投入教育和一次性跳到同样的识字率，后续发展潜力完全不同。

**层层约束。** 物质基底 → 生产关系 → 上层建筑 → 政策空间。每一层约束上一层。想跳层可以尝试，但代价极大，大概率失败。

**渐进演化。** 没有硬性的"时代"分界线。科技、制度、文化连续变化。行动菜单随文明能力结构动态生成，不靠时代标签切换。

### 1.3 玩家身份

玩家不是某一个君主，而是**王朝/统治集团**本身。换代自然过渡——老王驾崩、新王即位是叙事事件，不中断游戏。玩家的决策代表统治集团的集体意志，而非个人命令。

当王朝崩溃（大规模叛乱失控、外族征服、统治集团瓦解）时，**Game Over**。玩家可读档重来。

### 1.4 核心循环

```
玩家阅读当前状态 + 近期叙事
         │
         ▼
输入自然语言政令（或从行动菜单选择）
         │
         ▼
LLM① 意图解析：分类 + 前置条件检查 + 定性判断
         │ 结构化 JSON
         ▼
数学引擎：成功率 → 掷骰 → 查模型表 → 数值结算 → 被动事件检查
         │ 数值变动 + 事件列表
         ▼
记忆系统：检索相关历史事件
         │ 历史上下文
         ▼
LLM② 叙事生成：数值变动 + 历史上下文 → 中文史官叙事（流式输出）
         │
         ▼
前端更新：叙事区显示新日志 + 状态面板更新 + 行动菜单刷新
         │
         ▼
后台：更新积累值 + 压缩记忆 + 被动时间推进 + Game Over 检查
```

---

## 二、文明状态维度体系

### 2.1 四层结构总览

```
第一层：物质基底（硬约束，决定一切的地基）
  ├── 人口
  ├── 粮食盈余率
  ├── 技术（农业 / 工程军事 / 知识文化 三线）
  ├── 领土（核心领土 + 边疆）
  └── 生态肥力

第二层：生产关系（定义"谁拥有什么、谁为谁劳动"）
  ├── 土地制度
  ├── 劳动形态
  └── 剩余提取方式

第三层：上层建筑（统治的形式与能力）
  ├── 政体结构
  ├── 官僚化程度
  ├── 合法性结构
  └── 宗教体系

第四层：社会张力（派生指标，由前三层自动计算）
  ├── 阶级矛盾
  └── 精英凝聚力
```

### 2.2 第一层：物质基底

#### 人口 `population`

- 类型：整数
- 初始范围：10,000 — 100,000（视文明而定）
- 自然增长率：由粮食盈余率决定
  - 盈余率 < 1.0 → 人口下降（饥荒）
  - 1.0 — 1.2 → 微增长 0 — 0.5%/年
  - 1.2 — 1.5 → 正常增长 0.5 — 1.5%/年
  - 1.5+ → 快速增长，上限 2%/年
- 特殊减少事件：战争、瘟疫、饥荒、大规模迁徙
- 玩家可见：✅（侧栏主面板）

#### 粮食盈余率 `food_surplus_ratio`

- 类型：浮点数
- 公式：`(农业技术 × 耕地面积 × 生态肥力 × 劳动效率系数) / (人口 × 人均需求基数)`
- 劳动效率系数：由劳动形态决定
  - 自由民自耕：1.0
  - 徭役制：0.85
  - 农奴制：0.75
  - 奴隶制：0.65（短期高产出但效率低）
- 耕地面积：核心领土 × 可耕比例（由生态肥力近似）
- 人均需求基数：常数 1.0（归一化后的单位）
- 意义：这是马尔萨斯模型的真正接入点。它不触发离散事件，而是持续压缩或释放行动空间。
  - < 0.8 → 饥荒状态，每轮稳定性自动下降，叛乱概率上升
  - 0.8 — 1.0 → 勉强维持，无余力执行大工程
  - 1.0 — 1.2 → 温饱，可以支撑小规模建设和常备军
  - 1.2 — 1.5 → 小康，可以支撑官僚体系、大型工程
  - 1.5+ → 富裕，可以支撑学术、远征、制度改革
- 玩家可见：✅（显示为文字描述：饥荒 / 勉强温饱 / 温饱 / 小康 / 富裕）

#### 技术三线

技术不是一个统一数值，而是三条独立发展线。每条线的等级是连续浮点数（0.0 起步，无硬上限，但有实际天花板，约 5.0 对应近代早期）。

**农业技术 `tech_agriculture`**
- 影响：粮食产出、可开垦土地类型
- 里程碑示例：0.5=刀耕火种 → 1.0=灌溉农业 → 1.5=铁制农具 → 2.0=轮作制 → 2.5=水利工程 → 3.0=选种育种
- 玩家可见：✅

**工程与军事技术 `tech_engineering`**
- 影响：建筑能力、军事装备、基础设施、领土防御
- 里程碑示例：0.5=石器工具 → 1.0=青铜冶炼 → 1.5=铁器 → 2.0=攻城器械 → 2.5=道路与桥梁体系 → 3.0=钢铁冶炼
- 玩家可见：✅

**知识与文化技术 `tech_knowledge`**
- 影响：识字率、官僚效率上限、制度创新上限
- 里程碑示例：0.5=口头传统 → 1.0=象形文字 → 1.5=字母/简化文字 → 2.0=学宫/书院 → 2.5=印刷术 → 3.0=系统化学术
- 派生指标——识字率 `literacy_rate`：
  - 公式：`min(tech_knowledge × 0.15, 0.8) × 知识机构覆盖率`
  - 知识机构覆盖率：由宗教知识载体属性和学宫建设共同决定
  - 玩家可选显示：✅（后台有精确值，前端默认显示文字描述，玩家可在设置中开启数值显示）
- 玩家可见：✅

**技术路径依赖规则：**
- 每条线独立发展，但存在软性耦合：工程技术 > 2.0 需要知识技术 ≥ 1.0（需要记录和传承复杂工艺）
- 技术等级不会自然下降（已掌握的技术不会遗忘），除非发生重大灾难（战争摧毁、文化灭绝）
- 自然增长极慢（约 0.02 — 0.05/回合），主要靠玩家行动推进

#### 领土 `territory`

拆分为两个区域：

**核心领土 `territory_core`**
- 类型：整数（km²）
- 特征：治理效率不衰减，政令完全执行
- 扩展方式：同化（极慢）、长期驻军后转化

**边疆 `territory_frontier`**
- 类型：整数（km²）
- 特征：治理效率随距离衰减
- 治理效率公式：`E = 官僚化程度 × e^(-D_norm / V_norm)`
  - `D_norm = territory_frontier / territory_core`（边疆与核心的比值，无量纲）
  - `V_norm = (tech_engineering + tech_knowledge) / 2`（交通与通讯能力）
  - 实际含义：边疆面积超过核心面积时，没有足够的技术支撑，治理效率指数衰减
- 在边疆执行的政策，效果乘以治理效率系数
- 扩展方式：征服、殖民、联盟
- 玩家可见：✅（合并显示总领土，悬浮查看核心/边疆比例）

#### 生态肥力 `biome_fertility`

- 类型：浮点数 0.0 — 1.0
- 开局由地域决定，对局中缓慢变化
- 下降因素：过度耕作（粮食盈余率长期 > 1.5 且无轮作技术）、气候事件
- 上升因素：水利工程（农业技术里程碑）、休耕政策
- 玩家可见：❌（隐含在粮食盈余率中）

### 2.3 第二层：生产关系

这三个维度共同定义了"谁拥有生产资料、谁劳动、剩余产品怎么分配"。它们不是独立滑块，存在合法组合约束。

#### 土地制度 `land_system`

枚举值（文明同一时间只有一种主导制度，但可以并存过渡态）：

| 制度 | 描述 | 对粮食盈余的影响 | 对阶级矛盾的影响 |
|------|------|------------------|------------------|
| `clan_communal` | 氏族公有，集体耕作 | 产出低但分配均匀 | 矛盾低 |
| `noble_estate` | 贵族庄园，农民依附 | 产出中，贵族提取大量剩余 | 矛盾中高 |
| `state_grant` | 国有授田，按功/职分配 | 产出中高，国家控制强 | 矛盾中（取决于授田公平性） |
| `landlord_tenant` | 地主租佃，农民交租 | 产出高，但农民所得少 | 矛盾高 |
| `yeoman_smallhold` | 自耕农小农，个体经营 | 产出高，分配较均 | 矛盾低中 |

**制度变更规则：**
- 变更不是一个回合完成的。发起变更后，进入过渡期（3-5 轮），期间新旧制度并存，矛盾升高
- 前置条件：统治力 + 官僚化程度足以推行，或通过暴力革命（叛乱成功）强制切换
- 每种制度对后续可选制度有限制：`clan_communal` 不能直接跳到 `yeoman_smallhold`，中间必须经过过渡

#### 劳动形态 `labor_system`

不是单一枚举，而是**比例分布**（总和 = 100%）：

```
labor_distribution: {
  free_citizens: 0.0 — 1.0,    // 自由民（自主劳动）
  corvee: 0.0 — 1.0,           // 徭役（义务劳动，保留人身自由）
  serf: 0.0 — 1.0,             // 农奴（依附土地，有限人身自由）
  slave: 0.0 — 1.0             // 奴隶（无人身自由）
}
```

- 劳动效率 = 各类劳动者比例的加权平均效率
- 阶级矛盾贡献 = `serf × 0.3 + slave × 0.5`（受压迫劳动者越多，矛盾越高）
- 变更方式：渐进（政策每轮移动 5-15%）或剧烈（解放令/大规模奴役，但引发巨大动荡）

#### 剩余提取方式 `surplus_extraction`

| 方式 | 前置条件 | 国家财政效率 | 对经济发展的影响 |
|------|----------|-------------|------------------|
| `tribute` 贡赋 | 无 | 低（不稳定，随忠诚度波动） | 中性 |
| `tax_in_kind` 实物税 | 官僚化 ≥ 0.2 | 中（可预测但运输损耗大） | 略负（抑制交换） |
| `tax_monetary` 货币税 | 官僚化 ≥ 0.4 + 商业活动存在 | 高（灵活、损耗小） | 正面（促进货币化） |
| `commercial_tax` 商业税 | 官僚化 ≥ 0.3 + 贸易网络 | 视商业规模而定 | 强正面（激励贸易） |

- 多种方式可以并存（比例分配）
- 国家财政能力 = 提取效率 × 粮食盈余（或商业规模）× 治理效率

### 2.4 第三层：上层建筑

#### 政体结构 `polity`

不是单一枚举，而是三个子维度的组合：

**权力来源 `authority_source`：** `bloodline`（血统）/ `military`（军功）/ `election`（选举/推举）/ `theocratic`（神权）

**决策结构 `decision_structure`：** `autocracy`（独裁）/ `oligarchy`（寡头）/ `council`（议事会）/ `bureaucracy`（官僚体制）

**继承方式 `succession`：** `hereditary`（世袭）/ `abdication`（禅让）/ `election`（选举）/ `military_coup`（军事夺权）

常见历史组合示例：
- 苏美尔城邦：`election` + `council` + `election`
- 埃及法老：`theocratic` + `autocracy` + `hereditary`
- 西周：`bloodline` + `oligarchy` + `hereditary`
- 罗马共和：`military` + `oligarchy` + `election`
- 秦帝国：`military` + `bureaucracy` + `hereditary`

**政体影响机制：**
- `autocracy` → 决策速度快，但精英凝聚力对统治者个人能力敏感
- `council` → 决策慢，但更稳定
- `bureaucracy` → 需要高识字率和知识技术，但执行力最强
- 权力来源决定合法性类型（见下文）

#### 官僚化程度 `bureaucratization`

- 类型：浮点数 0.0 — 1.0
- 含义：国家通过制度化行政体系（而非个人关系）执行政策的能力
- 上限由知识技术约束：`bureaucratization_max = min(tech_knowledge × 0.4, 1.0)`
- 影响：
  - 政策执行力（官僚化低 → 诏令出不了首都）
  - 税收效率（可用的提取方式受限）
  - 改革可行性（制度变更需要官僚体系来落地）
- 增长方式：建立行政机构、推行文官制度、编纂法典
- 衰减方式：裙带关系侵蚀、长期忽视、战乱破坏行政网络
- 玩家可见：✅（显示为：原始部落治理 / 酋长个人统治 / 初级官僚 / 成熟官僚体系 / 高度制度化）

#### 合法性结构 `legitimacy`

合法性不是一个数值，而是由多个来源组成的结构，每个来源有自己的强度：

```
legitimacy: {
  traditional: 0.0 — 1.0,   // 传统型："我们家族一直统治"
  religious: 0.0 — 1.0,     // 宗教型："天命所归/神选"
  performance: 0.0 — 1.0,   // 绩效型："我带来了胜利/繁荣"
  legal: 0.0 — 1.0          // 法理型："制度规定我来统治"
}
```

- 总合法性 = 各来源强度的加权和（权重由社会结构决定）
- 不同来源对不同危机的敏感度：

| 来源 | 饥荒时 | 军事失败时 | 继承危机时 | 改革时 |
|------|--------|-----------|-----------|--------|
| 传统型 | 缓降 | 缓降 | 急降 | 不变 |
| 宗教型 | 不变 | 缓降 | 不变 | 可能急降（改革触犯教义） |
| 绩效型 | 急降 | 急降 | 不变 | 视结果而定 |
| 法理型 | 不变 | 不变 | 不变（制度处理） | 不变 |

- 总合法性低于阈值 → 叛乱概率急升、精英凝聚力下降
- 玩家可见：✅（显示为文字描述 + 主要合法性来源标签）

#### 宗教体系 `religions`

每个文明维护一个宗教实体列表（可以有 0 到多个）：

```
religion: {
  name: str,                          // 名称
  type: enum,                         // 多神自然崇拜 / 祖先崇拜 / 城邦守护神 / 一神教 / 哲学伦理体系
  coverage: 0.0 — 1.0,                // 人口覆盖率（所有宗教 coverage 之和 ≤ 1.0）
  state_relation: enum,               // 国教 / 受庇护 / 容忍 / 受压制
  organization: 0.0 — 1.0,            // 组织化程度（0=散漫民间信仰，1=高度组织化教团）
  knowledge_carrier: bool,            // 是否承担教育/记录/历法职能
  economic_power: 0.0 — 1.0           // 经济实力（神殿经济/教会地产/什一税）
}
```

**宗教影响的四个通道：**

1. **合法性通道**：国教的 `coverage × organization` → 宗教合法性强度
2. **社会凝聚通道**：
   - 宗教多样性 = 1 - Σ(coverage²)（赫芬达尔指数的反面）
   - 宗教张力 = Σ(被压制宗教的 coverage)
   - 张力 > 0.3 → 宗教冲突风险上升
3. **经济通道**：高 `economic_power` 的宗教是改革阻力来源
4. **知识通道**：`knowledge_carrier = true` 的宗教贡献识字率和知识传播

**玩家与宗教的交互：** 玩家不直接操控宗教属性。通过政策间接影响：
- "立某教为国教" → 改变 `state_relation`，提升该教 `coverage`，降低其他教
- "打压异端" → 被压制教 `coverage` 缓降，但 `宗教张力` 上升
- "宗教容忍令" → 张力下降，但凝聚力也可能下降
- "没收寺庙土地" → 降低宗教 `economic_power`，但触发该教反抗

### 2.5 第四层：社会张力

这两个指标由前三层自动计算，玩家不直接操控，通过叙事传递。

#### 阶级矛盾 `class_tension`

- 类型：浮点数 0.0 — 1.0
- 计算公式：

```
class_tension =
    0.3 × 劳动压迫度（serf×0.3 + slave×0.5）
  + 0.3 × 土地不平等度（noble_estate=0.7, landlord_tenant=0.8, 其他按表）
  + 0.2 × 提取压力（总税负 / 粮食盈余率，超过0.5时急升）
  + 0.2 × 近期矛盾事件（制度变更、强制征兵等引发的短期冲击）
  - 稳定因子（宗教凝聚 + 合法性强度的削减项）
```

- 当 class_tension > 0.6 → 叙事中出现不满信号
- 当 class_tension > 0.8 → 叛乱事件概率显著上升
- 叛乱成功条件：class_tension > 0.8 + 精英凝聚力 < 0.3 + 军事力量不足以镇压
- 玩家不可见精确数值，通过叙事感知：
  - 0.0-0.3："百姓安居乐业"
  - 0.3-0.6："市井偶有怨言"
  - 0.6-0.8："各地民变频发，亟需安抚"
  - 0.8+："烽烟四起，社稷危殆"

#### 精英凝聚力 `elite_cohesion`

- 类型：浮点数 0.0 — 1.0
- 含义：统治集团内部的团结程度
- 下降因素：
  - 继承危机（无明确继承人）
  - 大规模改革（触动既得利益集团）
  - 军事失败
  - 长期无作为（派系自然分化）
- 上升因素：
  - 军事胜利（共同的外敌团结内部）
  - 绩效合法性高（大家都跟着有肉吃）
  - 人事清洗成功（高风险高回报）
- 当 elite_cohesion < 0.3 → 权臣篡位、地方割据的概率上升
- 玩家不可见精确数值，通过叙事感知

### 2.6 玩家可见性汇总

| 维度 | 默认显示 | 可选显示 | 隐藏 |
|------|----------|---------|------|
| 人口 | ✅ 数值 | | |
| 粮食盈余率 | ✅ 文字档位 | ✅ 精确数值 | |
| 技术三线 | ✅ 数值+里程碑 | | |
| 识字率 | | ✅ 百分比 | ✅ 默认隐藏 |
| 领土（总） | ✅ 数值 | ✅ 核心/边疆比 | |
| 生态肥力 | | | ✅ |
| 土地制度 | ✅ 名称 | | |
| 劳动形态 | ✅ 主导类型 | ✅ 完整比例 | |
| 剩余提取 | ✅ 主要方式 | | |
| 政体 | ✅ 组合描述 | | |
| 官僚化 | ✅ 文字档位 | ✅ 数值 | |
| 合法性 | ✅ 主要来源标签 | ✅ 各源强度 | |
| 宗教 | ✅ 名称+国教标记 | ✅ 详细属性 | |
| 阶级矛盾 | | | ✅ 仅通过叙事 |
| 精英凝聚力 | | | ✅ 仅通过叙事 |

---

## 三、数学模型

### 3.1 社会摩擦模型（成功率计算）

所有玩家行动的成功率由此模型决定。

```
P_success = P_base × authority_mod × infrastructure_mod × accumulation_mod × random_factor

其中：
  P_base = 0.8 × (1 - cognitive_gap × resistance / A_norm)
  
  cognitive_gap: LLM 判断的认知代差（0-5），衡量行动超前程度
  resistance: 社会惯性系数，由结构状态计算
    = 0.3 × (1 - bureaucratization)          // 官僚化不足
    + 0.3 × (class_tension)                  // 阶级矛盾
    + 0.2 × (1 - elite_cohesion)             // 精英不团结
    + 0.2 × (religious_resistance)           // 宗教阻力（若触犯宗教利益）
  A_norm = max(统治力 / 20, 0.5)             // 归一化统治力，下限提高到0.5避免v0.1的不可玩问题

  authority_mod: 权威修正
    = 1.0（decision_structure = autocracy 时行动更快但风险更高）
    = 0.8（council 时成功率略低但失败后果更小）
    
  infrastructure_mod: 基础设施修正
    = 治理效率（边疆行动时打折）
    × 前置条件满足度（0 或 1，不满足则整个行动不可执行）
    
  accumulation_mod: 路径积累修正（见第六节）
    = 1.0 + 相关领域积累值 × 0.3（最高 +30% 加成）
    
  random_factor: 随机修正 0.85 — 1.15（±15%波动）
```

**成功率到结果的映射（掷骰）：**

| P_success 区间 | 大成功概率 | 成功 | 部分成功 | 失败 | 灾难性失败 |
|---------------|-----------|------|---------|------|-----------|
| 0.8+ | 20% | 50% | 25% | 5% | 0% |
| 0.6 — 0.8 | 10% | 35% | 35% | 15% | 5% |
| 0.4 — 0.6 | 5% | 20% | 35% | 30% | 10% |
| 0.2 — 0.4 | 0% | 10% | 25% | 45% | 20% |
| < 0.2 | 0% | 5% | 15% | 40% | 40% |

每档结果对数值变化的影响程度：大成功 = 150%效果，成功 = 100%，部分成功 = 50%，失败 = 0% + 副作用，灾难性失败 = 负面效果 + 严重副作用。

### 3.2 治理效率衰减模型

```
E_governance = bureaucratization × e^(-D_norm / V_norm)

D_norm = territory_frontier / max(territory_core, 1)
V_norm = (tech_engineering + tech_knowledge) / 2
```

影响范围：
- 在边疆执行的所有政策，效果 × E_governance
- 边疆税收效率 × E_governance
- 边疆叛乱镇压能力 × E_governance

参数标定检验：
- 典型早期文明：`bureaucratization=0.2, frontier=500, core=500, tech≈1.0`
  → `E = 0.2 × e^(-1/1) = 0.2 × 0.37 = 0.074` → 边疆几乎不受控
- 成熟帝国：`bureaucratization=0.6, frontier=2000, core=1000, tech≈2.0`
  → `E = 0.6 × e^(-2/2) = 0.6 × 0.37 = 0.22` → 边疆控制力有限
- 高度发达：`bureaucratization=0.8, frontier=1000, core=2000, tech≈3.0`
  → `E = 0.8 × e^(-0.5/3) = 0.8 × 0.85 = 0.68` → 有效控制

这比 v0.1 的参数合理得多。关键改变是用 D_norm（比值）替代原始领土面积。

### 3.3 人口动态模型

每轮结算时：

```
// 1. 计算粮食盈余率
food_surplus_ratio = calculate_food_surplus(...)

// 2. 基础增长率
if food_surplus_ratio < 0.8:
    base_growth = -0.02 × (0.8 - food_surplus_ratio) / 0.8  // 饥荒，最多-2%
elif food_surplus_ratio < 1.0:
    base_growth = -0.005  // 微降
elif food_surplus_ratio < 1.2:
    base_growth = 0.005   // 微增
elif food_surplus_ratio < 1.5:
    base_growth = 0.01    // 正常增长
else:
    base_growth = 0.015   // 快速增长

// 3. 按本回合时间跨度折算（年化率 × 回合年数）
actual_growth = base_growth × turn_years

// 4. 事件修正（战争死亡、瘟疫等由行动结算另加）
population_new = population × (1 + actual_growth) + event_population_change
```

### 3.4 稳定性模型

稳定性 `stability`（0-100）每轮自动调整：

```
stability_delta =
    +5 × (food_surplus_ratio - 1.0)           // 温饱程度
  + 3 × (legitimacy_total - 0.5)              // 合法性
  - 10 × max(class_tension - 0.5, 0)          // 阶级矛盾超标
  - 5 × max(0.5 - elite_cohesion, 0)          // 精英分裂
  + 行动结果带来的稳定性变化                     // 由具体行动决定
  
stability = clamp(stability + stability_delta, 0, 100)
```

### 3.5 统治力模型

统治力 `authority`（0-100）反映统治集团的实际控制力：

```
authority_delta =
    + 成功行动的统治力增益
    - 失败行动的统治力损失
    + 3 × (elite_cohesion - 0.5)              // 精英团结
    - 5 × max(class_tension - 0.6, 0)          // 高矛盾侵蚀
    - 2 × (bureaucratization < 0.2 时的衰减)    // 缺乏制度化

authority = clamp(authority + authority_delta, 0, 100)
```

---

## 四、行动系统

### 4.1 行动分类体系

定义 6 个行动域，每个域下有若干行动类型。行动菜单根据当前文明能力结构动态生成可用行动列表。

```
行动域：
├── 经济 (economic)
│   ├── 农业发展（开垦、灌溉、推广新作物）
│   ├── 贸易政策（开放市场、设关卡、建商路）
│   ├── 基础设施（修路、建仓、挖渠）
│   └── 税制改革（更改提取方式、调整税率）
│
├── 政治 (political)
│   ├── 制度改革（改变政体、土地制度、劳动形态）
│   ├── 行政建设（设置官职、编纂法典、建立档案）
│   ├── 人事任免（清洗/任命/联姻）
│   └── 外交（联盟、和亲、朝贡 — MVP 简化处理）
│
├── 军事 (military)
│   ├── 军备建设（练兵、造武器、筑城）
│   ├── 征伐（进攻邻近区域）
│   ├── 防御（应对入侵事件）
│   └── 镇压（应对叛乱）
│
├── 文化 (cultural)
│   ├── 教育（建学宫、推识字、培养工匠）
│   ├── 宗教政策（立国教、容忍、打压、世俗化）
│   ├── 意识形态（宣传合法性、重构历史叙事）
│   └── 文化工程（修建纪念建筑、编纂典籍）
│
├── 科技 (technology)
│   ├── 技术研发（投入资源推进某条技术线）
│   ├── 技术引进（从其他文明学习 — MVP 简化）
│   └── 知识注入（玩家提供超前知识 — 特殊管线）
│
└── 综合 (composite)
    └── 自由输入（不属于以上类别的创意行动）
```

### 4.2 行动菜单动态生成

行动菜单不是固定列表，而是根据当前状态动态筛选：

```python
def generate_action_menu(state):
    available_actions = []
    for action in ALL_ACTIONS:
        if check_prerequisites(action, state):
            available_actions.append({
                "name": action.name,
                "domain": action.domain,
                "description": action.description,
                "difficulty_hint": estimate_difficulty(action, state),  # 容易/中等/困难/极难
                "prerequisite_note": action.prerequisite_description
            })
    return available_actions
```

前置条件示例：
- "推行郡县制" → 需要 `bureaucratization ≥ 0.3` + `tech_knowledge ≥ 1.5` + `authority ≥ 40`
- "铸造货币" → 需要 `tech_engineering ≥ 1.0` + 商业活动存在
- "建立常备军" → 需要 `food_surplus_ratio ≥ 1.2`（养得起不种地的士兵）

**玩家始终可以自由输入。** 菜单是参考，不是限制。自由输入走 LLM 解析管线。

### 4.3 LLM 意图解析管线

```python
# LLM① 的系统提示词核心逻辑：

"""
你是一位古代文明的御前大臣。玩家（统治集团）下达了一道政令。
你的职责是分析这道政令，输出结构化评估。

你不决定结果，只提供判断材料。数值计算由数学引擎完成。

输出 JSON：
{
  "action_domain": "economic|political|military|cultural|technology|composite",
  "action_type": "具体行动类型",
  "action_description": "一句话描述这个行动的实质",
  
  "cognitive_gap": 0-5,  // 这个行动相对于当前文明认知水平的超前程度
  // 0=完全符合常识，1=略有创新，2=需要一定知识基础，
  // 3=明显超前，4=非常超前，5=完全不可理解
  
  "resistance_sources": ["贵族阶层", "祭司集团", ...],  // 谁会反对
  "beneficiaries": ["农民", "商人", ...],  // 谁会受益
  
  "prerequisites": {
    "met": true/false,
    "details": "需要什么条件，当前是否满足",
    "nearest_alternative": "如果不满足，最近的可行替代是什么"
  },
  
  "is_knowledge_injection": true/false,  // 是否包含超越时代的知识描述
  "knowledge_detail_level": "concept|direction|operational|detailed",
  
  "time_estimate_years": 1-20,  // 这个行动大约需要多少年
  "time_estimate_reasoning": "为什么是这个时间跨度"
}

当前文明状态：{state_summary}
最近5轮摘要：{recent_summary}
"""
```

**前置条件不满足时的处理：**

LLM 不说"不可执行"。它输出 `prerequisites.met = false`，以及 `nearest_alternative`。然后系统仍然走数学引擎，但行动被降级为替代行动。叙事中解释为什么原始意图无法实现，以及实际发生了什么。

示例：玩家输入"推行科举"，但识字率极低。

```
LLM 输出：prerequisites.met = false, 
  nearest_alternative = "建立地方学宫，培养基层识字人才"
→ 数学引擎按替代行动计算
→ 叙事："丞相献策，欲以试策取士。然国中识字者百不足一，
  学宫空设，无人应试。王遂改令，先于各郡设学宫，
  延请博学之士教化子弟。此为科举之基也。"
```

### 4.4 可变时间跨度

每个行动的时间跨度由 LLM 建议 + 规则约束决定：

| 行动类型 | 典型时间跨度 | 规则约束 |
|----------|-------------|---------|
| 战役/防御 | 0.25 — 0.5 年 | 不超过 1 年 |
| 宫廷政变/危机 | 0.1 — 0.25 年 | 不超过 0.5 年 |
| 法令/政策 | 1 — 3 年 | 不超过 5 年 |
| 基础设施 | 2 — 5 年 | 不超过 10 年 |
| 制度改革 | 2 — 5 年 | 不超过 5 年 |
| 文化/教育 | 3 — 5 年 | 不超过 10 年 |
| 技术研发 | 1 — 5 年 | 不超过 10 年 |

**被动时间推进：**

在行动消耗的时间内，以下事情自动发生：
1. 人口按年化增长率增长
2. 稳定性按当前结构缓慢变化
3. 积累值自然衰减
4. 之前推行的政策持续发酵（过渡期推进）
5. 可能触发随机事件（概率正比于时间跨度）：
   - 自然灾害（旱灾、洪水、地震）
   - 疫病
   - 边境冲突
   - 继承事件（统治者死亡、幼主即位）

---

## 五、知识注入机制

### 5.1 触发条件

当 LLM① 判定 `is_knowledge_injection = true` 时，进入知识注入评估管线（而非常规行动管线）。

### 5.2 三维评估

```
维度一：描述可执行度 (detail_level) — 由 LLM 判断

  "concept"   → 0.1 系数（只说了个名字，如"发明火药"）
  "direction" → 0.3 系数（给了方向，如"硝石和硫磺混合可以爆炸"）
  "operational"→ 0.6 系数（给了可操作步骤）
  "detailed"  → 0.9 系数（给了详细工序、材料比例、关键参数）

维度二：执行权威 (execution_authority)
  = min(authority / 100, 1.0) × bureaucratization_factor
  bureaucratization_factor = 0.5 + 0.5 × bureaucratization
  // 统治力高+官僚化程度高 → 能调动资源执行

维度三：基础设施跨度 (infra_gap)
  gap = 目标技术等级 - 当前相关技术等级
  if gap ≤ 1: infra_factor = 1.0      // 自然演进的加速
  if gap ≤ 2: infra_factor = 0.5      // 困难但可能做出粗糙原型
  if gap ≤ 3: infra_factor = 0.15     // 极难，需要大量中间环节
  if gap > 3:  infra_factor = 0.02    // 几乎不可能
```

### 5.3 结果计算

```
// 技术突破程度
breakthrough = detail_level × execution_authority × infra_factor

// 实际技术增长（降级处理，不直接获得目标技术）
if breakthrough > 0.5:
    tech_gain = min(gap, 1.0)           // 最多跳一个等级
elif breakthrough > 0.2:
    tech_gain = min(gap × 0.5, 0.5)     // 半个等级
elif breakthrough > 0.05:
    tech_gain = 0.1                      // 微小进步
else:
    tech_gain = 0                        // 失败

// 社会采纳（技术做出来了，但社会愿意用吗？）
adoption = social_friction_model(cognitive_gap=gap, ...)
final_tech_gain = tech_gain × adoption

// 副产品：学术积累值上升（即使失败，尝试本身也有价值）
academic_accumulation += breakthrough × 0.5
```

### 5.4 叙事角色设定

评判知识注入的 LLM 的角色不是审查员，而是"一个聪明但只有当时知识背景的工匠头领"：

```
"""
你是{civ_name}最有经验的工匠长。王上向你描述了一种新的技术方案。
你需要从你的经验出发判断：
1. 你能理解王上说的多少？（哪些部分对你来说是全新的概念？）
2. 以你现有的工具和材料，能不能尝试做出来？
3. 如果能做，大概做出来的东西是什么水平？
你不需要判断这个技术"应不应该"存在，只需要从实操角度说"能不能做"。
"""
```

---

## 六、路径积累系统

### 6.1 积累值定义

5 个领域维护各自的积累值（0.0 起步，无硬上限，但实践中约 0 — 3.0）：

```
accumulations: {
  academic:    0.0,   // 学术基础：教育/研究/知识传播
  military:    0.0,   // 军事传统：练兵/战争/军事改革
  commercial:  0.0,   // 商业生态：贸易/市场/货币
  administrative: 0.0, // 行政经验：官僚/法律/制度建设
  cultural:    0.0    // 宗教文化：宗教/仪式/意识形态
}
```

### 6.2 积累值更新规则

每轮结算时：

```python
# 行动贡献
for action in this_turn_actions:
    domain = action.domain_mapping  # 行动域 → 积累域
    success_weight = {
        "great_success": 1.5,
        "success": 1.0,
        "partial": 0.5,
        "failure": 0.1,  # 失败也有微小贡献（经验教训）
        "disaster": 0.0
    }[action.result]
    accumulations[domain] += 0.2 × success_weight

# 自然衰减（每轮）
for domain in accumulations:
    accumulations[domain] *= 0.95  # 5%衰减率
    # 但如果有制度化支撑，衰减更慢
    if domain == "academic" and has_academy:
        accumulations[domain] *= 1.03  # 部分抵消衰减
    if domain == "administrative" and bureaucratization > 0.5:
        accumulations[domain] *= 1.02
```

### 6.3 积累值的影响

```python
# 1. 修正行动成功率（accumulation_mod in 社会摩擦模型）
accumulation_mod = 1.0 + relevant_accumulation × 0.3

# 2. 修正知识注入可执行度
# 学术积累高 → 工匠/学者理解力加成
knowledge_injection_bonus = academic_accumulation × 0.15

# 3. 影响自然技术增长速度
# 积累值高的领域，技术自然增长更快
natural_tech_growth[domain] = base_growth × (1 + accumulation × 0.5)

# 4. 影响制度变革的平滑程度
# 行政积累高 → 制度过渡期更短、动荡更小
transition_turbulence *= (1 - administrative_accumulation × 0.2)
```

---

## 七、记忆系统（上下文工程）

### 7.1 三层架构

```
┌─────────────────────────────────────────────┐
│  近期记忆（最近 5 轮）                         │
│  完整记录：玩家指令、LLM 判断、数值变动、叙事全文  │
│  用途：直接喂给 LLM②叙事生成                    │
│  存储：内存 + PostgreSQL turns 表              │
├─────────────────────────────────────────────┤
│  中期摘要（第 6-30 轮，每 5 轮一条摘要）          │
│  内容：关键事件、因果链、领域行动频次、主要数值变化  │
│  生成方式：每 5 轮由 LLM 压缩                   │
│  用途：作为叙事 LLM 的"近代史"背景               │
│  存储：PostgreSQL summaries 表                │
├─────────────────────────────────────────────┤
│  长期索引（全部历史中的关键转折点）                 │
│  内容：朝代更替、制度变革、重大战争、技术突破        │
│  标签：按主题（政治/经济/军事/文化/科技）索引      │
│  用途：当前行动涉及相关领域时，检索并注入上下文      │
│  存储：PostgreSQL landmarks 表               │
└─────────────────────────────────────────────┘
```

### 7.2 中期摘要生成

每 5 轮触发一次摘要压缩：

```python
summary_prompt = """
以下是{civ_name}最近5轮（{year_start}年—{year_end}年）的完整记录。
请压缩为一段 200-300 字的摘要，必须保留：
1. 这5轮中最重要的 1-3 件事及其因果关系
2. 各维度的主要变化方向（上升/下降/稳定）
3. 每轮行动所属的领域标签（用于积累值追踪）
4. 任何可能在未来产生长期影响的种子事件

不要保留的：数值细节、叙事修辞、重复信息
格式：纯文本，不用 Markdown
"""
```

### 7.3 长期索引生成

当以下事件发生时，自动创建一条长期索引条目：

- 制度变更（土地制度、劳动形态、政体组件变化）
- 技术突破（任意一条技术线提升 ≥ 0.5）
- 重大军事事件（领土变化 ≥ 20%）
- 合法性危机（总合法性降到 0.3 以下）
- 稳定性极端事件（叛乱、饥荒、瘟疫）
- 宗教变动（新教/改宗/打压/宗教冲突）

```python
landmark_entry = {
    "turn": current_turn,
    "year": current_year,
    "tags": ["political", "institutional"],  # 主题标签
    "title": "推行郡县制",                     # 一句话标题
    "summary": "...",                         # 2-3句描述，含因果
    "state_snapshot": {                       # 当时的关键状态快照
        "population": ...,
        "stability": ...,
        "tech_levels": ...,
        "land_system": ...,
    }
}
```

### 7.4 历史检索与注入

叙事 LLM 生成前，系统检索相关历史：

```python
def retrieve_history_context(current_action, state):
    # 1. 根据当前行动的领域标签检索长期索引
    relevant_landmarks = db.query(
        "SELECT * FROM landmarks WHERE tags && %s ORDER BY turn DESC LIMIT 5",
        [current_action.domain_tags]
    )
    
    # 2. 获取中期摘要（最近 5 条 = 约 25 轮的压缩历史）
    recent_summaries = db.query(
        "SELECT * FROM summaries WHERE game_id = %s ORDER BY turn DESC LIMIT 5",
        [game_id]
    )
    
    # 3. 组装上下文
    history_context = format_history(relevant_landmarks, recent_summaries)
    return history_context
```

叙事 LLM 的 prompt 中：

```
"""
...
【历史背景】
{history_context}

请在叙事中自然地体现历史因果。如果当前事件与历史事件有关联，
要让读者感受到"因为当年做了X，所以今天Y才会发生"。
不要生硬地回顾历史，而是让因果关系自然浮现在叙事中。
...
"""
```

---

## 八、Game Over 机制

### 8.1 三种死法

**大规模叛乱失控**
- 触发条件：class_tension > 0.8 + stability < 20，持续 2 轮以上
- 警告信号（叙事中出现）：
  - 第一轮超标："各地匪盗蜂起，郡县官吏弃印逃亡"
  - 第二轮超标："叛军已据三郡，遥望王城"
  - 第三轮若仍未改善 → 触发叛乱决战事件
    - 军事力量足够 → 可镇压（但代价惨重）
    - 军事力量不足 → Game Over："王朝覆灭"

**精英瓦解**
- 触发条件：elite_cohesion < 0.15，持续 2 轮以上
- 表现：权臣篡位 或 地方势力宣布独立
- 警告信号："大将军拥兵自重，不听调遣" / "封疆大吏自行铸币"
- 若 authority 也低于 20 → Game Over："王朝分裂"

**文明崩溃**
- 触发条件：population < 初始人口的 10%
- 通常由持续饥荒或灾难性战败导致
- 不可逆 → 直接 Game Over："文明湮灭"

### 8.2 Game Over 展示

Game Over 时，展示一份"文明终结报告"：

```
{civ_name} · 历{total_turns}回合 · {start_year} — {end_year}

终结原因：{death_type}
巅峰时期：第{peak_turn}回合（人口{peak_pop}，领土{peak_territory}）
重大成就：{achievements_list}
历史教训：{lessons}（LLM 生成的 2-3 句反思）

[读档] [新游戏] [查看完整历史]
```

---

## 九、文明模板（MVP：6个）

### 9.1 模板设计原则

每个模板不只是一组数值，而是一套完整的初始结构，包含独特的生产关系和上层建筑组合，让 6 个文明从第一回合就有截然不同的体验。

### 9.2 模板列表

#### 苏美尔城邦联盟（两河流域，公元前 3000 年）

```yaml
# 物质基底
population: 30000
tech_agriculture: 1.0    # 灌溉农业已成熟
tech_engineering: 0.8
tech_knowledge: 1.0       # 楔形文字
territory_core: 300
territory_frontier: 200
biome_fertility: 0.75

# 生产关系
land_system: noble_estate         # 神殿-贵族庄园
labor_distribution:
  free_citizens: 0.4
  corvee: 0.3
  serf: 0.1
  slave: 0.2
surplus_extraction: [tribute, tax_in_kind]

# 上层建筑
polity:
  authority_source: theocratic     # 神权
  decision_structure: council      # 长老议事会
  succession: election             # 推举
bureaucratization: 0.25
legitimacy:
  traditional: 0.4
  religious: 0.7
  performance: 0.3
  legal: 0.1
religions:
  - name: 城邦守护神信仰
    type: city_patron
    coverage: 0.9
    state_relation: state_religion
    organization: 0.6
    knowledge_carrier: true
    economic_power: 0.5

# 社会张力（初始）
stability: 65
authority: 25

# 积累值
accumulations: { academic: 0.3, military: 0.2, commercial: 0.4, administrative: 0.2, cultural: 0.5 }
```

特色：高宗教合法性，议事会制衡王权，商业传统强。挑战：统治力低，推进集权困难。

#### 早王朝埃及（尼罗河流域，公元前 3000 年）

```yaml
population: 40000
tech_agriculture: 1.0
tech_engineering: 0.9     # 建筑能力
tech_knowledge: 0.8
territory_core: 600
territory_frontier: 200
biome_fertility: 0.85     # 尼罗河泛滥区

land_system: state_grant           # 法老授田
labor_distribution:
  free_citizens: 0.3
  corvee: 0.5              # 大量徭役（建金字塔的人力来源）
  serf: 0.1
  slave: 0.1
surplus_extraction: [tax_in_kind]

polity:
  authority_source: theocratic
  decision_structure: autocracy
  succession: hereditary
bureaucratization: 0.35
legitimacy:
  traditional: 0.5
  religious: 0.8            # 法老即神
  performance: 0.4
  legal: 0.2
religions:
  - name: 太阳神崇拜
    type: polytheistic
    coverage: 0.95
    state_relation: state_religion
    organization: 0.7
    knowledge_carrier: true
    economic_power: 0.6

stability: 70
authority: 50              # 法老权威高

accumulations: { academic: 0.2, military: 0.1, commercial: 0.1, administrative: 0.4, cultural: 0.6 }
```

特色：高统治力 + 强神权合法性，适合执行大工程。挑战：经济单一（依赖尼罗河），商业基础弱。

#### 哈拉帕联盟（印度河流域，公元前 2000 年）

```yaml
population: 50000
tech_agriculture: 1.2
tech_engineering: 1.0       # 城市规划能力强
tech_knowledge: 0.8
territory_core: 800
territory_frontier: 400
biome_fertility: 0.65

land_system: clan_communal          # 氏族公有为主
labor_distribution:
  free_citizens: 0.7
  corvee: 0.2
  serf: 0.05
  slave: 0.05
surplus_extraction: [tribute]

polity:
  authority_source: election        # 推举
  decision_structure: council       # 长老会
  succession: election
bureaucratization: 0.2
legitimacy:
  traditional: 0.6
  religious: 0.3
  performance: 0.5
  legal: 0.1
religions:
  - name: 自然崇拜
    type: nature_worship
    coverage: 0.7
    state_relation: tolerated
    organization: 0.2
    knowledge_carrier: false
    economic_power: 0.1

stability: 82               # 高稳定（矛盾少）
authority: 20                # 但统治力低（分散治理）

accumulations: { academic: 0.2, military: 0.1, commercial: 0.5, administrative: 0.1, cultural: 0.2 }
```

特色：高稳定低冲突的贸易文明，自由度高。挑战：统治力极低，集权改革极难推动；靠共识运转，一旦共识破裂可能快速瓦解。v0.1 的哈拉帕不可玩问题通过提高 A_norm 下限（0.5）来缓解，同时保留其"难以集权"的特色。

#### 古巴比伦王国（两河流域，公元前 2000 年）

```yaml
population: 60000
tech_agriculture: 1.2
tech_engineering: 1.1
tech_knowledge: 1.3          # 汉谟拉比法典
territory_core: 800
territory_frontier: 700
biome_fertility: 0.70

land_system: noble_estate
labor_distribution:
  free_citizens: 0.3
  corvee: 0.3
  serf: 0.2
  slave: 0.2
surplus_extraction: [tax_in_kind, tribute]

polity:
  authority_source: military       # 军事征服立国
  decision_structure: autocracy
  succession: hereditary
bureaucratization: 0.4             # 法典带来的制度化
legitimacy:
  traditional: 0.3
  religious: 0.5
  performance: 0.6
  legal: 0.4                       # 法典提供法理合法性
religions:
  - name: 马尔杜克神崇拜
    type: city_patron
    coverage: 0.7
    state_relation: state_religion
    organization: 0.5
    knowledge_carrier: true
    economic_power: 0.4

stability: 75
authority: 45

accumulations: { academic: 0.4, military: 0.3, commercial: 0.3, administrative: 0.5, cultural: 0.3 }
```

特色：已有法典传统（法理合法性高），行政基础好。挑战：边疆大，治理衰减明显；劳动形态压迫度较高，阶级矛盾隐患。

#### 西周王朝（黄河流域，公元前 1000 年）

```yaml
population: 80000
tech_agriculture: 1.5
tech_engineering: 1.3
tech_knowledge: 1.2
territory_core: 1000
territory_frontier: 1000
biome_fertility: 0.65

land_system: state_grant           # 井田制 ≈ 国有授田
labor_distribution:
  free_citizens: 0.3
  corvee: 0.4
  serf: 0.2
  slave: 0.1
surplus_extraction: [tribute, tax_in_kind]

polity:
  authority_source: bloodline      # 宗法制
  decision_structure: oligarchy    # 封建诸侯
  succession: hereditary           # 嫡长子继承
bureaucratization: 0.3
legitimacy:
  traditional: 0.8                 # 宗法传统
  religious: 0.5                   # 天命
  performance: 0.4
  legal: 0.2
religions:
  - name: 天命信仰与祖先崇拜
    type: ancestor_worship
    coverage: 0.8
    state_relation: state_religion
    organization: 0.4
    knowledge_carrier: true
    economic_power: 0.3

stability: 70
authority: 60                      # 高统治力

accumulations: { academic: 0.3, military: 0.4, commercial: 0.2, administrative: 0.3, cultural: 0.5 }
```

特色：最高统治力，改革推行力强。挑战：封建结构意味着诸侯势力大（elite_cohesion 容易下降），边疆与核心等大（治理衰减问题），传统合法性极强反而使激进改革更困难（动摇"祖制"）。

#### 古希腊城邦（地中海，公元前 500 年）

```yaml
population: 45000
tech_agriculture: 1.3
tech_engineering: 1.5
tech_knowledge: 1.8            # 哲学与科学传统
territory_core: 400
territory_frontier: 200
biome_fertility: 0.55          # 多山贫瘠

land_system: yeoman_smallhold          # 公民自耕农
labor_distribution:
  free_citizens: 0.5
  corvee: 0.1
  serf: 0.0
  slave: 0.4                   # 大量奴隶
surplus_extraction: [tax_monetary, commercial_tax]

polity:
  authority_source: election
  decision_structure: council          # 公民大会
  succession: election
bureaucratization: 0.2
legitimacy:
  traditional: 0.2
  religious: 0.2
  performance: 0.5
  legal: 0.5                          # 法律传统
religions:
  - name: 奥林匹斯诸神
    type: polytheistic
    coverage: 0.8
    state_relation: tolerated          # 宗教不主导政治
    organization: 0.3
    knowledge_carrier: false           # 知识由哲学家/学院承载
    economic_power: 0.2

stability: 60                          # 城邦政治本就不太稳定
authority: 20                          # 分权制，统治力低

accumulations: { academic: 0.8, military: 0.3, commercial: 0.6, administrative: 0.2, cultural: 0.7 }
```

特色：最高科技 + 最强学术积累 + 货币经济已存在。知识注入的天然温床。挑战：统治力极低（公民大会制），集权改革困难；奴隶比例高，阶级矛盾隐患；领土小且贫瘠，扩张空间有限。

---

## 十、技术架构

### 10.1 技术栈

```
前端：Next.js (React) + TypeScript + Tailwind CSS
后端：Python FastAPI
数据库：PostgreSQL (JSONB + 全文检索)
LLM：DeepSeek V4 Flash（OpenAI 兼容接口，可切换）
部署：Vercel (前端) + Railway/Fly.io (后端) + Neon/Supabase (PostgreSQL)
通信：REST + WebSocket（流式叙事输出）
```

### 10.2 后端模块结构

```
backend/
├── main.py                     # FastAPI 入口
├── config.py                   # 配置（LLM 模型、数据库、参数）
├── api/
│   ├── game.py                 # 游戏 CRUD：新建/存档/读档
│   ├── action.py               # 行动处理主入口
│   └── websocket.py            # WebSocket 流式输出
├── llm/
│   ├── client.py               # LLM 调用封装（模型可切换）
│   ├── intent_parser.py        # LLM①：意图解析 prompt + 解析
│   ├── knowledge_evaluator.py  # 知识注入评估 prompt + 解析
│   ├── narrator.py             # LLM②：叙事生成 prompt + 流式
│   └── summarizer.py           # 中期摘要压缩 prompt
├── engine/
│   ├── friction.py             # 社会摩擦模型
│   ├── governance.py           # 治理效率衰减
│   ├── population.py           # 人口动态
│   ├── stability.py            # 稳定性计算
│   ├── authority.py            # 统治力计算
│   ├── food.py                 # 粮食盈余率计算
│   ├── accumulation.py         # 积累值更新
│   ├── passive_events.py       # 被动事件生成
│   ├── gameover.py             # Game Over 检查
│   └── action_resolver.py      # 行动结果总结算
├── memory/
│   ├── recent.py               # 近期记忆管理
│   ├── summary.py              # 中期摘要管理
│   ├── landmark.py             # 长期索引管理
│   └── retriever.py            # 历史检索
├── templates/
│   ├── civilizations.py        # 6个文明模板
│   └── actions.py              # 行动类型定义 + 前置条件
├── models/
│   └── schemas.py              # Pydantic 数据模型
└── db/
    ├── database.py             # 数据库连接
    └── migrations/             # 数据库迁移
```

### 10.3 数据库 Schema

```sql
-- 游戏实例
CREATE TABLE games (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    civ_name TEXT,
    template_id TEXT,
    status TEXT DEFAULT 'active'  -- active / game_over
);

-- 当前状态（每局一行，频繁更新）
CREATE TABLE game_states (
    game_id UUID PRIMARY KEY REFERENCES games(id),
    turn INTEGER,
    year FLOAT,
    state JSONB  -- 完整的 CivState 结构
);

-- 每轮记录（追加）
CREATE TABLE turns (
    id SERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    turn INTEGER,
    year_start FLOAT,
    year_end FLOAT,
    player_input TEXT,
    llm_intent JSONB,           -- LLM①输出
    action_result JSONB,        -- 数学引擎输出
    narrative TEXT,              -- LLM②输出
    summary TEXT,               -- 一句话摘要
    state_before JSONB,         -- 行动前状态快照
    state_after JSONB,          -- 行动后状态快照
    domain_tags TEXT[],         -- 行动领域标签
    created_at TIMESTAMP
);

-- 中期摘要
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    turn_start INTEGER,
    turn_end INTEGER,
    year_start FLOAT,
    year_end FLOAT,
    content TEXT,               -- 摘要文本
    domain_frequencies JSONB,   -- 各领域行动频次
    created_at TIMESTAMP
);

-- 长期关键事件索引
CREATE TABLE landmarks (
    id SERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    turn INTEGER,
    year FLOAT,
    tags TEXT[],                -- 主题标签（可用 GIN 索引）
    title TEXT,
    summary TEXT,
    state_snapshot JSONB,
    created_at TIMESTAMP
);

-- 积累值时间序列
CREATE TABLE accumulations (
    id SERIAL PRIMARY KEY,
    game_id UUID REFERENCES games(id),
    turn INTEGER,
    values JSONB,              -- {academic, military, commercial, administrative, cultural}
    created_at TIMESTAMP
);

-- 索引
CREATE INDEX idx_turns_game_turn ON turns(game_id, turn DESC);
CREATE INDEX idx_summaries_game ON summaries(game_id, turn_end DESC);
CREATE INDEX idx_landmarks_game_tags ON landmarks USING GIN(game_id, tags);
CREATE INDEX idx_accumulations_game ON accumulations(game_id, turn DESC);
```

### 10.4 API 端点

```
POST   /api/game/new              -- 创建新游戏（选择模板）
GET    /api/game/{id}             -- 获取游戏状态
POST   /api/game/{id}/action      -- 提交行动（返回结果，叙事通过 WebSocket 流式推送）
GET    /api/game/{id}/menu        -- 获取当前可用行动菜单
GET    /api/game/{id}/history     -- 获取历史日志（分页）
POST   /api/game/{id}/save       -- 存档
GET    /api/game/saves            -- 列出存档
POST   /api/game/load/{save_id}  -- 读档
WS     /api/game/{id}/ws          -- WebSocket 连接（流式叙事）
```

### 10.5 一个回合的完整时序

```
1. 前端 POST /api/game/{id}/action { input: "推行均田制" }

2. 后端 action.py:
   a. 加载当前状态
   b. 调用 intent_parser.py → LLM① → 结构化意图 JSON
   c. 如果 is_knowledge_injection → 调用 knowledge_evaluator.py → LLM 评估
   d. 调用 action_resolver.py:
      - check_prerequisites → 满足/降级
      - friction.py → 成功率
      - 掷骰 → 结果档位
      - 查各模型 → 数值变动
      - passive_events.py → 被动事件
      - accumulation.py → 更新积累值
      - gameover.py → 检查是否 Game Over
   e. 调用 retriever.py → 检索相关历史
   f. 通过 WebSocket 调用 narrator.py → LLM② → 流式输出叙事
   g. 保存到 turns 表
   h. 更新 game_states
   i. 检查是否需要生成中期摘要（每 5 轮）
   j. 检查是否需要创建长期索引条目
   k. 返回 { state_changes, action_result, turn_info }

3. 前端通过 WebSocket 逐字显示叙事，同时更新状态面板
```

---

## 十一、UI 方向

### 11.1 风格：古典卷轴

整体视觉语言：羊皮纸质感 + 古典地图 + 史书排版。

**色彩基调：** 羊皮纸暖黄（#F4E4C1）为底，深棕（#3C2415）为文字，朱红（#8B2500）为重点标记，金色（#C5A55A）为装饰线条。

**字体：** 中文使用宋体/楷体系列作叙事字体，数据面板用等宽字体。

**布局概念：**

```
┌────────────────────────────────────────────────┐
│  顶栏：文明名 · 年份 · 王朝名                      │
├──────────────────────┬─────────────────────────┤
│                      │                         │
│   叙事卷轴区          │    状态面板              │
│   （主体区域）         │    ├── 物质基底          │
│                      │    ├── 生产关系          │
│   古典史书排版         │    ├── 上层建筑          │
│   LLM 叙事逐字显示    │    └── 社会信号          │
│                      │                         │
│   历史日志向上滚动     │    行动菜单              │
│                      │    （可折叠参考列表）      │
│                      │                         │
├──────────────────────┴─────────────────────────┤
│  底部输入栏：自然语言政令输入 + 执行按钮             │
└────────────────────────────────────────────────┘
```

### 11.2 叙事区设计

- 卷轴隐喻：新的叙事从下方展开，旧叙事向上卷起
- 叙事文字用楷体/宋体，配合淡墨色
- 数值变化以朱批风格显示在叙事旁边（而非独立弹窗）
- 关键事件（制度变更、战争、灾难）有特殊装饰边框

### 11.3 状态面板

- 折叠式设计，默认显示核心指标，展开查看详细维度
- 数值变化用箭头+颜色表示（上升=绿，下降=红，不变=灰）
- 玩家可在设置中配置哪些隐藏指标（如识字率、积累值）要显示

---

## 十二、MVP 范围与优先级

### 12.1 第一阶段：核心循环（4-6 周）

- [ ] 后端框架搭建（FastAPI + PostgreSQL + LLM 调用）
- [ ] 维度体系实现（四层状态结构）
- [ ] 数学引擎：社会摩擦模型 + 人口动态 + 稳定性
- [ ] LLM 管线：意图解析 + 叙事生成
- [ ] 前端：基础 UI（状态面板 + 叙事区 + 输入框）
- [ ] 1 个文明模板可玩

### 12.2 第二阶段：深度机制（4-6 周）

- [ ] 完整的生产关系系统（土地/劳动/提取）
- [ ] 宗教系统
- [ ] 治理效率衰减
- [ ] 知识注入管线
- [ ] 路径积累系统
- [ ] 行动菜单动态生成
- [ ] 可变时间跨度
- [ ] 被动事件系统
- [ ] 6 个文明模板全部实现

### 12.3 第三阶段：记忆与体验（3-4 周）

- [ ] 三层记忆系统完整实现
- [ ] Game Over 机制 + 文明终结报告
- [ ] 存档/读档系统
- [ ] UI 打磨（古典卷轴风格完整实现）
- [ ] 数值平衡调优

### 12.4 后续扩展（不在 MVP）

- 多文明并行与外交
- 文明碰撞（战争/贸易/文化交流的对手方）
- 更多文明模板（中美洲、南亚、东南亚）
- 玩家社区（分享文明历史记录）
- 多语言支持
