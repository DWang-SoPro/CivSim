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

    /// Process simulator output and generate narrative
    pub async fn process(
        &self,
        player_input: &str,
        sim_output: &SimulatorOutput,
        state: &CivState,
        history_context: Option<&str>,
    ) -> Result<ChroniclerOutput, Box<dyn std::error::Error + Send + Sync>> {
        let prompt = self.build_prompt(player_input, sim_output, state, history_context);
        let narrative = self.client.chat(&prompt).await?;
        
        let summary = narrative
            .lines()
            .next()
            .unwrap_or("No summary available")
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
            "你是一个古代文明的历史记录者。\n玩家下达了指令：{}\n将以下数值变动结合玩家指令转化为生动的叙事文字。\n\n年份：{}\n文明：{}\n变动：{}\n历史背景：{}\n\n输出 Markdown 格式的日志。",
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
