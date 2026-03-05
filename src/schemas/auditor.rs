use serde::{Deserialize, Serialize};
use schemars::JsonSchema;

/// Output from the Auditor Agent, calculating success rate and resistance
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct AuditorOutput {
    /// Cognitive gap between instruction and civilization level (0-5)
    pub cognitive_gap: i32,
    /// Social resistance coefficient (0.0-1.0)
    pub resistance_coefficient: f64,
    /// Base success rate (default 0.8)
    pub base_success_rate: f64,
    /// Final calculated success rate
    pub final_success_rate: f64,
    /// Optional warning message
    pub warning: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_auditor_output_serialization() {
        let output = AuditorOutput {
            cognitive_gap: 2,
            resistance_coefficient: 0.6,
            base_success_rate: 0.8,
            final_success_rate: 0.44,
            warning: Some("High cognitive gap detected".to_string()),
        };

        let json = serde_json::to_string(&output).unwrap();
        assert!(json.contains("cognitive_gap"));
        assert!(json.contains("final_success_rate"));
    }

    #[test]
    fn test_auditor_output_deserialization() {
        let json = r#"{"cognitive_gap":2,"resistance_coefficient":0.6,"base_success_rate":0.8,"final_success_rate":0.44,"warning":null}"#;
        let output: AuditorOutput = serde_json::from_str(json).unwrap();
        
        assert_eq!(output.cognitive_gap, 2);
        assert_eq!(output.final_success_rate, 0.44);
        assert!(output.warning.is_none());
    }
}
