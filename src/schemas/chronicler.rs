use serde::{Deserialize, Serialize};
use schemars::JsonSchema;

/// Output from the Chronicler Agent, converting numerical changes into narrative
#[derive(JsonSchema, Serialize, Deserialize, Clone, Debug)]
pub struct ChroniclerOutput {
    /// Markdown formatted narrative log
    pub narrative: String,
    /// Brief summary
    pub summary: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chronicler_output_serialization() {
        let output = ChroniclerOutput {
            narrative: "# Year -2000\n\nThe harvest was bountiful...".to_string(),
            summary: "Good harvest, population grows".to_string(),
        };

        let json = serde_json::to_string(&output).unwrap();
        assert!(json.contains("narrative"));
        assert!(json.contains("summary"));
    }

    #[test]
    fn test_chronicler_output_deserialization() {
        let json = r##"{"narrative":"# Test\nNarrative text","summary":"Summary text"}"##;
        let output: ChroniclerOutput = serde_json::from_str(json).unwrap();
        
        assert!(output.narrative.contains("Test"));
        assert_eq!(output.summary, "Summary text");
    }
}
