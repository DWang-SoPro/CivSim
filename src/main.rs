// 文明灵 (CivSim) - 主入口

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Arc;
use tokio::sync::Mutex as AsyncMutex;
use std::env;

mod agents;
mod llm;
mod math;
mod pipeline;
mod schemas;
mod state;
mod storage;
mod commands;
mod templates;

use commands::GameState;
use state::CivState;
use storage::Storage;
use pipeline::GamePipeline;

#[tokio::main]
async fn main() {
    // 加载 .env 环境变量
    dotenvy::dotenv().ok();
    
    eprintln!("[MAIN] DASHSCOPE_API_KEY loaded: {}", !env::var("DASHSCOPE_API_KEY").unwrap_or_default().is_empty());
    
    // 创建数据目录（如果不存在）
    let data_dir = std::path::Path::new("data");
    if !data_dir.exists() {
        std::fs::create_dir_all(data_dir).expect("Failed to create data directory");
    }
    
    // 初始化游戏状态
    let initial_state = CivState::default();
    let pipeline = GamePipeline::new_fast();
    let storage = Storage::new("data/civsim.db").expect("Failed to initialize storage");
    storage.init_schema().expect("Failed to initialize database schema");
    
    let game_state = GameState {
        pipeline,
        current_state: initial_state,
        storage,
        conversation_history: Vec::new(),
        current_save_id: None,
    };
    
    // 使用 Arc + AsyncMutex 包装状态
    let shared_state = Arc::new(AsyncMutex::new(game_state));
    
    // 启动 Tauri 应用
    tauri::Builder::default()
        .manage(shared_state)
        .invoke_handler(tauri::generate_handler![
            commands::process_player_input,
            commands::get_current_state,
            commands::save_game,
            commands::overwrite_save,
            commands::load_game,
            commands::list_saves,
            commands::delete_save,
            // Civilization selection commands
            commands::list_eras,
            commands::list_locations,
            commands::has_civ_template,
            commands::get_civ_template,
            commands::generate_civilization,
            commands::start_new_game_from_template,
            commands::start_new_game_from_generated,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
