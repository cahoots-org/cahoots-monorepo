#!/bin/bash

# Cahoots Monolith Startup Script

set -e

echo "🚀 Starting Cahoots Monolith System..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=0

    echo "⏳ Waiting for $service_name to be ready..."

    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "$url" >/dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        attempt=$((attempt + 1))
        echo "   Attempt $attempt/$max_attempts - waiting 5 seconds..."
        sleep 5
    done

    echo "❌ $service_name failed to start after $((max_attempts * 5)) seconds"
    return 1
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists docker; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Prerequisites check passed!"

# Parse command line arguments
MODE="api-only"
PROFILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-frontend)
            MODE="full-stack"
            PROFILE="--profile frontend"
            shift
            ;;
        --dev)
            MODE="development"
            PROFILE="--profile dev"
            shift
            ;;
        --clean)
            echo "🧹 Cleaning up previous containers and volumes..."
            docker-compose down -v
            docker system prune -f
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --with-frontend    Start with React frontend (requires frontend code)"
            echo "  --dev             Start in development mode with hot reload"
            echo "  --clean           Clean up before starting"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                      # Start API + Redis only"
            echo "  $0 --with-frontend      # Start API + Redis + Frontend"
            echo "  $0 --dev               # Start in development mode"
            echo "  $0 --clean --dev       # Clean and start in dev mode"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        cat > .env << EOF
# LLM Provider (mock for testing, change for production)
LLM_PROVIDER=mock

# Cache Settings
USE_SEMANTIC_CACHE=true
CACHE_TTL=3600

# Processing Settings
MAX_DEPTH=5
COMPLEXITY_THRESHOLD=0.45
BATCH_SIZE=3

# Environment
ENV=development
EOF
    fi
    echo "✅ Created .env file with default settings"
fi

# Start services based on mode
echo "🛠️  Starting services in $MODE mode..."

case $MODE in
    "api-only")
        echo "🔧 Starting API + Redis only..."
        docker-compose up -d redis api
        wait_for_service "http://localhost:8000/health" "API"
        ;;
    "full-stack")
        echo "🔧 Starting full stack (API + Redis + Frontend)..."
        docker-compose $PROFILE up -d
        wait_for_service "http://localhost:8000/health" "API"
        wait_for_service "http://localhost:3000" "Frontend"
        ;;
    "development")
        echo "🔧 Starting development mode (hot reload)..."
        docker-compose $PROFILE up -d
        wait_for_service "http://localhost:8001/health" "Development API"
        ;;
esac

# Show status
echo ""
echo "🎉 Cahoots Monolith is running!"
echo ""
echo "📡 Services Status:"
docker-compose ps

echo ""
echo "🌐 Access URLs:"
echo "   API Documentation: http://localhost:8000/docs"
echo "   API Health Check:  http://localhost:8000/health"
echo "   Task Statistics:   http://localhost:8000/api/tasks/stats"

if [ "$MODE" = "full-stack" ]; then
    echo "   Frontend:          http://localhost:3000"
fi

if [ "$MODE" = "development" ]; then
    echo "   Dev API:           http://localhost:8001"
    echo "   Dev API Docs:      http://localhost:8001/docs"
fi

echo ""
echo "🔍 Useful Commands:"
echo "   View logs:         docker-compose logs -f"
echo "   Stop services:     docker-compose down"
echo "   Clean restart:     $0 --clean"

if [ "$MODE" = "full-stack" ]; then
    echo "   Frontend logs:     docker-compose logs -f frontend"
fi

echo ""
echo "🧪 Test the system:"
echo "   Create a task:     curl -X POST http://localhost:8000/api/tasks -H 'Content-Type: application/json' -d '{\"description\":\"Create a hello world function\",\"user_id\":\"test\"}'"
echo "   Run benchmarks:    python test_benchmark.py"
echo ""
echo "Ready for testing! 🚀"