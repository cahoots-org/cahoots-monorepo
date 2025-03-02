#!/bin/bash
# Script to test GitHub Actions workflow locally using act
# https://github.com/nektos/act

# Don't exit immediately on errors to allow all jobs to run
# set -e

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo "Error: 'act' is not installed. Please install it first."
    echo "Installation instructions: https://github.com/nektos/act#installation"
    exit 1
fi

# Default values
EVENT="workflow_dispatch"
DEBUG="true"
TEST_ONLY="false"
BUILD_ONLY="false"
SECRETS_FILE=".secrets"
GITHUB_USERNAME="robmillersoftware"  # GitHub username for authentication

# Check if secrets file exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo "Warning: Secrets file '$SECRETS_FILE' not found. Creating a template..."
    cat > "$SECRETS_FILE" << EOF
# GitHub token for authentication
GITHUB_TOKEN=your_github_token_here
# Personal access token with packages:write scope
CR_PAT=your_personal_access_token_here
# Kubernetes config for deployment
KUBE_CONFIG=your_kube_config_here
EOF
    echo "Please edit '$SECRETS_FILE' with your actual secrets."
    exit 1
fi

# Extract GitHub token from secrets file
GITHUB_TOKEN=$(grep -E "^GITHUB_TOKEN=" "$SECRETS_FILE" | cut -d= -f2)
if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "your_github_token_here" ]; then
    echo "Error: Valid GITHUB_TOKEN not found in $SECRETS_FILE"
    echo "Please add a valid GitHub token to the secrets file."
    exit 1
fi

# Extract CR_PAT from secrets file (for GitHub Container Registry)
CR_PAT=$(grep -E "^CR_PAT=" "$SECRETS_FILE" | cut -d= -f2)
if [ -z "$CR_PAT" ] || [ "$CR_PAT" = "your_personal_access_token_here" ]; then
    echo "Warning: Valid CR_PAT not found in $SECRETS_FILE"
    echo "Using GITHUB_TOKEN as fallback for GitHub Container Registry."
    CR_PAT="$GITHUB_TOKEN"
fi

# Create event file in the .github directory
mkdir -p .github/workflow-events
EVENT_FILE=".github/workflow-events/event.json"

# Ensure .bandit file exists (needed for security scan)
if [ ! -f ".bandit" ]; then
    echo "Creating default .bandit configuration file..."
    cat > .bandit << EOF
[bandit]
exclude: /tests
EOF
fi

# Prepare coverage for local testing
# Create a basic .coveragerc file if not exists
if [ ! -f ".coveragerc" ]; then
    echo "Creating .coveragerc file..."
    cat > .coveragerc << EOF
[run]
source = libs,services
omit = */tests/*,*/__pycache__/*
EOF
fi

# Create event JSON file for workflow_dispatch
cat > "$EVENT_FILE" << EOF
{
  "inputs": {
    "debug_enabled": "$DEBUG",
    "test_only": "$TEST_ONLY",
    "build_only": "$BUILD_ONLY"
  }
}
EOF

# Run act with the event file
echo "Running workflow with event: workflow_dispatch"
echo "Debug mode: $DEBUG"

# Create required environment variables for all steps
# This includes artifacts handling and other GitHub Actions specifics
echo "Setting up environment variables for local testing..."

# Run act with necessary environment variables
# We're using continue-on-error for all jobs to see full results
act workflow_dispatch \
    --eventpath "$EVENT_FILE" \
    --secret-file "$SECRETS_FILE" \
    --env ACTIONS_RUNTIME_TOKEN=fake-token \
    --env ACTIONS_RESULTS_URL=fake-url \
    --env ACT=true \
    --env GITHUB_REPOSITORY="${GITHUB_USERNAME}/ai_dev_team" \
    --env GITHUB_REPOSITORY_OWNER="${GITHUB_USERNAME}" \
    --bind \
    --use-gitignore

echo ""
echo "⚠️ NOTE: Some jobs may fail when running with act due to platform differences"
echo "The following are expected limitations when running workflows locally:"
echo "  - Security scan may report vulnerabilities that are acceptable in your context"
echo "  - Coverage report may fail to generate if test execution doesn't produce coverage data"
echo "  - Docker operations may have issues with registry authentication"
echo ""
echo "NOTE: If you encounter authentication issues with GitHub Actions or GitHub Container Registry,"
echo "make sure your Personal Access Token (PAT) has the following scopes:"
echo "  - repo (full control of private repositories)"
echo "  - workflow (update GitHub Action workflows)" 
echo "  - packages:read and packages:write (for GitHub Container Registry)"
echo ""
echo "You can create a new PAT at: https://github.com/settings/tokens"