# 可调参数清单（Phase 5 数值平衡地图）

> 汇总 Phase 1–3 散落参数的**当前值**、含义与文件位置。  
> 改参后请跑对应 `tests/`；涉及粮食/国力时尤其注意锚点测试。

---

## 1. 国力三层 — `backend/engine/capacity.py` → `CapacityParams`

| 参数 | 当前值 | 含义 |
| --- | --- | --- |
| `BASE_CAPACITY` | `50.0` | 国力池基数 |
| `FOOD_FACTOR_MIN` / `MAX` | `0.3` / `2.0` | 粮食因子钳制 |
| `BUREAU_FACTOR_FLOOR` | `0.4` | `bureau_factor = 0.4 + 0.6×bureaucratization` |
| `GOV_FACTOR_FLOOR` | `0.4` | `gov_factor = 0.4 + 0.6×governance` |
| `W_AUTHORITY` | `0.30` | 传导权重：统治力 |
| `W_POWER_CONCENTRATION` | `0.25` | 权力集中度 |
| `W_ELITE_COHESION` | `0.15` | 精英凝聚 |
| `W_GOVERNANCE` | `0.15` | 治理效率 |
| `W_LEGITIMACY` | `0.15` | 合法性 |
| `POWER_CONC_AUTOCRACY` | `0.95` | 独裁集中度锚点 |
| `POWER_CONC_COUNCIL` | `0.35` | 议事会 |
| `POWER_CONC_BUREAU_FLOOR` / `SPAN` | `0.55` / `0.40` | 官僚：floor + span×bureaucratization |
| `POWER_CONC_OLIGARCHY_FLOOR` / `SPAN` | `0.40` / `0.50` | 寡头：floor + span×elite_cohesion |
| `SCALE_COST["small"]` | `1.0` | 小规模资源需求基数 |
| `SCALE_COST["medium"]` | `3.0` | 中 |
| `SCALE_COST["large"]` | `8.0` | 大 |
| `DILUTION_EXPONENT` | `1.5` | 超支稀释非线性指数 |
| `DILUTION_FLOOR` | `0.28` | 稀释系数下限（半拉子可见） |

**公式提醒：** `available = capacity × transmission`；`demand = scale_cost × (1 + gap × resistance)`；`dilution = max((available/total)^EXP, FLOOR)`。

---

## 2. 行动基础增量与规模倍率 — `backend/engine/action_resolver.py`

### 2.1 `_SCALE_EFFECT`

| scale | 倍率 |
| --- | --- |
| `small` | `0.5` |
| `medium` | `1.0` |
| `large` | `2.0` |

### 2.2 `_BASE_EFFECTS`（成功档 + medium 基准，再乘 scale/档位/稀释）

| domain | 主要键与值 |
| --- | --- |
| `economic` | stability +3.0, authority +1.5, population_pct +0.015, tech_agriculture +0.06, class_tension +0.02 |
| `military` | stability -1.5, authority +4.0, population_pct -0.02, class_tension +0.03 |
| `political` | stability +2.0, authority +5.0, bureaucratization +0.02, class_tension +0.025, elite_cohesion +0.02 |
| `cultural` | stability +3.0, authority +1.0, tech_knowledge +0.08, elite_cohesion +0.01 |
| `technology` | stability +1.0, authority +1.5, tech_engineering +0.1, tech_agriculture +0.02 |
| `composite` | stability +2.0, authority +2.0, class_tension +0.01 |

### 2.3 importance 阈值

| 常量 | 值 | 含义 |
| --- | --- | --- |
| `_MAJOR_STABILITY` | `8.0` | 稳定变化达此 → major 叙事 |
| `_MAJOR_AUTHORITY` | `8.0` | |
| `_MAJOR_POP_PCT` | `0.05` | 人口比例变化 |

### 2.4 掷骰随机因子（resolver 内）

`random_factor = 0.85 + 0.30 * rng.random()` → 约 **[0.85, 1.15]**

---

## 3. 社会摩擦 — `backend/engine/friction.py`

