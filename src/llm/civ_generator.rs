//! Civilization Generator using LLM
//!
//! Generates historically plausible civilization data for era+location combinations
//! that don't have pre-defined templates.

use crate::llm::client::LLMClient;
use crate::templates::presets::{Era, Location, GeneratedCivData};

pub struct CivGenerator {
    client: LLMClient,
}

impl CivGenerator {
    pub fn new() -> Self {
        Self {
            client: LLMClient::new_qwen(),
        }
    }
    
    /// Generate civilization data for a given era and location
    pub async fn generate_civilization(
        &self,
        era: &Era,
        location: &Location,
    ) -> Result<GeneratedCivData, String> {
        let prompt = self.build_prompt(era, location);
        
        let response = self.client.chat(&prompt).await
            .map_err(|e| format!("LLM error: {}", e))?;
        
        // Parse JSON from response
        let json_str = self.extract_json(&response)?;
        let mut generated: GeneratedCivData = serde_json::from_str(&json_str)
            .map_err(|e| format!("JSON parse error: {}", e))?;
        
        // Validate plausibility
        if generated.plausibility_score < 0.5 {
            return Err(format!(
                "Low plausibility score: {:.2}. This era+location combination may not be historically accurate.",
                generated.plausibility_score
            ));
        }
        
        // Validate and clamp values
        generated.initial_state.population = generated.initial_state.population.max(1000);
        generated.initial_state.stability = generated.initial_state.stability.clamp(0, 100);
        generated.initial_state.authority = generated.initial_state.authority.clamp(0, 100);
        generated.initial_state.centralization = generated.initial_state.centralization.clamp(0.0, 100.0);
        generated.initial_state.territory_size = generated.initial_state.territory_size.max(100.0);
        generated.initial_state.tech_level = generated.initial_state.tech_level.clamp(0.0, 3.0);
        generated.initial_state.biome_fertility = generated.initial_state.biome_fertility.clamp(0.0, 1.0);
        
        Ok(generated)
    }
    
    fn build_prompt(&self, era: &Era, location: &Location) -> String {
        format!(
            r#"You are a historical consultant for a civilization simulation game.

Generate historically accurate initial data for a civilization:

ERA: {} (Year: {} BCE/CE)
LOCATION: {}

Requirements:
1. Research or infer what civilization(s) existed in this era+location combination
2. If no major civilization existed, suggest a plausible emerging/declining one
3. Provide realistic population, stability, authority, and technology estimates
4. Population should be between 10,000 and 200,000 for ancient civilizations
5. Tech level: 0=Stone Age, 1=Bronze Age, 2=Iron Age, 3=Classical

Respond ONLY with valid JSON matching this schema:
{{
  "civ_name": "Civilization name in English",
  "historical_context": "Brief 1-2 sentence historical note",
  "initial_state": {{
    "population": <integer, typical range 10000-200000>,
    "stability": <integer 0-100, higher = more stable>,
    "authority": <integer 0-100, higher = more centralized power>,
    "centralization": <float 0-100, higher = more unified>,
    "territory_size": <float in square kilometers, typical 500-3000>,
    "tech_level": <float 0-3>,
    "biome_fertility": <float 0-1, override based on local conditions>
  }},
  "plausibility_score": <float 0-1, your confidence this is historically accurate>
}}

If this era+location combination is historically implausible, 
set plausibility_score below 0.5 and provide your best approximation."#,
            era.display_name_en, era.year.abs(), location.display_name_en
        )
    }
    
    fn extract_json(&self, response: &str) -> Result<String, String> {
        let response = response.trim();
        
        // Try to extract from markdown code block
        if let Some(start) = response.find("```json") {
            let rest = &response[start + 7..];
            if let Some(end) = rest.find("```") {
                return Ok(rest[..end].trim().to_string());
            }
        }
        
        // Try to find raw JSON
        if let Some(start) = response.find('{') {
            if let Some(end) = response.rfind('}') {
                return Ok(response[start..=end].to_string());
            }
        }
        
        Err("No valid JSON found in response".to_string())
    }
}

impl Default for CivGenerator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_generator_creation() {
        let _generator = CivGenerator::new();
    }
}
