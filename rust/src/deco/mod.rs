//! Decompression validation module.
//!
//! Provides Bühlmann ZHL-16C decompression calculations as HTTP endpoints,
//! eliminating subprocess overhead from the standalone binary.

mod models;
mod routes;
mod validator;

pub use routes::router;