| 参数 / 表 | 当前值 | 含义 |
| --- | --- | --- |
| resistance 权重 | `0.3, 0.3, 0.2, 0.2` | (1-bureau), class_tension, (1-elite), religious_resistance |
| `P_base` 系数 | `0.8` | `0.8 × (1 - gap × resistance / A_norm)` |
| `A_norm` | `max(authority/20, 0.5)` | 归一化统治力 |
| `AUTHORITY_MOD` | autocracy 1.0 / council 0.8 / oligarchy 0.9 / bureaucracy 0.95 | 决策结构修正 |
| 积累修正上限 | `accumulation_mod ≤ 1.3` | `1 + min(acc,1)×0.3`（见 accumulation） |
| `EFFECT_MULTIPLIER` | GS 1.5 / S 1.0 / P 0.5 / F 0.0 / D **-1.0** | 档位效果 |

### `RESULT_TABLE`（P_success 下限 → 五档概率）

| P ≥ | great | success | partial | failure | disaster |
| --- | --- | --- | --- | --- | --- |
| 0.8 | 0.20 | 0.50 | 0.25 | 0.05 | 0.00 |
| 0.6 | 0.10 | 0.35 | 0.35 | 0.15 | 0.05 |
| 0.4 | 0.05 | 0.20 | 0.35 | 0.30 | 0.10 |
| 0.2 | 0.00 | 0.10 | 0.25 | 0.45 | 0.20 |
| 0.0 | 0.00 | 0.05 | 0.15 | 0.40 | 0.40 |

---

## 4. 粮食 — `backend/engine/food.py`

| 参数 | 当前值 | 含义 |
| --- | --- | --- |
| `YIELD_FACTOR` | `1.2 × 80000 / (1.5 × 650 × 0.855)` ≈ **115.16** | 西周开局盈余 1.2 反推 |
| `LABOR_EFFICIENCY` | free 1.0 / corvee 0.85 / serf 0.75 / slave 0.65 | 劳动加权 |
| 公式 | `(tech_agri × arable × labor_eff × YIELD_FACTOR × agri_mod) / pop` | arable = core × fertility |

### 模板 `agricultural_modifier` — `backend/templates/civilizations.py`

| template_id | 值 | 备注 |
| --- | --- | --- |
| `zhou` | `1.0`（字段默认） | 标定锚点 |
| `egypt` / `harappa` / `babylon` | `1.0` | 默认 |
| `sumer` | `0.90/0.74278…` ≈ **1.212** | 开局盈余校准 |
| `greece` | `0.90/0.61846…` ≈ **1.455** | 开局盈余校准 |

---

## 5. 人口增长 — `backend/engine/population.py`

年化 `base_growth_rate(food_surplus_ratio)`：

| 盈余率 | 年化增长率 |
| --- | --- | --- |
| &lt; 0.8 | `-0.02 × (0.8-ratio)/0.8`（饥荒，最多约 -2%） |
| &lt; 1.0 | `-0.005` |
| &lt; 1.2 | `+0.005` |
| &lt; 1.5 | `+0.01` |
| else | `+0.015` |

实际：`pop × (1 + growth × turn_years) + event_change`。

---

## 6. 稳定性 — `backend/engine/stability.py`

```
delta = 5×(food-1) + 3×(legit-0.5)
      - 10×max(class_tension-0.5,0)
      - 5×max(0.5-elite_cohesion,0)
      + action_stability_delta
```

钳制 stability ∈ **[0, 100]**。

---

## 7. 统治力 — `backend/engine/authority.py`

```
delta = action_authority_delta
      + 3×(elite_cohesion-0.5)
      - 5×max(class_tension-0.6,0)
      - (2 if bureaucratization < 0.2 else 0)
```

钳制 authority ∈ **[0, 100]**。

---

## 8. 治理效率 — `backend/engine/governance.py`

`E = bureaucratization × exp(-D_norm / V_norm)`  
`D_norm = frontier / max(core,1)`，`V_norm = (tech_eng + tech_know)/2`  
钳制 **[0, 1]**；`V_norm≤0` 且有边疆 → 0。

（无独立可调常数；调技术/领土/官僚即间接调。）

---

## 9. 积累值 — `backend/engine/accumulation.py`

