use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// 子任务定义
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct SubTask {
    /// 子任务ID
    pub id: usize,
    /// 子任务描述（用于后续Agent处理）
    pub description: String,
    /// 子任务原始文本（用于显示）
    pub original_text: String,
    /// 子任务优先级（影响执行顺序）
    pub priority: i32,
}

/// TaskSplitter 输出 - 将玩家指令拆分为多个子任务
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct TaskSplitterOutput {
    /// 是否包含多个任务
    pub is_multi_task: bool,
    /// 子任务列表
    pub subtasks: Vec<SubTask>,
    /// 拆分理由（用于调试）
    pub split_reason: Option<String>,
}

impl TaskSplitterOutput {
    /// 创建单任务输出（无需拆分）
    pub fn single_task(original_input: &str) -> Self {
        Self {
            is_multi_task: false,
            subtasks: vec![SubTask {
                id: 1,
                description: original_input.to_string(),
                original_text: original_input.to_string(),
                priority: 1,
            }],
            split_reason: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_task() {
        let output = TaskSplitterOutput::single_task("发展农业");
        assert!(!output.is_multi_task);
        assert_eq!(output.subtasks.len(), 1);
        assert_eq!(output.subtasks[0].description, "发展农业");
    }

    #[test]
    fn test_multi_task_serialization() {
        let output = TaskSplitterOutput {
            is_multi_task: true,
            subtasks: vec![
                SubTask {
                    id: 1,
                    description: "发展农业".to_string(),
                    original_text: "发展农业".to_string(),
                    priority: 1,
                },
                SubTask {
                    id: 2,
                    description: "建立军队".to_string(),
                    original_text: "建立军队".to_string(),
                    priority: 2,
                },
            ],
            split_reason: Some("指令包含两个独立任务".to_string()),
        };

        let json = serde_json::to_string(&output).unwrap();
        assert!(json.contains("is_multi_task"));
        assert!(json.contains("subtasks"));
    }
}
