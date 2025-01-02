#!/bin/bash
set -eo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
MAX_PARALLEL_TESTS=${MAX_PARALLEL_TESTS:-4}
TEST_TIMEOUT=${TEST_TIMEOUT:-30}
COVERAGE_THRESHOLD=${COVERAGE_THRESHOLD:-80}

# Function to print section headers
print_header() {
    echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

# Function to print warnings
print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Function to handle errors
handle_error() {
    echo -e "\n${RED}Error in $1${NC}"
    # Kill any remaining test processes
    cleanup
    exit 1
}

# Function to cleanup resources
cleanup() {
    print_header "Cleaning up test environment"
    # Kill any remaining test processes
    pkill -f "pytest" || true
    pkill -f "k6" || true
    
    # Clean up any dangling containers
    docker ps -q -f "label=testcontainers" | xargs -r docker rm -f || true
}

# Set up trap for cleanup
trap 'handle_error ${BASH_SOURCE[0]}:${LINENO}' ERR
trap cleanup EXIT

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Run unit tests first
print_header "Running unit tests"
python -m pytest tests/ \
    -vv \
    -s \
    --log-cli-level=DEBUG \
    --cov=src \
    --cov-report=term-missing \
    --cov-config=pyproject.toml \
    -n auto \
    --dist loadscope \
    --cov-append

# Check coverage threshold
coverage_result=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
if (( $(echo "$coverage_result < $COVERAGE_THRESHOLD" | bc -l) )); then
    print_warning "Coverage ($coverage_result%) is below threshold ($COVERAGE_THRESHOLD%)"
    exit 1
fi

# Run k6 tests with custom Redis extension
print_header "Running k6 tests (integration, load, and stress)"

# Build k6 with required extensions
print_header "Building custom k6"
docker build -t k6-custom - <<EOF
FROM grafana/xk6:latest
RUN xk6 build \
    --with github.com/grafana/xk6-redis \
    --with github.com/grafana/xk6-prometheus \
    --with github.com/grafana/xk6-client-tracing
EOF

# Run k6 tests with custom build
docker run --rm \
    --network=host \
    -v "${PWD}/tests/k6:/scripts" \
    -e API_URL=http://localhost:8000 \
    -e REDIS_URL=localhost:6379 \
    k6-custom run \
    --out json=/scripts/results.json \
    --out prometheus \
    /scripts/test_api.js

# Parse and display test results
print_header "Test Results Summary"
jq -r '.metrics | to_entries | .[] | select(.key | contains("checks")) | "\(.key): \(.value.passes)/\(.value.fails)"' tests/k6/results.json

# Check for test failures
if jq -e '.metrics | to_entries | .[] | select(.key | contains("checks")) | .value.fails > 0' tests/k6/results.json > /dev/null; then
    print_warning "Some tests failed!"
    exit 1
fi

print_header "All tests completed successfully!" 