// 游戏状态定义

use serde::{Deserialize, Serialize};

/// 文明状态
/// 文明状态
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct CivState {
    // 基本信息
    pub year: i32,
    pub civ_name: String,
    pub population: i64,
    
    // 政治
    pub stability: i32,      // 稳定性 0-100
    pub authority: i32,      // 统治力 0-100
    pub centralization: f64, // 中央集权 0-100
    pub political_system: String, // 政治制度：封建制、中央集权制、共和制等
    
    // 经济
    pub economic_system: String,  // 经济制度：自然经济、商品经济、计划经济等
    
    // 领土
    pub territory_size: f64,  // 领土面积
    
    // 科技
    pub tech_level: f64,      // 科技水平
    pub biome_fertility: f64, // 生态肥力
}

impl Default for CivState {
    fn default() -> Self {
        Self {
            year: -2000,
            civ_name: "Harappan League".to_string(),
            population: 50000,
            stability: 82,
            authority: 3,
            centralization: 35.0,
            political_system: "封建制".to_string(),
            economic_system: "自然经济".to_string(),
            territory_size: 1200.0,
            tech_level: 1.0,
            biome_fertility: 0.6,
        }
    }
}

impl CivState {
    /// Create a new CivState from a template
    pub fn from_template(template: &crate::templates::CivTemplate, lang: &str) -> Self {
        Self {
            year: template.era_id.split('_').nth(1)
                .and_then(|s| match s {
                    "bce" => template.era_id.split('_').next().and_then(|n: &str| n.parse::<i32>().ok()).map(|y| -y),
                    _ => None,
                })
                .unwrap_or(-2000),
            civ_name: if lang == "zh" {
                template.civ_name_zh.clone()
            } else {
                template.civ_name_en.clone()
            },
            population: template.initial_state.population,
            stability: template.initial_state.stability,
            authority: template.initial_state.authority,
            centralization: template.initial_state.centralization,
            political_system: if lang == "zh" { "封建制".to_string() } else { "Feudalism".to_string() },
            economic_system: if lang == "zh" { "自然经济".to_string() } else { "Natural Economy".to_string() },
            territory_size: template.initial_state.territory_size,
            tech_level: template.initial_state.tech_level,
            biome_fertility: template.initial_state.biome_fertility,
        }
    }
}
