#!/bin/bash
set -e

# Buceo Feliz Deployment Script
# Usage: ./scripts/deploy.sh [command]

SERVER_HOST="${SERVER_HOST:-207.246.125.49}"
SERVER_USER="${SERVER_USER:-root}"
REMOTE_PATH="/opt/diveops"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Upload APK to server
upload_apk() {
    local apk_file="$1"

    if [ -z "$apk_file" ]; then
        # Find latest APK in common locations (check buceo-feliz first, then buceo)
        apk_file=$(find . -name "buceo-feliz-*.apk" -type f 2>/dev/null | head -1)
        [ -z "$apk_file" ] && apk_file=$(find . -name "buceo-*.apk" -type f 2>/dev/null | head -1)
        [ -z "$apk_file" ] && apk_file=$(find ~/Downloads -name "buceo-feliz-*.apk" -type f 2>/dev/null | head -1)
        [ -z "$apk_file" ] && apk_file=$(find ~/Downloads -name "buceo-*.apk" -type f 2>/dev/null | head -1)
    fi

    [ -z "$apk_file" ] && error "No APK file specified or found. Usage: $0 upload-apk [path/to/buceo-feliz-X.Y.Z.apk]"
    [ ! -f "$apk_file" ] && error "APK file not found: $apk_file"

    local filename=$(basename "$apk_file")
    local target_filename="$filename"

    # Convert buceo-feliz-X.Y.Z.apk to buceo-X.Y.Z.apk (Rust expects buceo-X.Y.Z.apk)
    if [[ "$filename" =~ ^buceo-feliz-(.+)\.apk$ ]]; then
        target_filename="buceo-${BASH_REMATCH[1]}.apk"
        info "Renaming $filename -> $target_filename for server"
    fi

    # Validate filename format (supports X.Y.Z or X.Y.Z-suffix like alpha, beta, rc1)
    if [[ ! "$target_filename" =~ ^buceo-[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?\.apk$ ]]; then
        warn "APK filename should be buceo-feliz-X.Y.Z.apk or buceo-X.Y.Z.apk format"
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi

    info "Uploading $filename to server as $target_filename (rsync with resume)..."

    # Upload to staging location using rsync (supports resume)
    ssh "$SERVER_USER@$SERVER_HOST" "mkdir -p $REMOTE_PATH/downloads"
    rsync -avP --progress "$apk_file" "$SERVER_USER@$SERVER_HOST:$REMOTE_PATH/downloads/$target_filename"

    info "Copying APK into Rust container..."
    ssh "$SERVER_USER@$SERVER_HOST" "docker cp $REMOTE_PATH/downloads/$target_filename diveops_rust:/app/static/downloads/"

    info "Purging nginx cache..."
    ssh "$SERVER_USER@$SERVER_HOST" "rm -rf /var/cache/nginx/happydiving/* && docker exec diveops_nginx nginx -s reload" 2>/dev/null || warn "Could not purge nginx cache"

    info "Restarting Rust container to pick up new APK..."
    ssh "$SERVER_USER@$SERVER_HOST" "cd $REMOTE_PATH && docker compose -f docker-compose.prod.yml restart rust"

    info "APK uploaded successfully: $target_filename"
    info "Download page will now show version: ${target_filename#buceo-}"
}

# List APKs on server
list_apks() {
    info "APKs on server:"
    ssh "$SERVER_USER@$SERVER_HOST" "docker exec diveops_rust ls -la /app/static/downloads/ 2>/dev/null || echo 'No APKs found'"
}

# Show logs
logs() {
    local service="${1:-web}"
    local lines="${2:-100}"
    ssh "$SERVER_USER@$SERVER_HOST" "cd $REMOTE_PATH && docker compose -f docker-compose.prod.yml logs --tail=$lines $service"
}

# Restart services
restart() {
    local service="$1"
    if [ -z "$service" ]; then
        info "Restarting all services..."
        ssh "$SERVER_USER@$SERVER_HOST" "cd $REMOTE_PATH && docker compose -f docker-compose.prod.yml restart"
    else
        info "Restarting $service..."
        ssh "$SERVER_USER@$SERVER_HOST" "cd $REMOTE_PATH && docker compose -f docker-compose.prod.yml restart $service"
    fi
}

# Show status
status() {
    ssh "$SERVER_USER@$SERVER_HOST" "cd $REMOTE_PATH && docker compose -f docker-compose.prod.yml ps"
}

# SSH into server
shell() {
    ssh "$SERVER_USER@$SERVER_HOST"
}

# Help
usage() {
    cat <<EOF
Buceo Feliz Deployment Script

Usage: $0 <command> [args]

Commands:
  upload-apk [file]   Upload APK to server (auto-finds if not specified)
  list-apks           List APKs currently on server
  logs [service] [n]  Show logs (default: web, 100 lines)
  restart [service]   Restart services (all if not specified)
  status              Show container status
  shell               SSH into server

Environment:
  SERVER_HOST         Server hostname (default: happydiving.mx)
  SERVER_USER         SSH user (default: root)

Examples:
  $0 upload-apk ~/Downloads/buceo-1.0.1.apk
  $0 logs rust 50
  $0 restart nginx
EOF
}

# Main
case "${1:-}" in
    upload-apk)  upload_apk "$2" ;;
    list-apks)   list_apks ;;
    logs)        logs "$2" "$3" ;;
    restart)     restart "$2" ;;
    status)      status ;;
    shell)       shell ;;
    -h|--help|help|"") usage ;;
    *)           error "Unknown command: $1. Use '$0 help' for usage." ;;
esac
