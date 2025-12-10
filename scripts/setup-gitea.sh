#!/bin/bash
# =============================================================================
# Gitea Setup Automation Script
# =============================================================================
# This script automates the creation of the cahoots-bot user in Gitea,
# which is required for the code generation system to function.
#
# Prerequisites:
#   - Docker Compose services must be running (docker compose up -d)
#   - Gitea container must be healthy
#
# Usage:
#   ./scripts/setup-gitea.sh
#
# =============================================================================

set -e

# Configuration
BOT_USERNAME="cahoots-bot"
BOT_EMAIL="bot@cahoots.dev"
BOT_PASSWORD="CahootsBot123!"  # Will be set during creation
ENV_FILE=".env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker Compose is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker compose ps &> /dev/null; then
        echo_error "Docker Compose services are not running. Run 'docker compose up -d' first."
        exit 1
    fi
}

# Wait for Gitea to be healthy
wait_for_gitea() {
    echo_info "Waiting for Gitea to be healthy..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose exec gitea gitea --version &> /dev/null; then
            echo_info "Gitea is ready!"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done

    echo_error "Gitea did not become healthy in time"
    exit 1
}

# Check if user already exists
check_user_exists() {
    echo_info "Checking if $BOT_USERNAME user exists..."
    if docker compose exec gitea gitea admin user list 2>/dev/null | grep -q "$BOT_USERNAME"; then
        echo_warn "User $BOT_USERNAME already exists"
        return 0
    fi
    return 1
}

# Create the cahoots-bot user
create_bot_user() {
    echo_info "Creating $BOT_USERNAME user..."

    docker compose exec gitea gitea admin user create \
        --username "$BOT_USERNAME" \
        --email "$BOT_EMAIL" \
        --password "$BOT_PASSWORD" \
        --must-change-password=false \
        --admin

    if [ $? -eq 0 ]; then
        echo_info "User $BOT_USERNAME created successfully!"
    else
        echo_error "Failed to create user $BOT_USERNAME"
        exit 1
    fi
}

# Generate API token
generate_token() {
    echo_info "Generating API token for $BOT_USERNAME..."

    # Generate a unique token name with timestamp
    local token_name="cahoots-api-$(date +%s)"

    # Create token using Gitea CLI
    local token_output=$(docker compose exec gitea gitea admin user generate-access-token \
        --username "$BOT_USERNAME" \
        --token-name "$token_name" \
        --scopes "all" 2>&1)

    # Extract the token from output (format: "Access token was successfully created: <token>")
    local token=$(echo "$token_output" | grep -oP 'Access token was successfully created: \K[a-f0-9]+' || \
                  echo "$token_output" | grep -oP '^[a-f0-9]{40}$')

    if [ -z "$token" ]; then
        echo_error "Failed to generate API token. Output was: $token_output"
        exit 1
    fi

    echo_info "API token generated successfully!"
    echo "$token"
}

# Update .env file with token
update_env_file() {
    local token=$1

    echo_info "Updating $ENV_FILE with GITEA_API_TOKEN..."

    if [ ! -f "$ENV_FILE" ]; then
        echo_error "$ENV_FILE not found!"
        exit 1
    fi

    # Check if GITEA_API_TOKEN already exists in .env
    if grep -q "^GITEA_API_TOKEN=" "$ENV_FILE"; then
        # Update existing token
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS sed syntax
            sed -i '' "s/^GITEA_API_TOKEN=.*/GITEA_API_TOKEN=$token/" "$ENV_FILE"
        else
            # Linux sed syntax
            sed -i "s/^GITEA_API_TOKEN=.*/GITEA_API_TOKEN=$token/" "$ENV_FILE"
        fi
        echo_info "Updated existing GITEA_API_TOKEN in $ENV_FILE"
    else
        # Add new token
        echo "" >> "$ENV_FILE"
        echo "# Gitea Configuration" >> "$ENV_FILE"
        echo "GITEA_API_TOKEN=$token" >> "$ENV_FILE"
        echo_info "Added GITEA_API_TOKEN to $ENV_FILE"
    fi
}

# Restart services that need the new token
restart_services() {
    echo_info "Restarting workspace-service to pick up new token..."
    docker compose up -d workspace-service
    echo_info "Services restarted!"
}

# Main execution
main() {
    echo "=============================================="
    echo "  Gitea Setup for Cahoots Code Generation"
    echo "=============================================="
    echo ""

    check_docker
    wait_for_gitea

    # Check if user exists, create if not
    if ! check_user_exists; then
        create_bot_user
    fi

    # Always generate a new token (in case the old one was lost)
    local token=$(generate_token)

    # Update .env file
    update_env_file "$token"

    # Restart services
    restart_services

    echo ""
    echo "=============================================="
    echo "  Setup Complete!"
    echo "=============================================="
    echo ""
    echo "The $BOT_USERNAME user has been created and configured."
    echo "API token has been saved to $ENV_FILE"
    echo ""
    echo "You can now use the code generation system."
    echo ""
}

main "$@"
