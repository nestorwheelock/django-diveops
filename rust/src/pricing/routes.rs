//! HTTP route handlers for pricing API.

use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use uuid::Uuid;

use crate::AppState;

use super::calculators::{allocate_shared_costs, calculate_totals, EquipmentRentalInput, PricingLineInput};
use super::queries;
use super::requests::{
    AllocateSharedCostsRequest, CalculateBoatCostRequest, CalculateGasFillsRequest,
    CalculateTotalsRequest, ResolvePricingRequest,
};
use super::responses::{
    AllocationResponse, BoatCostResponse, GasFillResponse,
    PricingErrorResponse, PricingResolutionResponse, PricingTotalsResponse,
};
use super::services::{self, PricingError};

/// Create the pricing router with all endpoints
pub fn router() -> Router<AppState> {
    Router::new()
        .route("/health", get(health))
        .route("/allocate", post(allocate))
        .route("/totals", post(totals))
        .route("/boat-cost", post(boat_cost))
        .route("/gas-fills", post(gas_fills))
        .route("/resolve", post(resolve))
}

/// Health check for pricing engine
async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "ok",
        "service": "pricing-engine",
        "version": "1.0.0"
    }))
}

/// Allocate shared costs among divers
async fn allocate(
    Json(request): Json<AllocateSharedCostsRequest>,
) -> Json<AllocationResponse> {
    let result = allocate_shared_costs(
        request.shared_total,
        request.diver_count,
        &request.currency,
    );

    Json(AllocationResponse {
        per_diver: result.per_diver,
        amounts: result.amounts,
    })
}

/// Calculate pricing totals from lines.
///
/// NOTE: This endpoint is currently unused by Django. Benchmarks show that for pure
/// calculations without DB access, Python is faster due to HTTP round-trip overhead
/// (~1.3ms vs 0.003ms). Django performs totals calculations locally.
///
/// Keeping this endpoint for potential future use:
/// - Direct API calls from mobile app or other clients
/// - Batch operations where multiple calculations justify HTTP overhead
/// - Future optimizations (request batching, connection pooling)
async fn totals(
    Json(request): Json<CalculateTotalsRequest>,
) -> Json<PricingTotalsResponse> {
    // Convert request types to calculator types
    let lines: Vec<PricingLineInput> = request
        .lines
        .into_iter()
        .map(|l| PricingLineInput {
            key: l.key,
            allocation: l.allocation,
            shop_cost_amount: l.shop_cost_amount,
            customer_charge_amount: l.customer_charge_amount,
        })
        .collect();

    let rentals: Vec<EquipmentRentalInput> = request
        .equipment_rentals
        .into_iter()
        .map(|r| EquipmentRentalInput {
            unit_cost_amount: r.unit_cost_amount,
            unit_charge_amount: r.unit_charge_amount,
            quantity: r.quantity,
        })
        .collect();

    let rentals_ref = if rentals.is_empty() {
        None
    } else {
        Some(rentals.as_slice())
    };

    let result = calculate_totals(&lines, request.diver_count, &request.currency, rentals_ref);

    Json(PricingTotalsResponse {
        shared_cost: result.shared_cost,
        shared_charge: result.shared_charge,
        per_diver_cost: result.per_diver_cost,
        per_diver_charge: result.per_diver_charge,
        shared_cost_per_diver: result.shared_cost_per_diver,
        shared_charge_per_diver: result.shared_charge_per_diver,
        total_cost_per_diver: result.total_cost_per_diver,
        total_charge_per_diver: result.total_charge_per_diver,
        margin_per_diver: result.margin_per_diver,
        diver_count: result.diver_count,
    })
}

/// Calculate boat cost using tiered pricing from vendor agreement
async fn boat_cost(
    State(state): State<AppState>,
    Json(request): Json<CalculateBoatCostRequest>,
) -> Result<Json<BoatCostResponse>, (StatusCode, Json<PricingErrorResponse>)> {
    // Look up content type ID for DiveSite model
    let dive_site_ct_id = queries::get_content_type_id(
        &state.db,
        "diveops_operations",
        "divesite",
    )
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(PricingErrorResponse {
                error_type: "configuration_error".to_string(),
                message: format!("Failed to look up DiveSite content type: {}", e),
                details: None,
            }),
        )
    })?;

    let result = services::calculate_boat_cost(
        &state.db,
        &state.cache,
        dive_site_ct_id,
        request.dive_site_id,
        request.diver_count,
        request.as_of,
    )
    .await
    .map_err(|e| pricing_error_to_response(e))?;

    Ok(Json(BoatCostResponse {
        total: result.total,
        per_diver: result.per_diver,
        base_cost: result.base_cost,
        overage_count: result.overage_count,
        overage_per_diver: result.overage_per_diver,
        included_divers: result.included_divers,
        diver_count: result.diver_count,
        agreement_id: result.agreement_id.and_then(|s| Uuid::parse_str(&s).ok()),
    }))
}

