// Tauri Commands - 前端与后端的交互接口

use crate::{
    pipeline::GamePipeline,
    state::CivState,
    storage::Storage,
};
use serde::{Deserialize, Serialize};
use tokio::sync::Mutex as AsyncMutex;
use std::sync::Arc;

/// 游戏状态管理
pub struct GameState {
    pub pipeline: GamePipeline,
    pub current_state: CivState,
    pub storage: Storage,
    pub conversation_history: Vec<ConversationTurn>,
    pub current_save_id: Option<i64>,
}

/// 对话回合记录
#[derive(Serialize, Deserialize, Clone)]
pub struct ConversationTurn {
    pub turn: i32,
    pub player_input: String,
    pub narrative: String,
    pub summary: String,
}

/// 回合结果（返回给前端）
#[derive(Serialize, Deserialize)]
pub struct TurnResultDto {
    pub narrative: String,
    pub summary: String,
    pub new_state: CivState,
    pub turn: i32,
}

/// 存档元数据
#[derive(Serialize, Deserialize)]
pub struct SaveMetadataDto {
    pub id: i64,
    pub name: String,
    pub created_at: String,
    pub updated_at: String,
}

/// 处理玩家输入指令
#[tauri::command]
pub async fn process_player_input(
    input: String,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<TurnResultDto, String> {
    let mut game_state = state.lock().await;
    
    // 计算当前回合数
    let turn = game_state.conversation_history.len() as i32 + 1;
    
    // 执行 Agent 流水线并更新状态
    let result = game_state.pipeline
        .process_turn(&input, &game_state.current_state, None)
        .await
        .map_err(|e| e.to_string())?;
    
    // 更新游戏状态 - 应用数值变化
    let mut new_state = game_state.current_state.clone();
    new_state.year += 5; // 每回合前进 5 年
    
    // 应用人口变化 (百分比变化)
    new_state.population = ((new_state.population as f64) * (1.0 + result.state_changes.population_change)) as i64;
    
    // 应用稳定性变化 (绝对值变化，限制在 0-100)
    new_state.stability = (new_state.stability + result.state_changes.stability_change).clamp(0, 100);
    
    // 应用统治力变化 (绝对值变化，限制在 0-100)
    new_state.authority = (new_state.authority + result.state_changes.authority_change).clamp(0, 100);
    
    // 应用科技进展 (百分比变化)
    new_state.tech_level += result.state_changes.tech_progress;
    
    // 应用领土变化 (绝对值变化)
    new_state.territory_size += result.state_changes.territory_change;
    
    // 确保数值在合理范围内
    new_state.population = new_state.population.max(0);
    new_state.territory_size = new_state.territory_size.max(0.0);
    new_state.tech_level = new_state.tech_level.max(0.0);
    
    // 记录对话历史
    let conv_turn = ConversationTurn {
        turn,
        player_input: input.clone(),
        narrative: result.narrative.clone(),
        summary: result.summary.clone(),
    };
    game_state.conversation_history.push(conv_turn);
    
    // 更新内存中的状态
    game_state.current_state = new_state.clone();
    
    Ok(TurnResultDto {
        narrative: result.narrative,
        summary: result.summary,
        new_state,
        turn,
    })
}

/// 获取当前游戏状态
#[tauri::command]
pub async fn get_current_state(
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<CivState, String> {
    let game_state = state.lock().await;
    Ok(game_state.current_state.clone())
}

/// 保存游戏（新存档）
#[tauri::command]
pub async fn save_game(
    name: String,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<i64, String> {
    let game_state = state.lock().await;
    
    let state_json = serde_json::to_string(&game_state.current_state)
        .map_err(|e| e.to_string())?;
    
    let history_json = serde_json::to_string(&game_state.conversation_history)
        .map_err(|e| e.to_string())?;
    
    game_state.storage
        .save_game(&name, &state_json, &history_json)
        .map_err(|e| e.to_string())
}

/// 覆盖保存游戏
#[tauri::command]
pub async fn overwrite_save(
    name: String,
    id: i64,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<(), String> {
    let game_state = state.lock().await;
    
    let state_json = serde_json::to_string(&game_state.current_state)
        .map_err(|e| e.to_string())?;
    
    let history_json = serde_json::to_string(&game_state.conversation_history)
        .map_err(|e| e.to_string())?;
    
    game_state.storage
        .update_save(id, &name, &state_json, &history_json)
        .map_err(|e| e.to_string())?;
    
    Ok(())
}

/// 加载游戏
#[tauri::command]
pub async fn load_game(
    id: i64,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<CivState, String> {
    let mut game_state = state.lock().await;
    
    let (state_json, history_json) = game_state.storage
        .load_game(id)
        .map_err(|e| e.to_string())?
        .ok_or("存档不存在")?;
    
    let civ_state: CivState = serde_json::from_str(&state_json)
        .map_err(|e| e.to_string())?;
    
    // 加载对话历史
    let history: Vec<ConversationTurn> = serde_json::from_str(&history_json).unwrap_or_default();
    game_state.conversation_history = history;
    game_state.current_save_id = Some(id);
    
    game_state.current_state = civ_state.clone();
    Ok(civ_state)
}

/// 列出所有存档
#[tauri::command]
pub async fn list_saves(
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<Vec<SaveMetadataDto>, String> {
    let game_state = state.lock().await;
    
    let saves = game_state.storage
        .list_saves()
        .map_err(|e| e.to_string())?;
    
    Ok(saves.into_iter().map(|s| SaveMetadataDto {
        id: s.id,
        name: s.name,
        created_at: s.created_at.to_string(),
        updated_at: s.updated_at.to_string(),
    }).collect())
}

/// 删除存档
#[tauri::command]
pub async fn delete_save(
    id: i64,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<(), String> {
    let game_state = state.lock().await;
    game_state.storage
        .delete_save(id)
        .map_err(|e| e.to_string())?;
    Ok(())
}

// ============================================================================
// Civilization Selection System
// ============================================================================

use crate::templates::{get_all_eras, get_all_locations, find_template};
use crate::llm::CivGenerator;

/// List all available eras
#[tauri::command]
pub async fn list_eras() -> Result<Vec<crate::templates::Era>, String> {
    Ok(get_all_eras().clone())
}

/// List all available locations
#[tauri::command]
pub async fn list_locations() -> Result<Vec<crate::templates::Location>, String> {
    Ok(get_all_locations().clone())
}

/// Check if a template exists for era+location
#[tauri::command]
pub async fn has_civ_template(era_id: String, location_id: String) -> Result<bool, String> {
    Ok(find_template(&era_id, &location_id).is_some())
}

/// Get a specific template by era+location
#[tauri::command]
pub async fn get_civ_template(
    era_id: String, 
    location_id: String,
    lang: String,
) -> Result<Option<crate::templates::CivTemplate>, String> {
    Ok(find_template(&era_id, &location_id).cloned())
}

/// Generate civilization via LLM (for non-template combinations)
#[tauri::command]
pub async fn generate_civilization(
    era_id: String,
    location_id: String,
) -> Result<crate::templates::GeneratedCivData, String> {
    // Find era and location
    let era = get_all_eras().iter().find(|e| e.id == era_id)
        .ok_or(format!("Era not found: {}", era_id))?;
    
    let location = get_all_locations().iter().find(|l| l.id == location_id)
        .ok_or(format!("Location not found: {}", location_id))?;
    
    // Generate via LLM
    let generator = CivGenerator::new();
    let result = generator.generate_civilization(era, location).await?;
    
    Ok(result)
}

/// Start a new game from a template
#[tauri::command]
pub async fn start_new_game_from_template(
    era_id: String,
    location_id: String,
    lang: String,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<CivState, String> {
    let template = find_template(&era_id, &location_id)
        .ok_or(format!("No template found for {} + {}", era_id, location_id))?;
    
    let new_state = CivState::from_template(template, &lang);
    
    let mut game_state = state.lock().await;
    game_state.current_state = new_state.clone();
    game_state.conversation_history = Vec::new();
    game_state.current_save_id = None;
    
    Ok(new_state)
}

/// Start a new game from generated civilization
#[tauri::command]
pub async fn start_new_game_from_generated(
    generated: crate::templates::GeneratedCivData,
    year: i32,
    lang: String,
    state: tauri::State<'_, Arc<AsyncMutex<GameState>>>,
) -> Result<CivState, String> {
    let new_state = CivState {
        year,
        civ_name: generated.civ_name.clone(),
        population: generated.initial_state.population,
        stability: generated.initial_state.stability,
        authority: generated.initial_state.authority,
        centralization: generated.initial_state.centralization,
        political_system: if lang == "zh" { "封建制".to_string() } else { "Feudalism".to_string() },
        economic_system: if lang == "zh" { "自然经济".to_string() } else { "Natural Economy".to_string() },
        territory_size: generated.initial_state.territory_size,
        tech_level: generated.initial_state.tech_level,
        biome_fertility: generated.initial_state.biome_fertility,
    };
    
    let mut game_state = state.lock().await;
    game_state.current_state = new_state.clone();
    game_state.conversation_history = Vec::new();
    game_state.current_save_id = None;
    
    Ok(new_state)
}
