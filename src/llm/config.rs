// DashScope OpenAI compatible configuration
// Encapsulates base endpoint and model name mappings for DashScope

#[derive(Debug, Clone)]
pub struct DashScopeConfig {
    // DashScope compatible API base URL
    pub base_url: String,
    // Default model names used by the four agents
    pub qwen_plus: String,
    pub qwen_max: String,
    pub deepseek_chat: String,
    pub deepseek_reasoner: String,
}

impl DashScopeConfig {
    pub fn new() -> Self {
        DashScopeConfig {
            base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1".to_string(),
            qwen_plus: "qwen-plus".to_string(),
            qwen_max: "qwen-max".to_string(),
            deepseek_chat: "deepseek-chat".to_string(),
            deepseek_reasoner: "deepseek-reasoner".to_string(),
        }
    }
}