/// Calculate gas fill costs from vendor agreement
async fn gas_fills(
    State(state): State<AppState>,
    Json(request): Json<CalculateGasFillsRequest>,
) -> Result<Json<GasFillResponse>, (StatusCode, Json<PricingErrorResponse>)> {
    // Look up content type ID for Organization model
    let org_ct_id = queries::get_content_type_id(
        &state.db,
        "django_parties",
        "organization",
    )
    .await
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(PricingErrorResponse {
                error_type: "configuration_error".to_string(),
                message: format!("Failed to look up Organization content type: {}", e),
                details: None,
            }),
        )
    })?;

    let result = services::calculate_gas_fills(
        &state.db,
        &state.cache,
        org_ct_id,
        request.dive_shop_id,
        &request.gas_type,
        request.fills_count,
        request.customer_charge_override,
        request.as_of,
    )
    .await
    .map_err(|e| pricing_error_to_response(e))?;

    Ok(Json(GasFillResponse {
        cost_per_fill: result.cost_per_fill,
        charge_per_fill: result.charge_per_fill,
        total_cost: result.total_cost,
        total_charge: result.total_charge,
        fills_count: result.fills_count,
        gas_type: result.gas_type,
        agreement_id: result.agreement_id.and_then(|s| Uuid::parse_str(&s).ok()),
        price_rule_id: result.price_rule_id.and_then(|s| Uuid::parse_str(&s).ok()),
    }))
}

/// Resolve component pricing from Price model
async fn resolve(
    State(state): State<AppState>,
    Json(request): Json<ResolvePricingRequest>,
) -> Result<Json<PricingResolutionResponse>, (StatusCode, Json<PricingErrorResponse>)> {
    let result = services::resolve_component_pricing(
        &state.db,
        request.catalog_item_id,
        request.dive_shop_id,
        request.party_id,
        request.agreement_id,
        request.as_of,
    )
    .await
    .map_err(|e| pricing_error_to_response(e))?;

    Ok(Json(PricingResolutionResponse {
        charge_amount: result.charge_amount,
        charge_currency: result.charge_currency,
        cost_amount: result.cost_amount,
        cost_currency: result.cost_currency,
        price_rule_id: Uuid::parse_str(&result.price_rule_id).unwrap_or_default(),
        has_cost: result.has_cost,
    }))
}

/// Convert PricingError to HTTP error response
fn pricing_error_to_response(error: PricingError) -> (StatusCode, Json<PricingErrorResponse>) {
    match error {
        PricingError::MissingVendorAgreement { scope_type, scope_ref } => {
            (
                StatusCode::NOT_FOUND,
                Json(PricingErrorResponse {
                    error_type: "missing_vendor_agreement".to_string(),
                    message: format!("No vendor agreement found for {}:{}", scope_type, scope_ref),
                    details: Some(serde_json::json!({
                        "scope_type": scope_type,
                        "scope_ref": scope_ref,
                    })),
                }),
            )
        }
        PricingError::MissingPrice { catalog_item_id, context } => {
            (
                StatusCode::NOT_FOUND,
                Json(PricingErrorResponse {
                    error_type: "missing_price".to_string(),
                    message: format!("No price found for catalog item {} ({})", catalog_item_id, context),
                    details: Some(serde_json::json!({
                        "catalog_item_id": catalog_item_id,
                        "context": context,
                    })),
                }),
            )
        }
        PricingError::ConfigurationError { message, errors } => {
            (
                StatusCode::BAD_REQUEST,
                Json(PricingErrorResponse {
                    error_type: "configuration_error".to_string(),
                    message,
                    details: Some(serde_json::json!({ "errors": errors })),
                }),
            )
        }
    }
}
