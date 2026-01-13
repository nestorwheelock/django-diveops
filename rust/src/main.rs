//! Happy Diving - Rust/Axum Frontend
//!
//! High-performance frontend for public-facing pages.
//! Django continues to handle admin, staff portals, and write operations.

use axum::{
    extract::State,
    response::{IntoResponse, Json},
    routing::get,
    Router,
};
use sqlx::postgres::PgPoolOptions;
use sqlx::PgPool;
use tower_http::{compression::CompressionLayer, services::ServeDir, trace::TraceLayer};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod cache;
mod db;
pub mod deco;
mod error;
mod models;
pub mod pricing;
mod routes;

use cache::{start_cache_warmer, AppCache};

/// Application state shared across all handlers
#[derive(Clone)]
pub struct AppState {
    pub db: PgPool,
    pub cache: AppCache,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Load .env file
    dotenvy::dotenv().ok();

    // Initialize tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "happydiving_web=debug,tower_http=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Database connection
    // Supports: DATABASE_URL, or build from POSTGRES_* vars
    // For Unix socket: set POSTGRES_HOST="" or POSTGRES_HOST="/var/run/postgresql"
    let database_url = std::env::var("DATABASE_URL").unwrap_or_else(|_| {
        let user = std::env::var("POSTGRES_USER").unwrap_or_else(|_| "diveops".to_string());
        let password = std::env::var("POSTGRES_PASSWORD").unwrap_or_else(|_| "diveops".to_string());
        let db = std::env::var("POSTGRES_DB").unwrap_or_else(|_| "diveops".to_string());
        let host = std::env::var("POSTGRES_HOST").unwrap_or_default();

        if host.is_empty() || host.starts_with('/') {
            // Unix socket connection (fastest)
            let socket_dir = if host.is_empty() { "/var/run/postgresql" } else { &host };
            format!("postgres://{}:{}@/{db}?host={socket_dir}", user, password)
        } else {
            // TCP connection
            let port = std::env::var("POSTGRES_PORT").unwrap_or_else(|_| "5432".to_string());
            format!("postgres://{}:{}@{}:{}/{}", user, password, host, port, db)
        }
    });

    tracing::info!("Connecting to database...");
    let pool = PgPoolOptions::new()
        .max_connections(10)
        .connect(&database_url)
        .await?;

    tracing::info!("Database connected successfully");

    // Create cache and application state
    let cache = AppCache::new();
    let state = AppState {
        db: pool.clone(),
        cache: cache.clone(),
    };

    // Start background cache warmer
    let warmer_cache = cache.clone();
    let warmer_db = pool.clone();
    tokio::spawn(async move {
        start_cache_warmer(warmer_cache, warmer_db).await;
    });

    // Build router
    let app = Router::new()
        // Health check and cache stats
        .route("/health", get(health_check))
        .route("/health/cache", get(cache_stats))
        // Blog routes
        .route("/blog/", get(routes::blog::list))
        .route("/blog/:slug/", get(routes::blog::detail))
        .route("/blog/category/:category/", get(routes::blog::by_category))
        // App download page (MUST be before slug catch-all)
        .route("/app", get(routes::app::download))
        .route("/app/", get(routes::app::download))
        // Pricing API (called by Django)
        .nest("/api/pricing", pricing::router())
        // Deco validation API (called by Django)
        .nest("/api/deco", deco::router())
        // CMS pages (catch-all for slugs)
        .route("/", get(routes::cms::home))
        .route("/:slug/", get(routes::cms::page))
        // Static files
        .nest_service("/static", ServeDir::new("static"))
        // State and middleware
        .with_state(state)
        .layer(CompressionLayer::new())
        .layer(TraceLayer::new_for_http());

    // Start server
    let addr = std::env::var("BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:8080".to_string());
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    tracing::info!("Listening on {}", addr);

    axum::serve(listener, app).await?;

    Ok(())
}

/// Health check endpoint
async fn health_check(State(state): State<AppState>) -> impl IntoResponse {
    // Test database connection
    match sqlx::query("SELECT 1").fetch_one(&state.db).await {
        Ok(_) => Json(serde_json::json!({
            "status": "healthy",
            "database": "connected",
            "service": "rust-frontend"
        })),
        Err(e) => {
            tracing::error!("Database health check failed: {}", e);
            Json(serde_json::json!({
                "status": "unhealthy",
                "database": "disconnected",
                "error": e.to_string()
            }))
        }
    }
}

/// Cache statistics endpoint
async fn cache_stats(State(state): State<AppState>) -> impl IntoResponse {
    Json(state.cache.stats())
}