| 参数 | 值 | 含义 |
| --- | --- | --- |
| 行动贡献 | `+0.2 × success_weight` | 每回合对映射域 |
| `SUCCESS_WEIGHT` | GS 1.5 / S 1.0 / P 0.5 / F 0.1 / D 0.0 | |
| 自然衰减 | `×0.95` / 回合 | |
| 学宫抵消 | academic 再 `×1.03`（若 `has_academy`） | |
| 官僚抵消 | administrative 再 `×1.02`（若 bureau &gt; 0.5） | |
| 成功率修正 | `1.0 + min(acc,1.0)×0.3`，封顶 1.3 | `accumulation_mod()` |

域映射 `ACTION_DOMAIN_TO_ACCUMULATION`：economic→commercial，political→administrative，military→military，cultural→cultural，technology→academic，composite→administrative。

---

## 10. 意图 / 拆分钳制 — LLM 侧

| 参数 | 文件 | 值 |
| --- | --- | --- |
| `TIME_ESTIMATE_MIN` / `MAX` | `intent_parser.py` | `0.1` / `20.0` |
| `SHORT_INPUT_THRESHOLD` | `task_splitter.py` | `10`（字符） |
| `MAX_SUBTASKS` | `task_splitter.py` | `4` |
| 前置失败年份钳制 | `action_resolver` | `min(years, 2.0)` |

---

## 11. 记忆系统阈值 — `backend/memory/*`

| 参数 | 文件 | 值 |
| --- | --- | --- |
| 近期回合数 | `recent.py` `RECENT_TURN_LIMIT` | `5` |
| 摘要间隔 | `summary.py` `SUMMARY_INTERVAL` | `5`（`turn % 5 == 0`） |
| 检索摘要条数 | `retriever` 默认 | `3` |
| 检索 landmark 条数 | `retriever` 默认 | `5` |
| `TECH_BREAKTHROUGH_DELTA` | `landmark.py` | `0.5` |
| `TERRITORY_CHANGE_RATIO` | `landmark.py` | `0.20` |
| `LEGITIMACY_CRISIS_THRESHOLD` | `landmark.py` | `0.3` |
| 稳定极端 | `stability < 20` 且下降 `≥15`，或关键词 | 见 `landmark.py` |

---

## 12. 识字率（CivState 方法）— `schemas.py`

`literacy = min(tech_knowledge × 0.15, 0.8) × knowledge_institution_coverage`

| 系数 | 值 |
| --- | --- |
| 知识→识字 | `0.15` |
| 识字上限 | `0.8` |

---

## 13. 阶级张力粗估 — `action_resolver.estimate_class_tension`

（当 `state.class_tension is None`）

```
oppression = serf×0.3 + slave×0.5
land_inequality: noble_estate 0.7 / landlord_tenant 0.8 / state_grant 0.4 /
                 clan_communal 0.2 / yeoman_smallhold 0.3
extraction_pressure = 0.3
raw = 0.3×oppression + 0.3×land_inequality + 0.2×extraction_pressure
```

`elite_cohesion` 缺省：**0.5**。

---

## 14. LLM / 运行配置 — `backend/config.py` + 环境变量

| 变量 | 默认 | 含义 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | （空） | 必需（LLM） |
| `LLM_BASE_URL` | `https://api.deepseek.com` | |
| `LLM_MODEL` | `deepseek-v4-flash` | |
| `LLM_MAX_RETRIES` | `3` | |
| `DATABASE_URL` | `postgresql://localhost/civsim` | 迁移用 |

客户端：`call_json` 开 thinking；`call_text_stream` 关 thinking。温度：叙事默认约 `0.8`（见 `client.call_text_stream`）。

---

## 15. Phase 5 调参建议优先级

1. **手感最大：** `DILUTION_FLOOR` / `SCALE_COST` / `BASE_CAPACITY`  
2. **成功率体感：** `RESULT_TABLE`、resistance 权重、`AUTHORITY_MOD`  
3. **长期曲线：** 积累 `0.95` 衰减、`0.2×weight` 贡献  
4. **文明差异：** 各模板初始状态 + `agricultural_modifier`  
5. **少动：** `YIELD_FACTOR`（一动全局粮食；优先动 modifier）

改完跑：`uv run pytest`；关键场景再跑 `--fullturn`。
