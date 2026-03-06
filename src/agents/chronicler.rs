use crate::llm::client::LLMClient;
use crate::schemas::{ChroniclerOutput, SimulatorOutput};
use crate::state::CivState;

/// Chronicler Agent - Converts numerical changes into narrative history
pub struct Chronicler {
    client: LLMClient,
}

impl Chronicler {
    /// Create a new Chronicler instance
    pub fn new() -> Self {
        Self {
            client: LLMClient::new_qwen(), // Qwen3.5-Plus：叙事能力
        }
    }

    /// Process simulator output and generate narrative with optimized parameters
    /// Uses temperature=0.6 for more consistent narrative quality
    pub async fn process(
        &self,
        player_input: &str,
        sim_output: &SimulatorOutput,
        state: &CivState,
        history_context: Option<&str>,
    ) -> Result<ChroniclerOutput, Box<dyn std::error::Error + Send + Sync>> {
        let prompt = self.build_prompt(player_input, sim_output, state, history_context);
        
        // Use optimized parameters for narrative generation:
        // - temperature=0.6: Lower than default (0.7) for more consistent output
        // - max_tokens=4096: Larger than default (2048) for longer narratives
        let narrative = self.client.chat_with_params(&prompt, 0.6, 4096).await?;
        
        // Extract first line as summary, fallback to default if empty
        let summary = narrative
            .lines()
            .find(|line| !line.trim().is_empty())
            .unwrap_or("历史事件已记录")
            .to_string();

        Ok(ChroniclerOutput {
            narrative,
            summary,
        })
    }


    pub fn model_name(&self) -> &str {
        self.client.model_name()
    }

    /// 获取 LLM 客户端引用（用于 Pipeline 生成综合叙事）
    pub fn client(&self) -> &LLMClient {
        &self.client
    }
    fn build_prompt(
        &self,
        player_input: &str,
        sim_output: &SimulatorOutput,
        state: &CivState,
        history_context: Option<&str>,
    ) -> String {
        let mut changes = String::new();
        if sim_output.population_change != 0.0 {
            changes.push_str(&format!("Population: {:.2}.\n", sim_output.population_change));
        }
        if sim_output.stability_change != 0 {
            changes.push_str(&format!("Stability: {}.\n", sim_output.stability_change));
        }
        if sim_output.authority_change != 0 {
            changes.push_str(&format!("Authority: {}.\n", sim_output.authority_change));
        }
        if sim_output.tech_progress != 0.0 {
            changes.push_str(&format!("Tech: {:.2}.\n", sim_output.tech_progress));
        }
        if !sim_output.events.is_empty() {
            changes.push_str(&format!("Events: {}.\n", sim_output.events.join(", ")));
        }
        if changes.is_empty() {
            changes = "No significant changes.".to_string();
        }

        let history = history_context.unwrap_or("No historical context.");

        format!(
            "你是一个古代文明的历史记录者。请**只用中文**撰写历史叙事，不要出现任何英文单词。\n\n玩家下达了指令：{}\n\n将以下数值变动结合玩家指令转化为生动的叙事文字。\n\n**当前状态**：\n- 年份：{}年\n- 文明：{}\n- 变动：{}\n- 历史背景：{}\n\n**写作要求**：\n1. 使用纯粹的中文，不要出现任何英文术语（如\"Population\"、\"Stability\"等）\n2. 用古代史官的口吻记录事件\n3. 将数值变化转化为具体的历史场景描写\n4. 输出 Markdown 格式的日志\n5. 段落之间要有逻辑连贯性\n\n**注意**：如果历史背景中提到之前的事件，请在叙事中体现前后的因果联系。",
            player_input, state.year, state.civ_name, changes, history
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chronicler_creation() {
        let _chronicler = Chronicler::new();
    }
}
