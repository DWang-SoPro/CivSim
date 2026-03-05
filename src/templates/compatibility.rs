//! Template compatibility checking utilities

use crate::templates::presets::{TEMPLATES, ERAS, LOCATIONS};

/// Returns true if era+location has a pre-defined template
pub fn has_template(era_id: &str, location_id: &str) -> bool {
    TEMPLATES.iter().any(|t| t.era_id == era_id && t.location_id == location_id)
}

/// Returns valid locations for a given era
pub fn valid_locations_for_era(era_id: &str) -> Vec<&'static str> {
    TEMPLATES.iter()
        .filter(|t| t.era_id == era_id)
        .map(|t| t.location_id.as_str())
        .collect()
}

/// Returns valid eras for a given location
pub fn valid_eras_for_location(location_id: &str) -> Vec<&'static str> {
    TEMPLATES.iter()
        .filter(|t| t.location_id == location_id)
        .map(|t| t.era_id.as_str())
        .collect()
}

/// Find a template by era+location
pub fn find_template(era_id: &str, location_id: &str) -> Option<&'static crate::templates::presets::CivTemplate> {
    TEMPLATES.iter().find(|t| t.era_id == era_id && t.location_id == location_id)
}

/// Get all available eras
pub fn get_all_eras() -> &'static Vec<crate::templates::presets::Era> {
    &ERAS
}

/// Get all available locations
pub fn get_all_locations() -> &'static Vec<crate::templates::presets::Location> {
    &LOCATIONS
}

/// Get all templates
pub fn get_all_templates() -> &'static Vec<crate::templates::presets::CivTemplate> {
    &TEMPLATES
}
