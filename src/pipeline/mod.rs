// Agent Pipeline - 串联 4 个 Agent，支持并行子任务处理

use crate::{
    agents::{Deconstructor, Auditor, Simulator, Chronicler, TaskSplitter},
    schemas::{DeconstructorOutput, AuditorOutput, SimulatorOutput, SubTask},
    state::CivState,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Semaphore;

/// 流水线处理结果
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct TurnResult {
    pub narrative: String,
    pub summary: String,
    pub state_changes: StateChanges,
    /// 子任务详情（用于前端展示）
    pub subtask_results: Vec<SubTaskResult>,
}

/// 子任务处理结果
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct SubTaskResult {
    pub subtask: SubTask,
    pub success_rate: f64,
    pub narrative: String,
    pub state_changes: StateChanges,
}

/// 状态变化量
#[derive(Serialize, Deserialize, Clone, Debug, Default)]
pub struct StateChanges {
    pub population_change: f64,
    pub stability_change: i32,
    pub authority_change: i32,
    pub tech_progress: f64,
    pub territory_change: f64,
    pub new_political_system: Option<String>,
    pub new_economic_system: Option<String>,
}
impl StateChanges {
    /// 累加另一个状态变化
    pub fn add(&mut self, other: &StateChanges) {
        self.population_change += other.population_change;
        self.stability_change += other.stability_change;
        self.authority_change += other.authority_change;
        self.tech_progress += other.tech_progress;
        self.territory_change += other.territory_change;
        // 对于制度变更，后一个覆盖前一个（如果有的话）
        if other.new_political_system.is_some() {
            self.new_political_system = other.new_political_system.clone();
        }
        if other.new_economic_system.is_some() {
            self.new_economic_system = other.new_economic_system.clone();
        }
    }
}

/// 游戏流水线
pub struct GamePipeline {
    task_splitter: Arc<TaskSplitter>,
    deconstructor: Arc<Deconstructor>,
    auditor: Arc<Auditor>,
    simulator: Arc<Simulator>,
    chronicler: Arc<Chronicler>,
    /// 并发控制信号量（最多3个并发）
    semaphore: Arc<Semaphore>,
}

impl GamePipeline {
    pub fn new() -> Self {
        Self {
            task_splitter: Arc::new(TaskSplitter::new()),
            deconstructor: Arc::new(Deconstructor::new()),
            auditor: Arc::new(Auditor::new()),
            simulator: Arc::new(Simulator::new()),
            chronicler: Arc::new(Chronicler::new()),
            // 限制并发数为3，避免过多的API调用
            semaphore: Arc::new(Semaphore::new(3)),
        }
    }
    
    /// Create a new GamePipeline with fast (flash) models for Auditor and Simulator
    /// This reduces API costs and improves response time for simple calculations
    pub fn new_fast() -> Self {
        Self {
            task_splitter: Arc::new(TaskSplitter::new()),
            deconstructor: Arc::new(Deconstructor::new()),
            auditor: Arc::new(Auditor::new_fast()),  // Use flash model
            simulator: Arc::new(Simulator::new_fast()),  // Use flash model
            chronicler: Arc::new(Chronicler::new()),
            // 限制并发数为3，避免过多的API调用
            semaphore: Arc::new(Semaphore::new(3)),
        }
    }

    
    /// 处理一个回合（支持多任务并行）
    pub async fn process_turn(
        &self,
        player_input: &str,
        state: &CivState,
        history_context: Option<&str>,
    ) -> Result<TurnResult, Box<dyn std::error::Error + Send + Sync>> {
        eprintln!("[PIPELINE]  Starting turn processing...");
        
        // 1. TaskSplitter: 拆分玩家指令为子任务
        let split_output = self.task_splitter.split(player_input).await?;
        let subtask_count = split_output.subtasks.len();
        
        eprintln!(
            "[PIPELINE] 📋 Task split complete - {} subtask(s)",
            subtask_count
        );
        
        if let Some(ref reason) = split_output.split_reason {
            eprintln!("[PIPELINE]   Reason: {}", reason);
        }

        // 2. 并行处理所有子任务
        let mut subtask_futures: Vec<tokio::task::JoinHandle<Result<SubTaskResult, String>>> = Vec::new();
        
        
        // 将历史上下文转换为 String 以便在异步块中使用
        let history_context_owned: Option<String> = history_context.map(|s| s.to_string());
        
        // 2. 并行处理所有子任务
        
        for subtask in split_output.subtasks {
            let semaphore = Arc::clone(&self.semaphore);
            let deconstructor = Arc::clone(&self.deconstructor);
            let auditor = Arc::clone(&self.auditor);
            let simulator = Arc::clone(&self.simulator);
            let chronicler = Arc::clone(&self.chronicler);
            let state = state.clone();
            let history_context_clone = history_context_owned.clone();
            
            let future = tokio::spawn(async move {
                // 获取信号量许可（控制并发）
                let _permit = semaphore.acquire().await.map_err(|e| {
                    format!("[SUBTASK {}] Failed to acquire semaphore: {}", subtask.id, e)
                })?;
                
                eprintln!("[SUBTASK {}] 🔄 Processing: {}", subtask.id, subtask.description);
                
                // 2.1 Deconstructor 和 2.2 Auditor: 并行执行
                let decon_future = async {
                    deconstructor.process(&subtask.description, &state).await
                };
                
                // 先执行 Deconstructor，然后 Auditor 可以并行
                let decon_output = decon_future.await
                    .map_err(|e| format!("[SUBTASK {}] Deconstructor failed: {}", subtask.id, e))?;
                
                // 2.2 Auditor: 计算成功率
                let audit_output = auditor
                    .process(&decon_output, &state)
                    .await
                    .map_err(|e| format!("[SUBTASK {}] Auditor failed: {}", subtask.id, e))?;
                
                // 2.3 Simulator: 计算数值变动
                let sim_output = simulator
                    .process(&subtask.description, &decon_output, &audit_output, &state)
                    .await
                    .map_err(|e| format!("[SUBTASK {}] Simulator failed: {}", subtask.id, e))?;
                
                // 2.4 Chronicler: 生成子任务叙事
                let chronicler_output = chronicler
                    .process(&subtask.description, &sim_output, &state, history_context_clone.as_deref())
                    .await
                    .map_err(|e| format!("[SUBTASK {}] Chronicler failed: {}", subtask.id, e))?;
                
                eprintln!(
                    "[SUBTASK {}] ✅ Complete - Success rate: {:.0}%, Changes: pop={:+.1}%, stab={:+}",
                    subtask.id,
                    audit_output.final_success_rate * 100.0,
                    sim_output.population_change * 100.0,
                    sim_output.stability_change
                );
                
                Ok::<SubTaskResult, String>(SubTaskResult {
                    subtask,
                    success_rate: audit_output.final_success_rate,
                    narrative: chronicler_output.narrative,
                    state_changes: StateChanges {
                        population_change: sim_output.population_change,
                        stability_change: sim_output.stability_change,
                        authority_change: sim_output.authority_change,
                        tech_progress: sim_output.tech_progress,
                        territory_change: sim_output.territory_change,
                        new_political_system: sim_output.new_political_system.clone(),
                        new_economic_system: sim_output.new_economic_system.clone(),
                    },
                })
            });
            
            subtask_futures.push(future);
        }

        // 等待所有子任务完成
        let results: Vec<Result<SubTaskResult, String>> = futures::future::join_all(subtask_futures)
            .await
            .into_iter()
            .map(|res| res.map_err(|e| format!("Task panicked: {}", e)).and_then(|r| r))
            .collect();

        // 检查是否有失败的子任务
        let mut subtask_results = Vec::new();
        let mut has_error = false;
        
        for result in results {
            match result {
                Ok(subtask_result) => subtask_results.push(subtask_result),
                Err(e) => {
                    eprintln!("[PIPELINE] ❌ Subtask error: {}", e);
                    has_error = true;
                }
            }
        }

        if has_error && subtask_results.is_empty() {
            return Err("All subtasks failed".into());
        }


        // 3. 汇总所有子任务的状态变化
        let mut total_changes = StateChanges::default();
        for result in &subtask_results {
            total_changes.add(&result.state_changes);
        }

        eprintln!(
            "[PIPELINE] 📊 Total changes: pop={:+.1}%, stab={:+}, auth={:+}, tech={:+.2}",
            total_changes.population_change * 100.0,
            total_changes.stability_change,
            total_changes.authority_change,
            total_changes.tech_progress
        );

        // 4. 生成综合叙事
        let combined_narrative = self.generate_combined_narrative(&subtask_results,
            player_input
        ).await?;

        // 5. 生成摘要
        let summary = format!(
            "{}个子任务已执行。总体影响：人口{:+.1}%，稳定性{:+}，统治力{:+}",
            subtask_results.len(),
            total_changes.population_change * 100.0,
            total_changes.stability_change,
            total_changes.authority_change
        );

        eprintln!("[PIPELINE] ✅ Turn processing complete");

        Ok(TurnResult {
            narrative: combined_narrative,
            summary,
            state_changes: total_changes,
            subtask_results,
        })
    }

    /// 生成综合叙事（汇总所有子任务的结果）
    async fn generate_combined_narrative(
        &self,
        subtask_results: &[SubTaskResult],
        original_input: &str,
    ) -> Result<String, Box<dyn std::error::Error + Send + Sync>> {
        // 如果只有一个子任务，直接使用其叙事
        if subtask_results.len() == 1 {
            return Ok(subtask_results[0].narrative.clone());
        }

        // 构建子任务描述
        let mut subtask_descriptions = String::new();
        for (idx, result) in subtask_results.iter().enumerate() {
            subtask_descriptions.push_str(
            &format!(
                "\n### 任务 {}：{}\n- 成功率：{:.0}%\n- 结果：{}\n",
                idx + 1,
                result.subtask.original_text,
                result.success_rate * 100.0,
                result.narrative.chars().take(500).collect::<String>()
            ));
        }

        let prompt = format!(
            r##"你是一个历史记录者。玩家下达了复合指令，包含多个任务。请将各个任务的结果整合为一段连贯的历史叙事。

玩家原始指令：{}

各任务执行情况：{}

要求：
1. 将多个任务的结果融合为一段流畅的历史叙事
2. 体现任务之间的关联和影响
3. 使用 Markdown 格式
4. 突出每个任务的成败对文明的影响
5. 以宏观视角总结这个时期的整体变化

输出一段完整的历史记录（不要分点）："##,
            original_input,
            subtask_descriptions
        );

        // 使用 Chronicler 的客户端生成综合叙事
        let combined = self.chronicler.client().chat(&prompt).await
            .map_err(|e| format!("Failed to generate combined narrative: {}", e))?;

        Ok(combined)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_state_changes_add() {
        let mut changes1 = StateChanges {
            population_change: 0.1,
            stability_change: 5,
            authority_change: 3,
            tech_progress: 0.05,
            territory_change: 100.0,
            new_political_system: None,
            new_economic_system: None,
        };

        let changes2 = StateChanges {
            population_change: 0.05,
            stability_change: -2,
            authority_change: 1,
            tech_progress: 0.03,
            territory_change: 50.0,
            new_political_system: None,
            new_economic_system: None,
        };

        changes1.add(&changes2);

        assert_eq!(changes1.population_change, 0.15);
        assert_eq!(changes1.stability_change, 3);
        assert_eq!(changes1.authority_change, 4);
        assert_eq!(changes1.tech_progress, 0.08);
        assert_eq!(changes1.territory_change, 150.0);
    }
}
