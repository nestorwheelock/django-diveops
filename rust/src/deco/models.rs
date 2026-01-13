//! Data types for decompression validation.

use serde::{Deserialize, Serialize};

/// Gas mix specification.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct GasMix {
    /// Oxygen fraction (0.0-1.0)
    pub o2: f64,
    /// Helium fraction (0.0-1.0)
    #[serde(default)]
    pub he: f64,
}

/// Dive segment at constant depth.
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Segment {
    /// Depth in meters
    pub depth_m: f64,
    /// Duration in minutes
    pub duration_min: f64,
}

/// Request payload for deco validation.
#[derive(Debug, Deserialize, Serialize)]
pub struct ValidateRequest {
    /// Dive profile segments
    pub segments: Vec<Segment>,
    /// Gas mix
    pub gas: GasMix,
    /// Gradient factor low (0.0-1.0)
    #[serde(default = "default_gf_low")]
    pub gf_low: f64,
    /// Gradient factor high (0.0-1.0)
    #[serde(default = "default_gf_high")]
    pub gf_high: f64,
}

fn default_gf_low() -> f64 {
    0.40
}

fn default_gf_high() -> f64 {
    0.85
}

/// Decompression stop information.
#[derive(Debug, Serialize)]
pub struct DecoStop {
    /// Stop depth in meters
    pub depth_m: f64,
    /// Stop duration in minutes
    pub duration_min: f64,
}

/// Response payload from deco validation.
#[derive(Debug, Serialize)]
pub struct ValidateResponse {
    /// Tool identifier
    pub tool: &'static str,
    /// Tool version
    pub tool_version: &'static str,
    /// Decompression model used
    pub model: &'static str,
    /// Gradient factor low used
    pub gf_low: f64,
    /// Gradient factor high used
    pub gf_high: f64,

    /// Current ceiling depth in meters
    pub ceiling_m: f64,
    /// Time to surface in minutes
    pub tts_min: f64,
    /// No-deco limit in minutes (None if deco required)
    pub ndl_min: Option<u64>,
    /// Whether decompression stops are required
    pub deco_required: bool,
    /// Decompression stops
    pub stops: Vec<DecoStop>,

    /// Maximum depth reached in meters
    pub max_depth_m: f64,
    /// Total runtime in minutes
    pub runtime_min: f64,
    /// SHA256 hash of input
    pub input_hash: String,

    /// Warning messages
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub warnings: Vec<String>,

    /// Error message if validation failed
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}
