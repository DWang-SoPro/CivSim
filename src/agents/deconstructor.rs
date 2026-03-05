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
        let client = LLMClient::new_qwen();
        Self {
            client: Arc::new(client),
        }
    }

    pub async fn process(&self, input: &str, state: &CivState) -> Result<DeconstructorOutput, LlmError> {
        // Build the prompt template
        let prompt = format!(r#"你是一个文明演化模拟器的意图分析专家。
分析玩家指令，提取其对文明四个维度的影响程度。

玩家指令：{}
当前文明状态：{{"year": {}, "civ_name": "{}", "population": {}, "stability": {}, "authority": {}}}

输出 JSON 格式：{{"dimensions": {{"admin": 0.0-1.0, "economy": 0.0-1.0, "culture": 0.0-1.0, "military": 0.0-1.0}}}}"#,
            input,
            state.year,
            state.civ_name,
            state.population,
            state.stability,
            state.authority
        );

        // Call LLM
        let response = self.client.chat(&prompt).await?;

        // Parse JSON response
        let parsed: Value = serde_json::from_str(&response)
            .map_err(|e| LlmError::Api(format!("JSON parse error: {}", e)))?;

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