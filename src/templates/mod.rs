//! Civilization Templates Module
//!
//! Provides pre-defined historical civilization templates and LLM generation
//! for creating historically accurate starting conditions.

pub mod presets;
pub mod compatibility;

pub use presets::{Era, Location, CivTemplate, CivStateInit, GeneratedCivData};
pub use compatibility::{
    has_template, find_template, get_all_eras, get_all_locations, 
    valid_locations_for_era, valid_eras_for_location,
};
