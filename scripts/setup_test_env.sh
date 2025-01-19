#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx aiohttp

# Create test directories if they don't exist
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/e2e

# Set up environment variables for testing
export PYTHONPATH=$PYTHONPATH:$(pwd)
export AGENT_TYPE="test-agent"
export K8S_NAMESPACE="test-namespace"
export SECURITY_JWT_SECRET="test-jwt-secret-that-is-at-least-32-chars-long"
export SECURITY_JWT_ALGORITHM="HS256"
export SECURITY_ACCESS_TOKEN_EXPIRE_MINUTES="30"
export DB_URL="postgresql+asyncpg://test:test@localhost:5432/test"
export REDIS_URL="redis://localhost:6379/0"

# Run tests with coverage
pytest tests/ -v --cov=src --cov-report=term-missing 