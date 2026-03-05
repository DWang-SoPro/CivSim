// 配置模块 - 从环境变量加载 LLM API 密钥等配置

use std::env;

/// LLM 配置结构体
pub struct LLMConfig {
    pub dashscope_api_key: String,
    pub dashscope_base_url: String,
    pub qwen_plus_model: String,
    pub qwen_max_model: String,
    pub deepseek_chat_model: String,
    pub deepseek_reasoner_model: String,
}

impl LLMConfig {
    /// 从环境变量加载配置
    pub fn from_env() -> Result<Self, String> {
        let dashscope_api_key = env::var("DASHSCOPE_API_KEY")
            .map_err(|_| "DASHSCOPE_API_KEY not set in .env file")?;
        
        Ok(Self {
            dashscope_api_key,
            dashscope_base_url: env::var("DASHSCOPE_BASE_URL")
                .unwrap_or_else(|_| "https://dashscope.aliyuncs.com/compatible-mode/v1".to_string()),
            qwen_plus_model: env::var("QWEN_PLUS_MODEL")
                .unwrap_or_else(|_| "qwen-plus".to_string()),
            qwen_max_model: env::var("QWEN_MAX_MODEL")
                .unwrap_or_else(|_| "qwen-max".to_string()),
            deepseek_chat_model: env::var("DEEPSEEK_CHAT_MODEL")
                .unwrap_or_else(|_| "deepseek-chat".to_string()),
            deepseek_reasoner_model: env::var("DEEPSEEK_REASONER_MODEL")
                .unwrap_or_else(|_| "deepseek-reasoner".to_string()),
        })
    }
}

/// 数据库配置
pub struct DatabaseConfig {
    pub path: String,
}

impl DatabaseConfig {
    pub fn from_env() -> Self {
        Self {
            path: env::var("DATABASE_PATH")
                .unwrap_or_else(|_| "./data/civsim.db".to_string()),
        }
    }
}

/// 服务器配置
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
}

impl ServerConfig {
    pub fn from_env() -> Self {
        Self {
            host: env::var("HOST")
                .unwrap_or_else(|_| "127.0.0.1".to_string()),
            port: env::var("PORT")
                .unwrap_or(|_| 5173u16),
        }
    }
}
