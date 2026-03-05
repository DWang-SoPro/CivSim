use serde::{Deserialize, Serialize};
use schemars::JsonSchema;

/// Four-dimensional impact matrix representing the effects on different aspects of civilization
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct Dimensions {
    /// Administrative impact (0.0-1.0)
    pub admin: f64,
    /// Economic impact (0.0-1.0)
    pub economy: f64,
    /// Cultural impact (0.0-1.0)
    pub culture: f64,
    /// Military impact (0.0-1.0)
    pub military: f64,
}

/// Output from the Deconstructor Agent, parsing player instructions into structured dimensions
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct DeconstructorOutput {
    pub dimensions: Dimensions,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_deconstructor_output_serialization() {
        let output = DeconstructorOutput {
            dimensions: Dimensions {
                admin: 0.5,
                economy: 0.7,
                culture: 0.3,
                military: 0.0,
            },
        };

        let json = serde_json::to_string(&output).unwrap();
        assert!(json.contains("admin"));
        assert!(json.contains("economy"));
    }

    #[test]
    fn test_deconstructor_output_deserialization() {
        let json = r#"{"dimensions":{"admin":0.5,"economy":0.7,"culture":0.3,"military":0.0}}"#;
        let output: DeconstructorOutput = serde_json::from_str(json).unwrap();
        
        assert_eq!(output.dimensions.admin, 0.5);
        assert_eq!(output.dimensions.economy, 0.7);
    }
}
