//! Core mathematical models for civilization simulation.
//!
//! This module implements three fundamental models:
//! 1. Social Friction Model - calculates policy success rate
//! 2. Governance Efficiency Decay Model - calculates administrative efficiency
//! 3. Malthusian Carrying Capacity Model - calculates population limits

/// Social Friction Model
///
/// Calculates the success rate of a policy based on cognitive gap,
/// social resistance, and ruling authority.
///
/// Formula: P_success = B × (1 - (ΔC × R) / A)
///
/// # Arguments
/// * `cognitive_gap` - Cognitive gap between instruction and civilization level (0-5)
/// * `resistance_coefficient` - Social resistance coefficient (0.0-1.0)
/// * `authority` - Ruling authority/power (0-100)
/// * `base_success_rate` - Base success rate (default 0.8)
///
/// # Returns
/// Success rate between 0.0 and 1.0
pub fn calculate_success_rate(
    cognitive_gap: i32,
    resistance_coefficient: f64,
    authority: i32,
    base_success_rate: f64,
) -> f64 {
    let delta_c = cognitive_gap as f64;
    let a = authority as f64;
    
    // Avoid division by zero
    if a <= 0.0 {
        return 0.0;
    }
    
    let raw_success = base_success_rate * (1.0 - (delta_c * resistance_coefficient) / a);
    
    // Clamp between 0.0 and 1.0
    raw_success.max(0.0).min(1.0)
}

/// Governance Efficiency Decay Model
///
/// Calculates administrative efficiency based on centralization,
/// territory size, and technology level.
///
/// Formula: E = C × e^(-D/V)
///
/// # Arguments
/// * `centralization` - Centralization degree (0-100)
/// * `territory_size` - Territory size/distance
/// * `tech_level` - Transportation/communication technology level
///
/// # Returns
/// Governance efficiency value
pub fn governance_efficiency(
    centralization: f64,
    territory_size: f64,
    tech_level: f64,
) -> f64 {
    // Avoid division by zero
    if tech_level <= 0.0 {
        return 0.0;
    }
    
    // E = C × e^(-D/V)
    let efficiency = centralization * (-territory_size / tech_level).exp();
    
    // Ensure non-negative result
    efficiency.max(0.0)
}

/// Malthusian Carrying Capacity Model
///
/// Calculates the maximum population a civilization can support
/// based on technology level and ecological fertility.
///
/// Formula: P_limit = Tech × Bio × BaseFactor
///
/// # Arguments
/// * `tech_level` - Technology level (affects food production, storage, etc.)
/// * `biome_fertility` - Ecological fertility (0.0-2.0, where 1.0 is average)
///
/// # Returns
/// Maximum sustainable population
pub fn malthus_limit(tech_level: f64, biome_fertility: f64) -> f64 {
    // Base factor: represents fundamental carrying capacity per tech level unit
    const BASE_FACTOR: f64 = 10_000.0;
    
    tech_level * biome_fertility * BASE_FACTOR
}

