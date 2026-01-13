//! HTTP route handlers for deco validation API.

use axum::{
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};

use crate::AppState;

use super::models::{ValidateRequest, ValidateResponse};
use super::validator;

/// Create the deco router with all endpoints.
pub fn router() -> Router<AppState> {
    Router::new()
        .route("/health", get(health))
        .route("/validate", post(validate))
}

/// Health check for deco validation engine.
async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "ok",
        "service": "deco-validator",
        "version": "0.2.0",
        "model": "Bühlmann ZHL-16C"
    }))
}

/// Validate a dive profile and return decompression status.
async fn validate(
    Json(request): Json<ValidateRequest>,
) -> Result<Json<ValidateResponse>, (StatusCode, Json<serde_json::Value>)> {
    // Serialize request for input hash
    let input_json = serde_json::to_string(&request).unwrap_or_default();

    match validator::validate(
        &request.segments,
        &request.gas,
        request.gf_low,
        request.gf_high,
        &input_json,
    ) {
        Ok(response) => Ok(Json(response)),
        Err(e) => Err((
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "error": e.to_string(),
                "tool": "diveops-deco-validate",
                "tool_version": "0.2.0"
            })),
        )),
    }
}
