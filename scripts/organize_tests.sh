#!/bin/bash

# Create test directory structure
mkdir -p tests/{unit,integration,e2e}/{api,services,models,utils,agents}
mkdir -p tests/fixtures
mkdir -p tests/data

# Move test files to appropriate directories
mv tests/test_*.py tests/unit/ 2>/dev/null || true
mv tests/api/test_*.py tests/unit/api/ 2>/dev/null || true
mv tests/services/test_*.py tests/unit/services/ 2>/dev/null || true
mv tests/models/test_*.py tests/unit/models/ 2>/dev/null || true
mv tests/utils/test_*.py tests/unit/utils/ 2>/dev/null || true
mv tests/agents/test_*.py tests/unit/agents/ 2>/dev/null || true

# Create test data directory
mkdir -p tests/data/{mock_responses,fixtures,schemas}

# Create test helper files
touch tests/conftest.py
touch tests/unit/conftest.py
touch tests/integration/conftest.py
touch tests/e2e/conftest.py

# Create README files
echo "# Unit Tests
This directory contains unit tests for individual components.

## Structure
- api/: API endpoint tests
- services/: Service layer tests
- models/: Data model tests
- utils/: Utility function tests
- agents/: Agent tests" > tests/unit/README.md

echo "# Integration Tests
This directory contains integration tests between components.

## Structure
- api/: API integration tests
- services/: Service integration tests
- agents/: Agent integration tests" > tests/integration/README.md

echo "# End-to-End Tests
This directory contains end-to-end tests for complete workflows.

## Structure
- api/: API e2e tests
- workflows/: Complete workflow tests" > tests/e2e/README.md

# Make script executable
chmod +x scripts/organize_tests.sh

echo "Test directory structure organized successfully!" 