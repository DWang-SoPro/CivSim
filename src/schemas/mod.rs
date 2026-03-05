// Schema 模块 - 所有数据结构定义

pub mod deconstructor;
pub mod auditor;
pub mod simulator;
pub mod chronicler;
pub mod task_splitter;

pub use deconstructor::{DeconstructorOutput, Dimensions};
pub use auditor::AuditorOutput;
pub use simulator::SimulatorOutput;
pub use chronicler::ChroniclerOutput;
pub use task_splitter::{TaskSplitterOutput, SubTask};

use serde::{Deserialize, Serialize};

/// 回合结果
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct TurnResult {
    pub narrative: String,
    pub summary: String,
}
