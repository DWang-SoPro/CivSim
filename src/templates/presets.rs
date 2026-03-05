//! Pre-defined civilization templates and data structures

use serde::{Deserialize, Serialize};
use schemars::JsonSchema;
use lazy_static::lazy_static;

/// Era definition - historical period
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct Era {
    pub id: String,
    pub year: i32,
    pub display_name_zh: String,
    pub display_name_en: String,
    pub description_zh: String,
    pub description_en: String,
}

/// Location definition - geographic region
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct Location {
    pub id: String,
    pub display_name_zh: String,
    pub display_name_en: String,
    pub biome_fertility: f64,
}

/// Civilization template - pre-defined era+location combinations
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct CivTemplate {
    pub era_id: String,
    pub location_id: String,
    pub civ_name_zh: String,
    pub civ_name_en: String,
    pub initial_state: CivStateInit,
}

/// Initial state values for template
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct CivStateInit {
    pub population: i64,
    pub stability: i32,
    pub authority: i32,
    pub centralization: f64,
    pub territory_size: f64,
    pub tech_level: f64,
    pub biome_fertility: f64,
}

/// LLM-generated civilization data
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct GeneratedCivData {
    pub civ_name: String,
    pub historical_context: String,
    pub initial_state: CivStateInit,
    pub plausibility_score: f64,
}

// ============================================================================
// STATIC DATA: Eras
// ============================================================================

lazy_static! {
    pub static ref ERAS: Vec<Era> = vec![
        Era {
            id: "3000_bce".to_string(),
            year: -3000,
            display_name_zh: "公元前 3000 年".to_string(),
            display_name_en: "3000 BCE".to_string(),
            description_zh: "早期文明萌芽，城市国家初现".to_string(),
            description_en: "Dawn of civilization, emergence of city-states".to_string(),
        },
        Era {
            id: "2000_bce".to_string(),
            year: -2000,
            display_name_zh: "公元前 2000 年".to_string(),
            display_name_en: "2000 BCE".to_string(),
            description_zh: "青铜时代鼎盛，帝国雏形".to_string(),
            description_en: "Bronze Age peak, early empires forming".to_string(),
        },
        Era {
            id: "1000_bce".to_string(),
            year: -1000,
            display_name_zh: "公元前 1000 年".to_string(),
            display_name_en: "1000 BCE".to_string(),
            description_zh: "铁器时代开启，古典文明兴起".to_string(),
            description_en: "Iron Age begins, classical civilizations rise".to_string(),
        },
        Era {
            id: "500_bce".to_string(),
            year: -500,
            display_name_zh: "公元前 500 年".to_string(),
            display_name_en: "500 BCE".to_string(),
            description_zh: "轴心时代，哲学与帝国并存".to_string(),
            description_en: "Axial Age, philosophy and empires coexist".to_string(),
        },
    ];
}

// ============================================================================
// STATIC DATA: Locations
// ============================================================================

lazy_static! {
    pub static ref LOCATIONS: Vec<Location> = vec![
        Location {
            id: "mesopotamia".to_string(),
            display_name_zh: "美索不达米亚".to_string(),
            display_name_en: "Mesopotamia".to_string(),
            biome_fertility: 0.7,
        },
        Location {
            id: "indus_valley".to_string(),
            display_name_zh: "印度河流域".to_string(),
            display_name_en: "Indus Valley".to_string(),
            biome_fertility: 0.6,
        },
        Location {
            id: "nile_delta".to_string(),
            display_name_zh: "尼罗河三角洲".to_string(),
            display_name_en: "Nile Delta".to_string(),
            biome_fertility: 0.8,
        },
        Location {
            id: "yellow_river".to_string(),
            display_name_zh: "黄河流域".to_string(),
            display_name_en: "Yellow River".to_string(),
            biome_fertility: 0.65,
        },
        Location {
            id: "mediterranean".to_string(),
            display_name_zh: "地中海东岸".to_string(),
            display_name_en: "Eastern Mediterranean".to_string(),
            biome_fertility: 0.55,
        },
    ];
}

// ============================================================================
// STATIC DATA: Pre-defined Templates
// ============================================================================

lazy_static! {
    pub static ref TEMPLATES: Vec<CivTemplate> = vec![
        // 3000 BCE Mesopotamia - Sumerian city-states
        CivTemplate {
            era_id: "3000_bce".to_string(),
            location_id: "mesopotamia".to_string(),
            civ_name_zh: "苏美尔城邦联盟".to_string(),
            civ_name_en: "Sumerian City-States".to_string(),
            initial_state: CivStateInit {
                population: 30000,
                stability: 65,
                authority: 25,
                centralization: 20.0,
                territory_size: 500.0,
                tech_level: 0.8,
                biome_fertility: 0.7,
            },
        },
        // 3000 BCE Nile - Early Dynastic Egypt
        CivTemplate {
            era_id: "3000_bce".to_string(),
            location_id: "nile_delta".to_string(),
            civ_name_zh: "早王朝埃及".to_string(),
            civ_name_en: "Early Dynastic Egypt".to_string(),
            initial_state: CivStateInit {
                population: 40000,
                stability: 70,
                authority: 50,
                centralization: 45.0,
                territory_size: 800.0,
                tech_level: 0.85,
                biome_fertility: 0.8,
            },
        },
        // 2000 BCE Indus Valley - Harappan
        CivTemplate {
            era_id: "2000_bce".to_string(),
            location_id: "indus_valley".to_string(),
            civ_name_zh: "哈拉帕联盟".to_string(),
            civ_name_en: "Harappan League".to_string(),
            initial_state: CivStateInit {
                population: 50000,
                stability: 82,
                authority: 3,
                centralization: 35.0,
                territory_size: 1200.0,
                tech_level: 1.0,
                biome_fertility: 0.6,
            },
        },
        // 2000 BCE Mesopotamia - Old Babylonian
        CivTemplate {
            era_id: "2000_bce".to_string(),
            location_id: "mesopotamia".to_string(),
            civ_name_zh: "古巴比伦王国".to_string(),
            civ_name_en: "Old Babylonian Kingdom".to_string(),
            initial_state: CivStateInit {
                population: 60000,
                stability: 75,
                authority: 45,
                centralization: 55.0,
                territory_size: 1500.0,
                tech_level: 1.2,
                biome_fertility: 0.7,
            },
        },
        // 1000 BCE Yellow River - Western Zhou
        CivTemplate {
            era_id: "1000_bce".to_string(),
            location_id: "yellow_river".to_string(),
            civ_name_zh: "西周王朝".to_string(),
            civ_name_en: "Western Zhou Dynasty".to_string(),
            initial_state: CivStateInit {
                population: 80000,
                stability: 70,
                authority: 60,
                centralization: 40.0,
                territory_size: 2000.0,
                tech_level: 1.5,
                biome_fertility: 0.65,
            },
        },
        // 500 BCE Mediterranean - Classical Greece
        CivTemplate {
            era_id: "500_bce".to_string(),
            location_id: "mediterranean".to_string(),
            civ_name_zh: "古希腊城邦".to_string(),
            civ_name_en: "Classical Greek City-States".to_string(),
            initial_state: CivStateInit {
                population: 45000,
                stability: 60,
                authority: 20,
                centralization: 15.0,
                territory_size: 600.0,
                tech_level: 1.8,
                biome_fertility: 0.55,
            },
        },
    ];
}
