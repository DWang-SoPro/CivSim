use std::fmt;
use std::error::Error as StdError;
use std::time::Duration;

use async_openai::Client;
use async_openai::config::OpenAIConfig;
use async_openai::types::{CreateChatCompletionRequestArgs, ChatCompletionRequestMessage};
use std::env;
use tokio::time::timeout;

#[derive(Debug)]
pub enum LlmError {
    Timeout,
    Api(String),
}

impl fmt::Display for LlmError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            LlmError::Timeout => write!(f, "LLM request timed out"),
            LlmError::Api(msg) => write!(f, "LLM API error: {}", msg),
        }
    }
}

impl StdError for LlmError {}

pub struct LLMClient {
    client: Client<OpenAIConfig>,
    model: String,
}


impl LLMClient {
    /// Qwen3.5-Flash-2026-02-23 - 用于任务拆分（轻量级、快速）
    pub fn new_qwen_splitter() -> Self {
        let config = OpenAIConfig::new()
            .with_api_base("https://dashscope.aliyuncs.com/compatible-mode/v1")
            .with_api_key(env::var("DASHSCOPE_API_KEY").unwrap_or_default());
        
        eprintln!("INFO: TaskSplitter client initialized with model: qwen3.5-flash-2026-02-23");
        
        let client = Client::with_config(config);
        LLMClient { client, model: "qwen3.5-flash-2026-02-23".to_string() }
    }

    /// Qwen3.5-Plus - 平衡性能和成本
    pub fn new_qwen() -> Self {
        let config = OpenAIConfig::new()
            .with_api_base("https://dashscope.aliyuncs.com/compatible-mode/v1")
            .with_api_key(env::var("DASHSCOPE_API_KEY").unwrap_or_default());
        
        eprintln!("INFO: Qwen client initialized with model: qwen3.5-plus");
        
        let client = Client::with_config(config);
        LLMClient { client, model: "qwen3.5-plus".to_string() }
    }

    /// Qwen3-Max - 2026 最新旗舰，推理能力 SOTA（快照版）
    pub fn new_qwen3_max() -> Self {
        let config = OpenAIConfig::new()
            .with_api_base("https://dashscope.aliyuncs.com/compatible-mode/v1")
            .with_api_key(env::var("DASHSCOPE_API_KEY").unwrap_or_default());
        
        eprintln!("INFO: Qwen3-Max client initialized with model: qwen3-max-2026-01-23 (snapshot)");
        
        let client = Client::with_config(config);
        LLMClient { client, model: "qwen3-max-2026-01-23".to_string() }
    }

    /// Qwen-Max - 上一代旗舰（兼容旧代码）
    #[deprecated(note = "Use new_qwen3_max() instead for better performance")]
    pub fn new_qwen_max() -> Self {
        let config = OpenAIConfig::new()
            .with_api_base("https://dashscope.aliyuncs.com/compatible-mode/v1")
            .with_api_key(env::var("DASHSCOPE_API_KEY").unwrap_or_default());
        
        eprintln!("INFO: Qwen-Max client initialized with model: qwen-max");
        
        let client = Client::with_config(config);
        LLMClient { client, model: "qwen-max".to_string() }
    }

    /// DeepSeek-V3.2 - 深度推理模型（已弃用，太慢）
    #[deprecated(note = "Use new_qwen3_max() instead - DeepSeek is too slow")]
    pub fn new_deepseek() -> Self {
        let config = OpenAIConfig::new()
            .with_api_base("https://dashscope.aliyuncs.com/compatible-mode/v1")
            .with_api_key(env::var("DASHSCOPE_API_KEY").unwrap_or_default());
        
        eprintln!("INFO: DeepSeek client initialized with model: deepseek-v3.2");
        
        let client = Client::with_config(config);
        LLMClient { client, model: "deepseek-v3.2".to_string() }
    }

    pub fn model_name(&self) -> &str { &self.model }

    pub async fn chat(&self, prompt: &str) -> Result<String, LlmError> {
        let agent_name = std::panic::Location::caller().file();
        eprintln!("[{}] Sending request to model: {}", agent_name, self.model);
        
        let mut last_error = String::new();
        for attempt in 1..=3 {
            eprintln!("[{}] Attempt {}/3", agent_name, attempt);
            
            let req = CreateChatCompletionRequestArgs::default()
                .model(&self.model)
                .messages(vec![ChatCompletionRequestMessage::User(
                    async_openai::types::ChatCompletionRequestUserMessage {
                        content: async_openai::types::ChatCompletionRequestUserMessageContent::Text(prompt.to_string()),
                        name: None,
                    },
                )])
                .temperature(0.7)
                .max_tokens(2048u16)
                .build()
                .map_err(|e| LlmError::Api(format!("Request build error: {}", e)))?;

            let chat = self.client.chat();
            let fut = chat.create(req);
            
            eprintln!("[{}] Waiting for response (120s timeout)...", agent_name);
            match timeout(Duration::from_secs(120), fut).await {
                Ok(Ok(r)) => {
                    eprintln!("[{}] ✅ Response received", agent_name);
                    let text = r
                        .choices
                        .get(0)
                        .and_then(|c| c.message.content.as_ref())
                        .cloned()
                        .unwrap_or_else(|| "".to_string());
                    
                    if text.is_empty() {
                        eprintln!("[{}] ⚠️ Empty response, retrying...", agent_name);
                        last_error = "Empty response".to_string();
                        tokio::time::sleep(Duration::from_secs(2)).await;
                        continue;
                    }
                    
                    eprintln!("[{}] Response length: {} chars", agent_name, text.len());
                    return Ok(text);
                },
                Ok(Err(e)) => {
                    let err_msg = format!("API error: {}", e);
                    eprintln!("[{}] ❌ {}", agent_name, err_msg);
                    last_error = err_msg;
                    if e.to_string().contains("rate_limit") || e.to_string().contains("429") {
                        eprintln!("[{}] Rate limited, waiting 10s...", agent_name);
                        tokio::time::sleep(Duration::from_secs(10)).await;
                    } else {
                        tokio::time::sleep(Duration::from_secs(2)).await;
                    }
                },
                Err(_) => {
                    eprintln!("[{}] ⏰ Timeout after 120s", agent_name);
                    last_error = "Request timeout".to_string();
                    tokio::time::sleep(Duration::from_secs(2)).await;
                }
            }
        }
        
        Err(LlmError::Api(format!("All retry attempts failed: {}", last_error)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_llm_client_creation() {
        let client = LLMClient::new_qwen();
        assert_eq!(client.model_name(), "qwen3.5-plus");
    }
}