/// Malthusian Crisis Checker
///
/// Checks if population exceeds carrying capacity and returns
/// appropriate crisis event if triggered.
///
/// # Arguments
/// * `current_population` - Current population
/// * `tech_level` - Technology level
/// * `biome_fertility` - Ecological fertility
///
/// # Returns
/// Option<String> containing crisis event name if population exceeds limit
pub fn check_malthus_crisis(
    current_population: i64,
    tech_level: f64,
    biome_fertility: f64,
) -> Option<String> {
    let limit = malthus_limit(tech_level, biome_fertility);
    let population = current_population as f64;
    
    if population > limit {
        // Determine severity based on how much population exceeds limit
        let ratio = population / limit;
        
        if ratio > 2.0 {
            Some("Catastrophic Famine".to_string())
        } else if ratio > 1.5 {
            Some("Severe Famine".to_string())
        } else {
            Some("Food Shortage".to_string())
        }
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ==================== Social Friction Model Tests ====================

    #[test]
    fn test_calculate_success_rate_normal_case() {
        let result = calculate_success_rate(2, 0.6, 50, 0.8);
        // Expected: 0.8 * (1 - (2 * 0.6) / 50) = 0.8 * (1 - 0.024) = 0.7808
        assert!((result - 0.7808).abs() < 0.0001);
    }

    #[test]
    fn test_calculate_success_rate_high_friction() {
        let result = calculate_success_rate(5, 1.0, 20, 0.8);
        // Expected: 0.8 * (1 - (5 * 1.0) / 20) = 0.8 * 0.75 = 0.6
        assert!((result - 0.6).abs() < 0.0001);
    }

    #[test]
    fn test_calculate_success_rate_clamp_zero() {
        let result = calculate_success_rate(5, 1.0, 1, 0.8);
        // Expected: 0.8 * (1 - 5) = -3.2 -> clamped to 0.0
        assert_eq!(result, 0.0);
    }

    #[test]
    fn test_calculate_success_rate_clamp_one() {
        let result = calculate_success_rate(0, 0.0, 100, 0.8);
        // Expected: 0.8 * (1 - 0) = 0.8
        assert!((result - 0.8).abs() < 0.0001);
    }

    #[test]
    fn test_calculate_success_rate_division_by_zero() {
        let result = calculate_success_rate(2, 0.6, 0, 0.8);
        // Should return 0.0 when authority is 0
        assert_eq!(result, 0.0);
    }

    #[test]
    fn test_calculate_success_rate_no_gap() {
        let result = calculate_success_rate(0, 0.5, 50, 0.8);
        // Expected: 0.8 * (1 - 0) = 0.8
        assert!((result - 0.8).abs() < 0.0001);
    }

    // ==================== Governance Efficiency Tests ====================

    #[test]
    fn test_governance_efficiency_basic() {
        let result = governance_efficiency(50.0, 1000.0, 1000.0);
        // E = 50 * e^(-1000/1000) = 50 * e^(-1) = 50 * 0.367879441... ≈ 18.39397...
        let expected = 50.0 * (-1.0_f64).exp();
        assert!((result - expected).abs() < 0.0001);
    }

    #[test]
    fn test_governance_efficiency_high_tech() {
        let result = governance_efficiency(50.0, 1000.0, 5000.0);
        // E = 50 * e^(-1000/5000) = 50 * e^(-0.2) ≈ 50 * 0.81873 ≈ 40.94
        let expected = 50.0 * (-0.2_f64).exp();
        assert!((result - expected).abs() < 0.0001);
    }

    #[test]
    fn test_governance_efficiency_low_tech() {
        let result = governance_efficiency(50.0, 1000.0, 100.0);
        // E = 50 * e^(-1000/100) = 50 * e^(-10) ≈ 50 * 0.0000454 ≈ 0.00227
        let expected = 50.0 * (-10.0_f64).exp();
        assert!((result - expected).abs() < 0.0001);
    }

    #[test]
    fn test_governance_efficiency_zero_tech() {
        let result = governance_efficiency(50.0, 1000.0, 0.0);
        // Should return 0.0 when tech level is 0
        assert_eq!(result, 0.0);
    }

    #[test]
    fn test_governance_efficiency_zero_territory() {
        let result = governance_efficiency(50.0, 0.0, 1000.0);
        // E = 50 * e^(0) = 50 * 1 = 50
        assert!((result - 50.0).abs() < 0.0001);
    }

    #[test]
    fn test_governance_efficiency_max_centralization() {
        let result = governance_efficiency(100.0, 500.0, 1000.0);
        // E = 100 * e^(-0.5) ≈ 100 * 0.6065 ≈ 60.65
        let expected = 100.0 * (-0.5_f64).exp();
        assert!((result - expected).abs() < 0.0001);
    }

    // ==================== Malthus Limit Tests ====================

    #[test]
    fn test_malthus_limit_basic() {
        let result = malthus_limit(1.0, 1.0);
        // Expected: 1.0 * 1.0 * 10000 = 10000
        assert_eq!(result, 10000.0);
    }

    #[test]
    fn test_malthus_limit_high_tech() {
        let result = malthus_limit(3.0, 1.0);
        // Expected: 3.0 * 1.0 * 10000 = 30000
        assert_eq!(result, 30000.0);
    }

    #[test]
    fn test_malthus_limit_fertile_land() {
        let result = malthus_limit(1.0, 2.0);
        // Expected: 1.0 * 2.0 * 10000 = 20000
        assert_eq!(result, 20000.0);
    }

    #[test]
    fn test_malthus_limit_infertile_land() {
        let result = malthus_limit(1.0, 0.5);
        // Expected: 1.0 * 0.5 * 10000 = 5000
        assert_eq!(result, 5000.0);
    }

    #[test]
    fn test_malthus_limit_combined() {
        let result = malthus_limit(2.5, 1.5);
        // Expected: 2.5 * 1.5 * 10000 = 37500
        assert_eq!(result, 37500.0);
    }

    // ==================== Malthus Crisis Tests ====================

    #[test]
    fn test_malthus_crisis_no_crisis() {
        // Population under limit
        let result = check_malthus_crisis(5000, 1.0, 1.0);
        // Limit = 10000, population = 5000, no crisis
        assert!(result.is_none());
    }

    #[test]
    fn test_malthus_crisis_at_limit() {
        // Population at exactly the limit
        let result = check_malthus_crisis(10000, 1.0, 1.0);
        // Limit = 10000, population = 10000, no crisis (not exceeding)
        assert!(result.is_none());
    }

    #[test]
    fn test_malthus_crisis_slight_excess() {
        // Population slightly exceeds limit
        let result = check_malthus_crisis(11000, 1.0, 1.0);
        // Limit = 10000, population = 11000, ratio = 1.1, Food Shortage
        assert_eq!(result, Some("Food Shortage".to_string()));
    }

    #[test]
    fn test_malthus_crisis_moderate_excess() {
        // Population moderately exceeds limit
        let result = check_malthus_crisis(16000, 1.0, 1.0);
        // Limit = 10000, population = 16000, ratio = 1.6, Severe Famine
        assert_eq!(result, Some("Severe Famine".to_string()));
    }

    #[test]
    fn test_malthus_crisis_severe_excess() {
        // Population severely exceeds limit
        let result = check_malthus_crisis(25000, 1.0, 1.0);
        // Limit = 10000, population = 25000, ratio = 2.5, Catastrophic Famine
        assert_eq!(result, Some("Catastrophic Famine".to_string()));
    }
}