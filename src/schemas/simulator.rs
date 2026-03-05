use serde::{Deserialize, Serialize};
use schemars::JsonSchema;

/// Output from the Simulator Agent, calculating numerical changes over 5 years
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct SimulatorOutput {
    /// Population change rate (-0.30 to 0.30)
    pub population_change: f64,
    /// Stability change (absolute value, -20 to 20)
    pub stability_change: i32,
    /// Authority change (absolute value, -15 to 15)
    pub authority_change: i32,
    /// Technology progress rate (0.0 to 0.30)
    pub tech_progress: f64,
    /// Territory change in km² (-500 to 500)
    /// Territory change in km² (-500 to 500)
    pub territory_change: f64,
    /// New political system (if changed)
    pub new_political_system: Option<String>,
    /// New economic system (if changed)
    pub new_economic_system: Option<String>,
    /// Triggered events list
    pub events: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simulator_output_serialization() {
        let output = SimulatorOutput {
            population_change: 0.12,
            stability_change: -5,
            authority_change: -2,
            tech_progress: 0.15,
            territory_change: 100.0,
            new_political_system: None,
            new_economic_system: None,
            events: vec!["Drought intensifies".to_string(), "Food shortage".to_string()],
        };

        let json = serde_json::to_string(&output).unwrap();
        assert!(json.contains("population_change"));
        assert!(json.contains("events"));
    }

    #[test]
    fn test_simulator_output_deserialization() {
        let json = r#"{"population_change":0.12,"stability_change":-5,"authority_change":-2,"tech_progress":0.15,"events":[]}"#;
        let output: SimulatorOutput = serde_json::from_str(json).unwrap();
        
        assert_eq!(output.population_change, 0.12);
        assert_eq!(output.stability_change, -5);
        assert!(output.events.is_empty());
    }
}
