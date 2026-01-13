//! Bühlmann ZHL-16C decompression validation logic.

use dive_deco::{BuehlmannConfig, BuehlmannModel, Deco, DecoModel, DecoStageType, Gas};
use sha2::{Digest, Sha256};

use super::models::{DecoStop, GasMix, Segment, ValidateResponse};

/// Compute SHA256 hash of input string.
fn sha256_hex(s: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(s.as_bytes());
    let digest = hasher.finalize();
    format!("sha256:{}", hex::encode(digest))
}

/// Validation error types.
#[derive(Debug)]
pub enum ValidationError {
    NoSegments,
    InvalidGasFractions,
    GasFractionsExceedOne,
}

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoSegments => write!(f, "no segments provided"),
            Self::InvalidGasFractions => write!(f, "gas fractions must be between 0.0 and 1.0"),
            Self::GasFractionsExceedOne => write!(f, "gas fractions (O2 + He) exceed 1.0"),
        }
    }
}

/// Validate a dive profile and compute decompression status.
pub fn validate(
    segments: &[Segment],
    gas: &GasMix,
    gf_low: f64,
    gf_high: f64,
    input_json: &str,
) -> Result<ValidateResponse, ValidationError> {
    // Basic validation
    if segments.is_empty() {
        return Err(ValidationError::NoSegments);
    }
    if !(0.0..=1.0).contains(&gas.o2) || !(0.0..=1.0).contains(&gas.he) {
        return Err(ValidationError::InvalidGasFractions);
    }
    if gas.o2 + gas.he > 1.0 {
        return Err(ValidationError::GasFractionsExceedOne);
    }

    let input_hash = sha256_hex(input_json);

    // Compute basic metrics
    let max_depth_m = segments
        .iter()
        .map(|s| s.depth_m)
        .fold(0.0_f64, f64::max);

    let runtime_min: f64 = segments.iter().map(|s| s.duration_min).sum();

    // Convert gradient factors from fractions (0.0-1.0) to integers (0-100)
    let gf_low_int = (gf_low * 100.0).round() as u8;
    let gf_high_int = (gf_high * 100.0).round() as u8;

    // Configure Bühlmann model with gradient factors
    let config = BuehlmannConfig::new().gradient_factors(gf_low_int, gf_high_int);
    let mut model = BuehlmannModel::new(config);

    // Create gas mix
    let dive_gas = Gas::new(gas.o2, gas.he);

    // Record each segment (step takes depth in meters, duration in seconds)
    for seg in segments {
        let seconds = (seg.duration_min * 60.0).round() as usize;
        model.step(&seg.depth_m, &seconds, &dive_gas);
    }

    // Get ceiling (meters) - this is the depth we cannot ascend above
    let ceiling_m = model.ceiling();
    let deco_required = ceiling_m > 0.0;

    // Get NDL (no-deco limit in minutes) - only meaningful if not in deco
    let ndl_min: Option<u64> = if !deco_required {
        let ndl = model.ndl();
        // NDL returns Minutes::MAX for surface/shallow, cap at 999
        if ndl > 999 {
            Some(999)
        } else {
            Some(ndl as u64)
        }
    } else {
        None
    };

    // Calculate deco schedule and TTS
    let available_gases = vec![dive_gas];
    let Deco { deco_stages, tts } = model.deco(available_gases);

    // TTS is in seconds, convert to minutes
    let tts_min = tts as f64 / 60.0;

    // Extract deco stops (filter out ascent stages, keep only DecoStop)
    let stops: Vec<DecoStop> = deco_stages
        .iter()
        .filter(|stage| matches!(stage.stage_type, DecoStageType::DecoStop))
        .filter(|stage| stage.duration > 0)
        .map(|stage| DecoStop {
            depth_m: stage.start_depth,
            duration_min: stage.duration as f64 / 60.0,
        })
        .collect();

    Ok(ValidateResponse {
        tool: "diveops-deco-validate",
        tool_version: "0.2.0",
        model: "Bühlmann ZHL-16C",
        gf_low,
        gf_high,
        ceiling_m,
        tts_min,
        ndl_min,
        deco_required,
        stops,
        max_depth_m,
        runtime_min,
        input_hash,
        warnings: vec![],
        error: None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_no_deco_dive() {
        let segments = vec![
            Segment { depth_m: 18.0, duration_min: 30.0 },
        ];
        let gas = GasMix { o2: 0.21, he: 0.0 };

        let result = validate(&segments, &gas, 0.40, 0.85, "{}").unwrap();

        assert!(!result.deco_required);
        assert!(result.ndl_min.is_some());
        assert_eq!(result.max_depth_m, 18.0);
        assert_eq!(result.runtime_min, 30.0);
    }

    #[test]
    fn test_deco_dive() {
        let segments = vec![
            Segment { depth_m: 40.0, duration_min: 30.0 },
        ];
        let gas = GasMix { o2: 0.21, he: 0.0 };

        let result = validate(&segments, &gas, 0.40, 0.85, "{}").unwrap();

        assert!(result.deco_required);
        assert!(result.ndl_min.is_none());
        assert!(result.ceiling_m > 0.0);
        assert!(!result.stops.is_empty());
    }

    #[test]
    fn test_empty_segments_error() {
        let segments: Vec<Segment> = vec![];
        let gas = GasMix { o2: 0.21, he: 0.0 };

        let result = validate(&segments, &gas, 0.40, 0.85, "{}");
        assert!(matches!(result, Err(ValidationError::NoSegments)));
    }

    #[test]
    fn test_invalid_gas_fractions() {
        let segments = vec![Segment { depth_m: 18.0, duration_min: 10.0 }];
        let gas = GasMix { o2: 1.5, he: 0.0 };

        let result = validate(&segments, &gas, 0.40, 0.85, "{}");
        assert!(matches!(result, Err(ValidationError::InvalidGasFractions)));
    }

    #[test]
    fn test_gas_fractions_exceed_one() {
        let segments = vec![Segment { depth_m: 18.0, duration_min: 10.0 }];
        let gas = GasMix { o2: 0.6, he: 0.5 };

        let result = validate(&segments, &gas, 0.40, 0.85, "{}");
        assert!(matches!(result, Err(ValidationError::GasFractionsExceedOne)));
    }

    #[test]
    fn test_ean32() {
        let segments = vec![
            Segment { depth_m: 30.0, duration_min: 40.0 },
        ];
        let gas = GasMix { o2: 0.32, he: 0.0 };

        let result = validate(&segments, &gas, 0.40, 0.85, "{}").unwrap();

        // EAN32 at 30m for 40min should be close to NDL or just in deco
        assert_eq!(result.max_depth_m, 30.0);
        assert_eq!(result.runtime_min, 40.0);
    }

    #[test]
    fn test_input_hash() {
        let segments = vec![Segment { depth_m: 18.0, duration_min: 10.0 }];
        let gas = GasMix { o2: 0.21, he: 0.0 };

        let result = validate(&segments, &gas, 0.40, 0.85, r#"{"test": true}"#).unwrap();

        assert!(result.input_hash.starts_with("sha256:"));
        assert_eq!(result.input_hash.len(), 7 + 64); // "sha256:" + 64 hex chars
    }
}
