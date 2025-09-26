#!/bin/bash

# Simple all-in-one deployment script
set -e

echo "🚀 Deploying Cahoots..."

# Load environment variables from .env
if [ -f .env ]; then
    echo "Loading .env file..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and add your API keys"
    exit 1
fi

# Check for required API keys
if [ -z "$CEREBRAS_API_KEY" ]; then
    echo "Error: Missing CEREBRAS_API_KEY in .env"
    echo "Please add CEREBRAS_API_KEY to .env"
    exit 1
fi

# Check for Fly CLI
if ! command -v flyctl &> /dev/null; then
    echo "Installing Fly CLI..."
    curl -L https://fly.io/install.sh | sh
    export PATH="/home/$USER/.fly/bin:$PATH"
fi

# Use Upstash Redis URL with token
REDIS_TOKEN="AS2CAAIncDJlMjEzZDhkNjMwN2Q0ZThkYThmMjAzMmQzMDUzYmM3YnAyMTE2NTA"
REDIS_URL="redis://default:${REDIS_TOKEN}@more-ladybug-11650.upstash.io:6379"
echo "Using Upstash Redis database at more-ladybug-11650.upstash.io"

# Check if app already exists
if flyctl apps list 2>/dev/null | grep -q "cahoots"; then
    echo "App 'cahoots' already exists, skipping creation..."
else
    echo "Creating new Fly app..."
    # Retry logic for network issues
    for i in {1..3}; do
        if flyctl launch --name cahoots --dockerfile Dockerfile --region iad --now=false; then
            break
        else
            echo "Network error, retrying in 5 seconds... (attempt $i/3)"
            sleep 5
        fi
    done
fi

# Set all secrets from .env
echo "Setting secrets..."
flyctl secrets set \
    REDIS_URL="$REDIS_URL" \
    CEREBRAS_API_KEY="$CEREBRAS_API_KEY" \
    CEREBRAS_MODEL="${CEREBRAS_MODEL:-llama3.1-70b}" \
    LLM_PROVIDER="cerebras" \
    MAX_DEPTH="${MAX_DEPTH:-3}" \
    ATOMICITY_THRESHOLD="${ATOMICITY_THRESHOLD:-0.45}" \
    LAMBDA_API_KEY="${LAMBDA_API_KEY:-none}" \
    GROQ_API_KEY="${GROQ_API_KEY:-none}" \
    GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}" \
    GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET}" \
    ENVIRONMENT="production" \
    JWT_SECRET_KEY="$(openssl rand -base64 32)" \
    --app cahoots

# Deploy API
echo "Deploying API..."
flyctl deploy --app cahoots

# Deploy Frontend
echo ""
echo "Deploying Frontend..."
cd frontend

# Build the frontend first to ensure latest changes are included
echo "Building frontend..."
# Docker's multi-stage build will handle the build directory itself
# We don't need to build locally since Dockerfile.fly does it

# Check if frontend app exists
if flyctl apps list 2>/dev/null | grep -q "cahoots-frontend"; then
    echo "Frontend app already exists, deploying..."
else
    echo "Creating frontend app..."
    flyctl launch --name cahoots-frontend --dockerfile Dockerfile.fly --region iad --now=false
fi

# Deploy frontend using Fly.io specific Dockerfile with no-cache to force rebuild
echo "Deploying frontend (forcing rebuild)..."
flyctl deploy --app cahoots-frontend --dockerfile Dockerfile.fly --no-cache

cd ..

echo ""
echo "✅ Done! Your apps are at:"
echo "   API:      https://cahoots.fly.dev"
echo "   Frontend: https://cahoots-frontend.fly.dev"
echo ""
echo "View API logs:      flyctl logs --app cahoots"
echo "View Frontend logs: flyctl logs --app cahoots-frontend"