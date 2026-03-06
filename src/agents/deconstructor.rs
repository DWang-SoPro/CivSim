use std::sync::Arc;
use serde_json::Value;

use crate::llm::client::{LLMClient, LlmError};
use crate::schemas::deconstructor::{DeconstructorOutput, Dimensions};
use crate::state::CivState;

pub struct Deconstructor {
    client: Arc<LLMClient>,
}

impl Deconstructor {
    pub fn new() -> Self {
        let client = LLMClient::new_qwen(); // Qwen3.5-Plus：更稳定的 JSON 输出
        Self {
            client: Arc::new(client),
        }
    }

    pub async fn process(&self, input: &str, state: &CivState) -> Result<DeconstructorOutput, LlmError> {
        // Build the prompt template
        let prompt = format!(r##"你是一个文明演化模拟器的意图分析专家。
分析玩家指令，提取其对文明四个维度的影响程度。

玩家指令：{}
当前文明状态：{{"year": {}, "civ_name": "{}", "population": {}, "stability": {}, "authority": {}}}

**重要：只输出纯 JSON，不要包含 markdown 代码块标记（```），不要包含任何解释文字。**

输出必须是如下格式的纯 JSON：
{{"dimensions": {{"admin": 0.5, "economy": 0.3, "culture": 0.2, "military": 0.4}}}}

维度说明：
- admin: 行政影响（0.0-1.0，如官僚改革、法律制定）
- economy: 经济影响（0.0-1.0，如贸易、农业、税收）
- culture: 文化影响（0.0-1.0，如教育、宗教、艺术）
- military: 军事影响（0.0-1.0，如战争、征兵、防御）"##,
            input,
            state.year,
            state.civ_name,
            state.population,
            state.stability,
            state.authority
        );

        // Call LLM
        let response = self.client.chat(&prompt).await?;
        eprintln!("[DECONSTRUCTOR] Raw response (first 300 chars): {}", &response[..response.len().min(300)]);
        
        // Extract JSON from response (handle markdown code blocks)
        let json_str = extract_json_from_response(&response);
        
        if json_str.is_empty() {
            return Err(LlmError::Api("Empty response from LLM".to_string()));
        }

        // Parse JSON response
        let parsed: Value = serde_json::from_str(json_str)
            .map_err(|e| LlmError::Api(format!("JSON parse error: {} - Response: {}", e, &response[..response.len().min(200)])))?;
        // Extract dimensions
        let dimensions = parsed.get("dimensions")
            .ok_or_else(|| LlmError::Api("Missing 'dimensions' field in response".to_string()))?;

        let admin = dimensions.get("admin")
            .and_then(|v: &serde_json::Value| v.as_f64())
            .ok_or_else(|| LlmError::Api("Invalid 'admin' value".to_string()))?;

        let economy = dimensions.get("economy")
            .and_then(|v: &serde_json::Value| v.as_f64())
            .ok_or_else(|| LlmError::Api("Invalid 'economy' value".to_string()))?;

        let culture = dimensions.get("culture")
            .and_then(|v: &serde_json::Value| v.as_f64())
            .ok_or_else(|| LlmError::Api("Invalid 'culture' value".to_string()))?;

        let military = dimensions.get("military")
            .and_then(|v: &serde_json::Value| v.as_f64())
            .ok_or_else(|| LlmError::Api("Invalid 'military' value".to_string()))?;

        let output = DeconstructorOutput {
            dimensions: Dimensions {
                admin,
                economy,
                culture,
                military,
            },
        };

        Ok(output)
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

    #[test]
    fn test_deconstructor_creation() {
        let deconstructor = Deconstructor::new();
        assert!(deconstructor.client.model_name().contains("qwen"));
    }

    #[test]
    fn test_deconstructor_output_parsing() {
        // Test parsing a valid JSON response
        let json_response = r#"{"dimensions":{"admin":0.5,"economy":0.7,"culture":0.3,"military":0.2}}"#;
        let parsed: serde_json::Value = serde_json::from_str(json_response).unwrap();
        
        let dimensions = parsed.get("dimensions")
            .expect("Missing 'dimensions' field");
        
        let admin = dimensions.get("admin")
            .and_then(|v: &serde_json::Value| v.as_f64())
            .expect("Invalid 'admin' value");
        
        assert_eq!(admin, 0.5);
        assert_eq!(dimensions.get("economy").and_then(|v: &serde_json::Value| v.as_f64()).unwrap(), 0.7);
        assert_eq!(dimensions.get("culture").and_then(|v: &serde_json::Value| v.as_f64()).unwrap(), 0.3);
        assert_eq!(dimensions.get("military").and_then(|v: &serde_json::Value| v.as_f64()).unwrap(), 0.2);
    }

    #[test]
    fn test_deconstructor_output_validation() {
        // Test that DeconstructorOutput can be properly constructed
        let output = DeconstructorOutput {
            dimensions: Dimensions {
                admin: 0.5,
                economy: 0.7,
                culture: 0.3,
                military: 0.2,
            },
        };
        
        assert_eq!(output.dimensions.admin, 0.5);
        assert_eq!(output.dimensions.economy, 0.7);
        assert_eq!(output.dimensions.culture, 0.3);
        assert_eq!(output.dimensions.military, 0.2);
    }
}