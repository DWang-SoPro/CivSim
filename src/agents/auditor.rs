use crate::llm::client::LLMClient;
use crate::schemas::{DeconstructorOutput, AuditorOutput};
use crate::state::CivState;
use serde_json::Value;

pub struct Auditor {
    client: LLMClient,
}

impl Auditor {
    pub fn new() -> Self {
        Self {
            client: LLMClient::new_qwen(), // Qwen3.5-Plus：轻量级、快速
        }
    }
    
    /// Create a new Auditor with the fast (flash) model
    /// This is suitable for simple risk assessment where deep reasoning is not required
    pub fn new_fast() -> Self {
        Self {
            client: LLMClient::with_model("qwen3.5-flash-2026-02-23"),
        }
    }


    pub async fn process(
        &self,
        decon_output: &DeconstructorOutput,
        state: &CivState,
    ) -> Result<AuditorOutput, Box<dyn std::error::Error + Send + Sync>> {
        eprintln!("[AUDITOR] 📊 Starting cognitive gap analysis...");
        
        let prompt = format!(r##"你是一个文明演化模拟器的阻力审计专家。

你的任务是分析玩家指令与当前文明发展水平的差距，计算政策推行的成功率。
**重要原则：游戏需要保持适度的挑战性和可玩性，不要过度惩罚玩家。**

## 当前文明状态
- 年份：公元{}年
- 文明名称：{}
- 人口：{}
- 稳定性：{}/100
- 统治力：{}/100
- 科技水平：{:.1}（1=石器时代，2=青铜时代，3=铁器时代，4=工业时代）
- 中央集权：{:.0}/100

## 玩家指令的四维影响分析
- 行政影响：{:.2}（0=无影响，1=极大影响）
- 经济影响：{:.2}
- 文化影响：{:.2}
- 军事影响：{:.2}


## 你的任务

### 1. 认知差距评估（0-5）
**评分标准（请参考以下典型例子）：**

| 分数 | 含义 | 典型例子 |
|------|------|----------|
| 0 | 完全符合，毫无超前 | 石器时代：制作石器工具 |
| 1 | 小幅优化，自然演进 | 石器时代：改进石器打磨技术 |
| 2 | 轻微超前，可理解 | 青铜时代：改进灌溉系统；石器时代：简单农业尝试 |
| 3 | 明显超前，需教育 | 青铜时代：推行文字教育；铁器时代：建立行省制 |
| 4 | 高度超前，阻力大 | 青铜时代：发明印刷术；中世纪早期：火药武器 |
| 5 | 完全超越时代 | 石器时代：电力系统；青铜时代：蒸汽机 |

**评分指导：**
- 大部分合理指令应落在 **1-3 分** 区间
- 只有明显荒谬的指令才给 4-5 分
- 考虑文明的实际能力，不要过度悲观

### 2. 社会惯性系数（0.0-1.0）
**计算公式参考：**
```
基础阻力 = 0.5  // 任何社会都有一定惯性
集权修正 = (100 - 中央集权) / 200  // 0~0.5，集权低则阻力大
稳定修正 = (100 - 稳定性) / 200    // 0~0.5，不稳定则阻力大

社会惯性系数 = 基础阻力 + 集权修正 + 稳定修正
最终结果限制在 0.2 ~ 0.8 之间
```

**快速参考：**
- 集权 80+，稳定 80+ → 约 0.2-0.3（阻力很小）
- 集权 50，稳定 50 → 约 0.5（中等阻力）
- 集权 20，稳定 30 → 约 0.7-0.8（阻力很大）

### 3. 计算最终成功率
公式：P_success = B × (1 - (ΔC × R) / A)
- B = 基础成功率 0.8
- ΔC = 认知差距
- R = 社会惯性系数
- A = 统治力/20（归一化为 0-5）

## 输出要求（重要！）
**只输出纯 JSON，不要包含：**
- Markdown 代码块（不要用 ```json ... ```）
- 任何解释文字
- 换行符以外的空白字符

**参考示例：**
- 简单指令（改进农具）：{{"cognitive_gap": 1, "resistance_coefficient": 0.3, "analysis": "小幅改进现有技术", "warning": null}}
- 中等指令（推行新政）：{{"cognitive_gap": 2, "resistance_coefficient": 0.5, "analysis": "制度创新需要适应期", "warning": null}}
- 困难指令（超前发明）：{{"cognitive_gap": 4, "resistance_coefficient": 0.7, "analysis": "远超当前科技水平", "warning": "此政策可能引发混乱"}}

输出 JSON：
"##,
            state.year,
            state.civ_name,
            state.population,
            state.stability,
            state.authority,
            state.tech_level,
            state.centralization,
            decon_output.dimensions.admin,
            decon_output.dimensions.economy,
            decon_output.dimensions.culture,
            decon_output.dimensions.military
        );

        let response = self.client.chat(&prompt).await
            .map_err(|e| format!("[AUDITOR] AI 调用失败：{}", e))?;

        let json_str = extract_json_from_response(&response);

        let parsed: Value = serde_json::from_str(json_str)
            .map_err(|e| format!("[AUDITOR] JSON 解析失败：{}\n原始响应：{}", e, response))?;

        let cognitive_gap = parsed.get("cognitive_gap")
            .and_then(|v| v.as_i64())
            .map(|v| v as i32)
            .ok_or("[AUDITOR] Missing cognitive_gap")?;

        let resistance_coefficient = parsed.get("resistance_coefficient")
            .and_then(|v| v.as_f64())
            .ok_or("[AUDITOR] Missing resistance_coefficient")?;

        let warning = parsed.get("warning")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        let cognitive_gap = cognitive_gap.clamp(0, 5);
        let resistance_coefficient = resistance_coefficient.clamp(0.0, 1.0);

        let base_success_rate = 0.8;
        let authority_normalized = (state.authority as f64 / 20.0).max(0.1);
        let final_success_rate = base_success_rate * (1.0 - (cognitive_gap as f64 * resistance_coefficient / authority_normalized));
        let final_success_rate = final_success_rate.clamp(0.0, 1.0);

        eprintln!("[AUDITOR] ✅ Analysis complete - Success rate: {:.0}%", final_success_rate * 100.0);

        Ok(AuditorOutput {
            cognitive_gap,
            resistance_coefficient,
            base_success_rate,
            final_success_rate,
            warning,
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_json_from_response() {
        let markdown_response = r#"```json
{"cognitive_gap": 2, "resistance_coefficient": 0.5}
```"#;
        let extracted = extract_json_from_response(markdown_response);
        assert!(extracted.contains("cognitive_gap"));
        assert!(!extracted.contains("```"));
    }

    #[test]
    fn test_extract_plain_json() {
        let plain_json = r#"{"cognitive_gap": 2, "resistance_coefficient": 0.5}"#;
        let extracted = extract_json_from_response(plain_json);
        assert_eq!(extracted, plain_json);
    }
}
