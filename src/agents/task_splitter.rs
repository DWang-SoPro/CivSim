use crate::llm::client::LLMClient;
use crate::schemas::task_splitter::{SubTask, TaskSplitterOutput};
use serde_json::Value;

/// TaskSplitter Agent - 将玩家指令拆分为多个子任务
/// 使用 qwen3.5-plus-2026-02-15 模型进行轻量级任务拆分
pub struct TaskSplitter {
    client: LLMClient,
}

impl TaskSplitter {
    pub fn new() -> Self {
        Self {
            client: LLMClient::new_qwen_splitter(),
        }
    }

    /// 分析玩家指令，拆分为子任务
    pub async fn split(
        &self,
        player_input: &str,
    ) -> Result<TaskSplitterOutput, Box<dyn std::error::Error + Send + Sync>> {
        // 如果指令很短，直接作为单任务处理
        if player_input.len() < 10 {
            return Ok(TaskSplitterOutput::single_task(player_input));
        }

        let prompt = format!(
            r##"你是一个任务拆分专家。分析玩家指令，判断是否需要拆分为多个独立子任务。

玩家指令：{}

## 拆分规则
1. **以下情况应拆分**：
   - 使用"和"、"并"、"同时"等连接词的复合指令
   - 明显包含多个不同领域的行动（如"发展农业和建立军队"）
   - 时间跨度大的多个目标（如"改进工具和建造宫殿"）

2. **以下情况不拆分**：
   - 单领域的细化描述（如"改进灌溉系统，增加农田面积"）
   - 同一目标的不同方面（如"训练士兵，购买武器"）
   - 简短的单一行动

3. **拆分原则**：
   - 最多拆分为 4 个子任务
   - 每个子任务应该是独立可执行的
   - 保持子任务的原始意图

## 输出格式
**如果是单任务**：
{{"is_multi_task": false, "subtasks": [{{"id": 1, "description": "任务描述", "original_text": "原始文本", "priority": 1}}], "split_reason": null}}

**如果是多任务**（示例）：
{{"is_multi_task": true, "subtasks": [{{"id": 1, "description": "发展农业技术", "original_text": "发展农业", "priority": 1}}, {{"id": 2, "description": "建立军事体系", "original_text": "建立军队", "priority": 2}}], "split_reason": "指令包含农业和军事两个独立领域"}}

只输出 JSON，不要解释。"##,
            player_input
        );

        let response = self.client.chat(&prompt).await
            .map_err(|e| format!("[TASK_SPLITTER] LLM 调用失败：{}", e))?;

        let json_str = extract_json_from_response(&response);
        let parsed: Value = serde_json::from_str(json_str)
            .map_err(|e| format!("[TASK_SPLITTER] JSON 解析失败：{}\n原始响应：{}", e, response))?;

        let is_multi_task = parsed.get("is_multi_task")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        let subtasks = parsed.get("subtasks")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .enumerate()
                    .filter_map(|(idx, v)| {
                        let description = v.get("description")?.as_str()?.to_string();
                        let original_text = v.get("original_text")?.as_str()?.to_string();
                        let priority = v.get("priority")?.as_i64()? as i32;
                        
                        Some(SubTask {
                            id: idx + 1,
                            description,
                            original_text,
                            priority,
                        })
                    })
                    .collect()
            })
            .unwrap_or_else(|| vec![SubTask {
                id: 1,
                description: player_input.to_string(),
                original_text: player_input.to_string(),
                priority: 1,
            }]);

        let split_reason = parsed.get("split_reason")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        eprintln!("[TASK_SPLITTER] ✅ 拆分完成 - 子任务数：{}", subtasks.len());

        Ok(TaskSplitterOutput {
            is_multi_task,
            subtasks,
            split_reason,
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
    fn test_splitter_creation() {
        let splitter = TaskSplitter::new();
        assert!(splitter.model_name().contains("qwen"));
    }
}
