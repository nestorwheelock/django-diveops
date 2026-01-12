# Build stage
FROM rust:1-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y pkg-config libssl-dev && rm -rf /var/lib/apt/lists/*

# Copy manifests
COPY Cargo.toml Cargo.lock* ./

# Create dummy src for dependency caching
RUN mkdir src && echo "fn main() {}" > src/main.rs

# Build dependencies only (cached layer)
RUN cargo build --release && rm -rf src

# Copy actual source code
COPY src ./src
COPY templates ./templates

# Build the application
RUN touch src/main.rs && cargo build --release

# Runtime stage
FROM debian:bookworm-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy binary from builder
COPY --from=builder /app/target/release/happydiving-web /app/happydiving-web

# Copy templates (Askama embeds at compile time, but keep for reference)
COPY --from=builder /app/templates /app/templates

# Copy static files
COPY static /app/static

# Set environment
ENV RUST_LOG=happydiving_web=info,tower_http=info
ENV BIND_ADDR=0.0.0.0:8080

EXPOSE 8080

CMD ["/app/happydiving-web"]
