"""Tests for the TestSuiteGenerator service."""
import pytest
from unittest.mock import Mock, AsyncMock

from src.services.test_suite_generator import TestSuiteGenerator
from src.utils.model import Model

@pytest.fixture
def generator(mock_model: Mock, mock_base_logger: Mock) -> TestSuiteGenerator:
    """Create a TestSuiteGenerator instance with mocked dependencies."""
    return TestSuiteGenerator(mock_model, mock_base_logger)

@pytest.mark.asyncio
async def test_generate_test_suite_success(generator: TestSuiteGenerator, mock_model: Mock) -> None:
    """Test successful test suite generation."""
    # Mock model response
    mock_response = """Title: Test Login Flow
Description: Verify user can log in successfully
Steps:
1. Navigate to login page
2. Enter valid credentials
3. Click submit
Expected Result: User is logged in and redirected to dashboard
---
Title: Test Invalid Login
Description: Verify error handling for invalid credentials
Steps:
1. Navigate to login page
2. Enter invalid credentials
3. Click submit
Expected Result: Error message is displayed"""
    mock_model.generate_response = AsyncMock(return_value=mock_response)
    
    # Generate test suite
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="User Login",
        description="As a user, I want to log in to the system"
    )
    
    # Verify test suite
    assert test_suite.title == "Test Suite for User Login"
    assert test_suite.description == "Test suite generated for story: As a user, I want to log in to the system"
    assert len(test_suite.test_cases) == 2
    
    # Verify first test case
    test_case = test_suite.test_cases[0]
    assert test_case.title == "Test Login Flow"
    assert test_case.description == "Verify user can log in successfully"
    assert len(test_case.steps) == 3
    assert test_case.expected_result == "User is logged in and redirected to dashboard"
    
    # Verify model was called correctly
    mock_model.generate_response.assert_called_once()
    prompt = mock_model.generate_response.call_args[0][0]
    assert "Title: User Login" in prompt
    assert "Description: As a user, I want to log in to the system" in prompt 