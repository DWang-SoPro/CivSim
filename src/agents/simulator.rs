use crate::llm::client::LLMClient;
use crate::schemas::{DeconstructorOutput, AuditorOutput, SimulatorOutput};
use crate::state::CivState;
use serde_json::Value;

pub struct Simulator {
    client: LLMClient,
}

impl Simulator {
    pub fn new() -> Self {
        Self {
            client: LLMClient::new_qwen(), // Qwen-Plus：数值计算性价比优
        }
    }
    
    /// Create a new Simulator with the fast (flash) model
    /// This is suitable for simple numerical calculations where creativity is less important
    pub fn new_fast() -> Self {
        Self {
            client: LLMClient::with_model("qwen3.5-flash-2026-02-23"),
        }
    }


    pub async fn process(
        &self,
        player_input: &str,
        decon_output: &DeconstructorOutput,
        audit: &AuditorOutput,
        state: &CivState,
    ) -> Result<SimulatorOutput, Box<dyn std::error::Error + Send + Sync>> {
        eprintln!("[SIMULATOR] 📈 Calculating numerical changes...");
        
        let prompt = format!(r##"你是一个文明演化模拟器的动力学推演专家。
你的任务是根据政策成功率、指令影响维度和当前文明状态，计算 5 年后的数值变化。

## 当前文明状态
- 年份：公元{}年
- 人口：{}
- 稳定性：{}/100
- 统治力：{}/100
- 科技水平：{:.2}
- 领土面积：{:.0} km²
- 生态肥力：{:.2}（0-1，越高越适合农业）
- 当前政治制度：{}
- 当前经济制度：{}

## 玩家指令影响维度

## 玩家指令影响维度
- 行政影响：{:.2}
- 经济影响：{:.2}
- 文化影响：{:.2}
- 军事影响：{:.2}

## 政策推行成功率
- 成功率：{:.0}%
- 认知差距：{}/5
- 社会阻力系数：{:.2}

## 你的任务
根据以上信息，计算 5 年后的各项数值变化。请遵循以下约束：

### 成功率与数值变化的关系（非常重要！）
上面的成功率表示政策推行的顺利程度，直接影响数值变化的方向和幅度：

- **高成功率 (>70%)**：政策推行顺利，应该带来**正面效果**
  - stability_change 应该为正数（社会稳定提升）
- **中等成功率 (40-70%)**：政策效果 mixed
  - 可能有正面也有负面效果
- **低成功率 (<40%)**：政策推行受阻，带来**负面效果**
  - stability_change 应该为负数（社会动荡）

### 数值变化约束
1. **人口变化率**（population_change）：范围：-0.30 到 +0.30
2. **稳定性变化**（stability_change）：范围：-20 到 +20
3. **统治力变化**（authority_change）：范围：-15 到 +15
4. **科技进展**（tech_progress）：范围：0.00 到 0.30
5. **领土变化**（territory_change）：范围：-500 到 +500 km²

**重要指导原则**：
- 成功的政变/改革应该提升稳定性（人民支持新秩序）
- 失败的政变/改革才会降低稳定性（混乱和反抗）

### 事件列表
如果触发了特殊事件，在 events 数组中添加事件名称。

## 输出要求（重要！）
**只输出纯 JSON，不要包含：**
- Markdown 代码块
- 任何解释文字

**JSON 字段说明：**
- population_change: 人口变化率 (-0.30 到 +0.30)
- stability_change: 稳定性变化 (-20 到 +20)
- authority_change: 统治力变化 (-15 到 +15)
- tech_progress: 科技进展 (0.00 到 0.30)
- territory_change: 领土变化 (-500 到 +500)
- new_political_system: 新政治制度（如"中央集权制"、"共和制"，如果政体变更则填写，否则为 null）
- new_economic_system: 新经济制度（如"商品经济"、"计划经济"，如果经济制度变更则填写，否则为 null）
- events: 事件列表（字符串数组）

**政体变更检测（关键！）：**
当前政治制度：{}
当前经济制度：{}

根据玩家指令和成功率，判断是否需要转变制度：

**政治制度转变规则：**
1. **向中央集权制转变**（关键词：集权、中央集权、削弱诸侯、废除分封、郡县制、天子亲政、收回权力）：
   - 当前是"封建制" + 指令含集权关键词 + 成功率 > 60% → 转变为"中央集权制"
   - 例如："天子派亲信接管各地诸侯国，成立中央集权制" → 确定转变为中央集权制

2. **向封建制转变**（关键词：分封、封邦建国、册封诸侯、裂土封王）：
   - 指令含分封关键词 + 成功率 > 50% → 转变为"封建制"

3. **向共和制转变**（关键词：共和、选举、议会、宪政、废除君主）：
   - 指令含共和关键词 + 成功率 > 70% → 转变为"共和制"

4. **向君主专制转变**（关键词：称帝、皇位、世袭、独裁、万岁）：
   - 指令含帝制关键词 + 成功率 > 60% → 转变为"君主专制"

**经济制度转变规则：**
1. **向商品经济转变**（关键词：重商、贸易、市场、商税、互通有无）：
   - 指令含商业关键词 + 成功率 > 60% → 转变为"商品经济"

2. **向计划经济转变**（关键词：计划、国有、配给、统购统销）：
   - 指令含计划关键词 + 成功率 > 60% → 转变为"计划经济"

3. **向自然经济转变**（关键词：均田、井田、自给自足、小农）：
   - 指令含自然经济关键词 + 成功率 > 60% → 转变为"自然经济"

**判断原则：**
- 成功率 < 40%：制度变更失败，维持原制度
- 成功率 40-60%：制度部分变更，可改为过渡形态或维持原制度
- 只有明确的关键词匹配 + 足够高的成功率，才设置 new_political_system 或 new_economic_system
- 如果指令不涉及制度变更，这两个字段必须为 null

**常见转变示例：**
- "废除诸侯，设立郡县" + 成功率75% → new_political_system: "中央集权制"
- "天子派亲信接管诸侯国" + 成功率70% → new_political_system: "中央集权制"
- "发展商业，降低关税" + 成功率65% → new_economic_system: "商品经济"
如果玩家指令涉及以下关键词，请判断是否发生政体变更：
- "政变"、"革命"、"改制" → 可能从"封建制"变为"中央集权制"
- "共和"、"民主" → 可能建立"共和制"
- "帝制"、"称帝" → 可能建立"君主专制"

**正确示例：**
{{"population_change": 0.05, "stability_change": 3, "authority_change": 2, "tech_progress": 0.08, "territory_change": 0, "new_political_system": null, "new_economic_system": null, "events": []}}

**政体变更示例：**
{{"population_change": 0.02, "stability_change": -5, "authority_change": 10, "tech_progress": 0.05, "territory_change": 0, "new_political_system": "中央集权制", "new_economic_system": null, "events": ["政变成功", "旧贵族被清洗"]}}

输出 JSON：
"##,
            state.year,
            state.population,
            state.stability,
            state.authority,
            state.tech_level,
            state.territory_size,
            state.biome_fertility,
            state.political_system,
            state.economic_system,
            decon_output.dimensions.admin,
            decon_output.dimensions.economy,
            decon_output.dimensions.culture,
            decon_output.dimensions.military,
            audit.final_success_rate * 100.0,
            audit.cognitive_gap,
            audit.resistance_coefficient,
            state.political_system,
            state.economic_system
        );

        let response = self.client.chat(&prompt).await
            .map_err(|e| format!("[SIMULATOR] AI 调用失败：{}", e))?;

        let json_str = extract_json_from_response(&response);
        let parsed: Value = serde_json::from_str(json_str)
            .map_err(|e| format!("[SIMULATOR] JSON 解析失败：{}", e))?;

        let mut population_change = parsed.get("population_change").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let mut stability_change = parsed.get("stability_change").and_then(|v| v.as_i64()).map(|v| v as i32).unwrap_or(0);
        let mut authority_change = parsed.get("authority_change").and_then(|v| v.as_i64()).map(|v| v as i32).unwrap_or(0);
        let mut tech_progress = parsed.get("tech_progress").and_then(|v| v.as_f64()).unwrap_or(0.0);
        let mut territory_change = parsed.get("territory_change").and_then(|v| v.as_f64()).unwrap_or(0.0);

        population_change = population_change.clamp(-0.30, 0.30);
        stability_change = stability_change.clamp(-20, 20);
        authority_change = authority_change.clamp(-15, 15);
        tech_progress = tech_progress.clamp(0.0, 0.30);
        territory_change = territory_change.clamp(-500.0, 500.0);

        // 根据成功率缩放数值变化（代码层保护）
        // 高成功率: 数值变化幅度保持，低成功率: 数值变化向负面方向调整
        let success_modifier = (audit.final_success_rate - 0.5) * 2.0; // 将 0-1 映射到 -1 到 +1
        if success_modifier > 0.0 {
            // 成功: 提升正面效果，减轻负面效果
            if stability_change > 0 {
                stability_change = (stability_change as f64 * (1.0 + success_modifier * 0.5)) as i32;
            } else {
                stability_change = (stability_change as f64 * (1.0 - success_modifier * 0.5)) as i32;
            }
            if authority_change > 0 {
                authority_change = (authority_change as f64 * (1.0 + success_modifier * 0.5)) as i32;
            } else {
                authority_change = (authority_change as f64 * (1.0 - success_modifier * 0.5)) as i32;
            }
        } else if success_modifier < 0.0 {
            // 失败: 削弱正面效果，增强负面效果
            let failure_factor = -success_modifier; // 转为正数
            if stability_change > 0 {
                stability_change = (stability_change as f64 * (1.0 - failure_factor * 0.7)) as i32;
            } else {
                stability_change = (stability_change as f64 * (1.0 + failure_factor * 0.7)) as i32;
            }
            if authority_change > 0 {
                authority_change = (authority_change as f64 * (1.0 - failure_factor * 0.7)) as i32;
            } else {
                authority_change = (authority_change as f64 * (1.0 + failure_factor * 0.7)) as i32;
            }
        }
        
        // 重新限制范围
        stability_change = stability_change.clamp(-20, 20);
        authority_change = authority_change.clamp(-15, 15);

        let events = parsed.get("events")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
            .unwrap_or_default();
        
        // 代码层制度校正（方案C）
        let mut new_political_system = parsed.get("new_political_system")
            .and_then(|v| v.as_str().map(String::from));
        let mut new_economic_system = parsed.get("new_economic_system")
            .and_then(|v| v.as_str().map(String::from));
        
        // 强制校正：根据关键词判断制度变更
        let input_lower = player_input.to_lowercase();
        let current_political = state.political_system.as_str();
        let success_rate = audit.final_success_rate;
        
        // 政治制度强制校正
        if success_rate > 0.5 {
            if input_lower.contains("集权") || input_lower.contains("中央集权") || 
               input_lower.contains("削弱诸侯") || input_lower.contains("废除分封") ||
               input_lower.contains("郡县") || input_lower.contains("接管诸侯") ||
               input_lower.contains("收回权力") || input_lower.contains("天子亲政") {
                if current_political == "封建制" || current_political == "分封制" {
                    new_political_system = Some("中央集权制".to_string());
                    eprintln!("[SIMULATOR] 制度校正：封建制 → 中央集权制");
                }
            } else if input_lower.contains("分封") || input_lower.contains("封邦建国") ||
                      input_lower.contains("册封诸侯") || input_lower.contains("裂土封王") {
                new_political_system = Some("封建制".to_string());
                eprintln!("[SIMULATOR] 制度校正：→ 封建制");
            } else if input_lower.contains("共和") || input_lower.contains("选举") ||
                      input_lower.contains("议会") || input_lower.contains("宪政") {
                if success_rate > 0.65 {
                    new_political_system = Some("共和制".to_string());
                    eprintln!("[SIMULATOR] 制度校正：→ 共和制");
                }
            } else if input_lower.contains("称帝") || input_lower.contains("皇帝") ||
                      input_lower.contains("皇位") || input_lower.contains("世袭独裁") {
                if success_rate > 0.55 {
                    new_political_system = Some("君主专制".to_string());
                    eprintln!("[SIMULATOR] 制度校正：→ 君主专制");
                }
            }
        }
        
        // 经济制度强制校正
        if success_rate > 0.5 {
            if input_lower.contains("重商") || input_lower.contains("贸易") || 
               input_lower.contains("市场") || input_lower.contains("商税") ||
               input_lower.contains("商业") || input_lower.contains("互通有无") {
                new_economic_system = Some("商品经济".to_string());
                eprintln!("[SIMULATOR] 制度校正：→ 商品经济");
            } else if input_lower.contains("计划") || input_lower.contains("国有") ||
                      input_lower.contains("配给") || input_lower.contains("统购统销") {
                new_economic_system = Some("计划经济".to_string());
                eprintln!("[SIMULATOR] 制度校正：→ 计划经济");
            } else if input_lower.contains("均田") || input_lower.contains("井田") ||
                      input_lower.contains("自给自足") || input_lower.contains("小农") {
                new_economic_system = Some("自然经济".to_string());
                eprintln!("[SIMULATOR] 制度校正：→ 自然经济");
            }
        }

        eprintln!("[SIMULATOR] Calculation complete - Population: {:+.1}%, Stability: {:+}, Territory: {:+} km²", 
                  population_change * 100.0, stability_change, territory_change);

        eprintln!("[SIMULATOR] ✅ Calculation complete - Population: {:+.1}%, Stability: {:+}, Territory: {:+} km²", 
                  population_change * 100.0, stability_change, territory_change);

        Ok(SimulatorOutput {
            population_change,
            stability_change,
            authority_change,
            tech_progress,
            territory_change,
            new_political_system,
            new_economic_system,
            events,
        })
    }

    pub fn model_name(&self) -> &str {
        self.client.model_name()
    }
}

fn extract_json_from_response(response: &str) -> &str {
    if let Some(start) = response.find("```json") {
        let content_start = start + 7;
        if let Some(end) = response[content_start..].find("```") {
            return response[content_start..content_start + end].trim();
        }
    }
    if let Some(start) = response.find("```") {
        let content_start = start + 3;
        if let Some(end) = response[content_start..].find("```") {
            return response[content_start..content_start + end].trim();
        }
    }
    response.trim()
}
