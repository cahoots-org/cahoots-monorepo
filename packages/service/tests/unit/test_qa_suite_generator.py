"""Tests for the QASuiteGenerator service."""
import pytest
from unittest import mock
from unittest.mock import Mock, AsyncMock, patch
from cahoots_service.services.qa_suite_generator import QASuiteGenerator
from cahoots_service.utils.model import Model
from cahoots_service.utils.base_logger import BaseLogger
from cahoots_service.models.qa_suite import TestCase
import asyncio

@pytest.fixture
def mock_model() -> Mock:
    """Create a mock Model instance."""
    mock = Mock(spec=Model)
    mock.generate_response = AsyncMock()
    return mock

@pytest.fixture
def mock_base_logger() -> Mock:
    """Create a mock BaseLogger instance."""
    return Mock(spec=BaseLogger)

@pytest.fixture
def generator(mock_model: Mock, mock_base_logger: Mock) -> QASuiteGenerator:
    """Create a QASuiteGenerator instance with mocked dependencies."""
    return QASuiteGenerator(mock_model, mock_base_logger)

@pytest.mark.asyncio
async def test_generate_test_suite_success(generator: QASuiteGenerator, mock_model: Mock) -> None:
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
    mock_model.generate_response.return_value = mock_response
    
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
    
    # Verify second test case
    test_case = test_suite.test_cases[1]
    assert test_case.title == "Test Invalid Login"
    assert test_case.description == "Verify error handling for invalid credentials"
    assert len(test_case.steps) == 3
    assert test_case.expected_result == "Error message is displayed"
    
    # Verify model was called correctly
    mock_model.generate_response.assert_called_once()
    prompt = mock_model.generate_response.call_args[0][0]
    assert "Title: User Login" in prompt
    assert "Description: As a user, I want to log in to the system" in prompt

@pytest.mark.asyncio
async def test_generate_test_suite_model_error(generator: QASuiteGenerator, mock_model: Mock, mock_base_logger: Mock) -> None:
    """Test error handling when model generation fails."""
    # Mock model error
    mock_model.generate_response.side_effect = Exception("Model error")
    
    # Generate test suite
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="User Login",
        description="As a user, I want to log in to the system"
    )
    
    # Verify default test case was created
    assert len(test_suite.test_cases) == 1
    test_case = test_suite.test_cases[0]
    assert test_case.title == "Basic User Login Test"
    assert test_case.description == "Basic test case for User Login"
    assert test_case.steps == ["Verify basic functionality"]
    assert test_case.expected_result == "Basic functionality works as expected"
    
    # Verify error was logged
    mock_base_logger.error.assert_called_once()
    assert "Model error" in mock_base_logger.error.call_args[0][0]

@pytest.mark.asyncio
async def test_generate_test_suite_empty_response(generator: QASuiteGenerator, mock_model: Mock, mock_base_logger: Mock) -> None:
    """Test handling of empty model response."""
    # Mock empty response
    mock_model.generate_response.return_value = ""
    
    # Generate test suite
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="User Login",
        description="As a user, I want to log in to the system"
    )
    
    # Verify default test case was created
    assert len(test_suite.test_cases) == 1
    test_case = test_suite.test_cases[0]
    assert test_case.title == "Basic User Login Test"
    
    # Verify warning was logged
    mock_base_logger.warning.assert_called_once()
    assert "No valid test cases parsed" in mock_base_logger.warning.call_args[0][0]

@pytest.mark.asyncio
async def test_generate_test_suite_invalid_format(generator: QASuiteGenerator, mock_model: Mock, mock_base_logger: Mock) -> None:
    """Test handling of invalid model response format."""
    # Mock invalid response format
    mock_model.generate_response.return_value = """Invalid format
Not following the template
Random text"""
    
    # Generate test suite
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="User Login",
        description="As a user, I want to log in to the system"
    )
    
    # Verify default test case was created
    assert len(test_suite.test_cases) == 1
    test_case = test_suite.test_cases[0]
    assert test_case.title == "Basic User Login Test"
    
    # Verify warning was logged
    mock_base_logger.warning.assert_called()

@pytest.mark.asyncio
async def test_parse_test_cases_partial_match(generator: QASuiteGenerator) -> None:
    """Test parsing of partially valid test cases."""
    # Response with one valid and one invalid test case
    response = """Title: Valid Test
Description: Valid description
Steps:
1. Step one
2. Step two
Expected Result: Expected outcome
---
Title: Invalid Test
Missing description
Invalid steps
No expected result"""
    
    test_cases = generator._parse_test_cases(response)
    
    # Verify only valid test case was parsed
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.title == "Valid Test"
    assert test_case.description == "Valid description"
    assert len(test_case.steps) == 2
    assert test_case.expected_result == "Expected outcome"

@pytest.mark.asyncio
async def test_parse_test_cases_with_error(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test handling of test case parsing errors."""
    # Response that will cause a parsing error
    response = """Title: Test Case
Description: Description
Steps:
1. [invalid regex pattern
Expected Result: Result
---
Title: Valid Test
Description: Valid description
Steps:
1. Valid step
Expected Result: Valid result"""
    
    test_cases = generator._parse_test_cases(response)
    
    # Verify both test cases were parsed
    assert len(test_cases) == 2
    
    # Verify first test case
    test_case = test_cases[0]
    assert test_case.title == "Test Case"
    assert test_case.description == "Description"
    assert test_case.steps == ["[invalid regex pattern"]
    assert test_case.expected_result == "Result"
    
    # Verify second test case
    test_case = test_cases[1]
    assert test_case.title == "Valid Test"
    assert test_case.description == "Valid description"
    assert test_case.steps == ["Valid step"]
    assert test_case.expected_result == "Valid result"

@pytest.mark.asyncio
async def test_build_prompt(generator: QASuiteGenerator) -> None:
    """Test prompt building."""
    title = "Test Story"
    description = "Test description"
    
    prompt = generator._build_prompt(title, description)
    
    # Verify prompt format
    assert "Title: Test Story" in prompt
    assert "Description: Test description" in prompt
    assert "Generate at least 2 test cases" in prompt
    assert "positive and negative scenarios" in prompt 

@pytest.mark.asyncio
async def test_parse_test_cases_exception_handling(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test handling of exceptions during test case parsing."""
    # Set up mock logger
    generator.logger = mock_base_logger
    
    # Response with malformed test case that will cause a regex match failure
    response = """Title: Test Case
Description: Description
Steps:
1. Step one
Expected Result: Result
---
Title: Invalid Test
Description: Description
Steps:
1. Step one
Expected Result: Result
[invalid section]
---
Title: Valid Test
Description: Valid description
Steps:
1. Valid step
Expected Result: Valid result"""
    
    # Mock regex search to raise an exception
    with patch('re.search', side_effect=[
        Mock(group=lambda x: "Test Case"),  # First title
        Mock(group=lambda x: "Description"),  # First description
        Mock(group=lambda x: "1. Step one"),  # First steps
        Mock(group=lambda x: "Result"),  # First result
        Exception("Regex error"),  # Second test case - raise exception
        Mock(group=lambda x: "Valid Test"),  # Third title
        Mock(group=lambda x: "Valid description"),  # Third description
        Mock(group=lambda x: "1. Valid step"),  # Third steps
        Mock(group=lambda x: "Valid result")  # Third result
    ]):
        test_cases = generator._parse_test_cases(response)
    
    # Verify valid test cases were parsed
    assert len(test_cases) == 2
    
    # Verify first test case
    test_case = test_cases[0]
    assert test_case.title == "Test Case"
    assert test_case.description == "Description"
    assert test_case.steps == ["Step one"]
    assert test_case.expected_result == "Result"
    
    # Verify second test case (skipped invalid one)
    test_case = test_cases[1]
    assert test_case.title == "Valid Test"
    assert test_case.description == "Valid description"
    assert test_case.steps == ["Valid step"]
    assert test_case.expected_result == "Valid result"
    
    # Verify error was logged
    mock_base_logger.warning.assert_called_once()
    assert "Error parsing test case" in mock_base_logger.warning.call_args[0][0] 

@pytest.mark.asyncio
async def test_parse_test_cases_malformed_sections(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test handling of malformed test case sections."""
    # Response with malformed sections
    response = """Title: Test Case
Description: Description
Steps:
Invalid steps format
Expected Result: Result
---
Title: Test Case 2
Description: Description 2
Steps:
1. Valid step
Expected Result: Result
Missing section marker
Title: Test Case 3
Description: Description 3
Steps:
1. Valid step
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    # Verify only valid test cases were parsed
    assert len(test_cases) == 2
    
    # Verify second test case
    test_case = test_cases[0]
    assert test_case.title == "Test Case 2"
    assert test_case.description == "Description 2"
    assert test_case.steps == ["Valid step"]
    assert test_case.expected_result == "Result"
    
    # Verify third test case
    test_case = test_cases[1]
    assert test_case.title == "Test Case 3"
    assert test_case.description == "Description 3"
    assert test_case.steps == ["Valid step"]
    assert test_case.expected_result == "Result"

@pytest.mark.asyncio
async def test_parse_test_cases_missing_fields(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test handling of test cases with missing required fields."""
    # Response with missing fields
    response = """Title: Test Case
Steps:
1. Step one
Expected Result: Result
---
Description: Only description
---
Title: Valid Test
Description: Valid description
Steps:
1. Valid step
Expected Result: Valid result"""
    
    test_cases = generator._parse_test_cases(response)
    
    # Verify only valid test case was parsed
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.title == "Valid Test"
    assert test_case.description == "Valid description"
    assert test_case.steps == ["Valid step"]
    assert test_case.expected_result == "Valid result"
    
    # Verify warning was logged for invalid test cases
    assert mock_base_logger.warning.call_count == 2

@pytest.mark.asyncio
async def test_generate_test_suite_with_special_characters(generator: QASuiteGenerator, mock_model: Mock) -> None:
    """Test handling of special characters in test case generation."""
    # Mock response with special characters
    mock_response = """Title: Test <script>alert('xss')</script>
Description: Test case with special chars: & < > " '
Steps:
1. Step with newline\nand tab\t
2. Step with unicode: 🚀 💻
Expected Result: Result with special chars: & < > " '"""
    mock_model.generate_response.return_value = mock_response
    
    # Generate test suite
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="Special <script>alert('xss')</script>",
        description="Description with special chars: & < > \" '"
    )
    
    # Verify test case was parsed correctly
    assert len(test_suite.test_cases) == 1
    test_case = test_suite.test_cases[0]
    assert "<script>" in test_case.title
    assert "special chars: & < > \" '" in test_case.description
    assert "unicode: 🚀 💻" in test_case.steps[1]
    assert "special chars: & < > \" '" in test_case.expected_result

@pytest.mark.asyncio
async def test_generate_test_suite_concurrent_calls(generator: QASuiteGenerator, mock_model: Mock) -> None:
    """Test concurrent test suite generation."""
    # Mock model response
    mock_model.generate_response.return_value = """Title: Test Case
Description: Description
Steps:
1. Step one
Expected Result: Result"""
    
    # Generate multiple test suites concurrently
    tasks = [
        generator.generate_test_suite(
            story_id=f"story-{i}",
            title=f"Story {i}",
            description=f"Description {i}"
        )
        for i in range(5)
    ]
    
    # Run tasks concurrently
    test_suites = await asyncio.gather(*tasks)
    
    # Verify all test suites were generated
    assert len(test_suites) == 5
    for i, test_suite in enumerate(test_suites):
        assert test_suite.story_id == f"story-{i}"
        assert len(test_suite.test_cases) == 1
        assert test_suite.test_cases[0].title == "Test Case" 

@pytest.mark.asyncio
async def test_parse_test_cases_bullet_points(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with bullet point steps."""
    response = """Title: Test Case
Description: Description
Steps:
* First bullet point
* Second bullet point
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == ["First bullet point", "Second bullet point"]

@pytest.mark.asyncio
async def test_parse_test_cases_multiline_steps(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with multiline steps."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step
   with continuation
2. Second step
   also with continuation
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == ["First step with continuation", "Second step also with continuation"]

@pytest.mark.asyncio
async def test_parse_test_cases_invalid_step_format(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with invalid step format."""
    response = """Title: Test Case
Description: Description
Steps:
Invalid step format without number or bullet
1. Valid step
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == ["Valid step"]

@pytest.mark.asyncio
async def test_parse_test_cases_empty_steps(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with empty steps section."""
    response = """Title: Test Case
Description: Description
Steps:

Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 0
    mock_base_logger.warning.assert_called_with("No valid steps found in test case: Title: Test Case\nDescription: Description\nSteps:\n\nExpected Result: Result...")

@pytest.mark.asyncio
async def test_generate_test_suite_model_error_with_retry(generator: QASuiteGenerator, mock_model: Mock) -> None:
    """Test handling of model error with retry."""
    # First call raises exception, second call succeeds
    mock_model.generate_response.side_effect = [
        Exception("Model error"),
        """Title: Test Case
Description: Description
Steps:
1. Step one
Expected Result: Result"""
    ]
    
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="Story",
        description="Description"
    )
    
    assert len(test_suite.test_cases) == 1
    assert test_suite.test_cases[0].title == "Test Case" 

@pytest.mark.asyncio
async def test_generate_test_suite_double_failure(generator: QASuiteGenerator, mock_model: Mock) -> None:
    """Test handling of model error when both attempts fail."""
    # Both calls raise exceptions
    mock_model.generate_response.side_effect = [
        Exception("First error"),
        Exception("Second error")
    ]
    
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="Story",
        description="Description"
    )
    
    # Should use default test case
    assert len(test_suite.test_cases) == 1
    assert test_suite.test_cases[0].title == "Basic Story Test"
    assert mock_model.generate_response.call_count == 2

@pytest.mark.asyncio
async def test_parse_test_cases_mixed_step_formats(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with mixed step formats."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step
   with continuation
* Bullet point
2. Second step
   also with continuation
- Another bullet point
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == [
        "First step with continuation",
        "Bullet point",
        "Second step also with continuation",
        "Another bullet point"
    ]

@pytest.mark.asyncio
async def test_parse_test_cases_invalid_lines_between_steps(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with invalid lines between steps."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step
Invalid line
2. Second step
Another invalid line
* Bullet point
Invalid line after bullet
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == [
        "First step Invalid line",
        "Second step Another invalid line",
        "Bullet point Invalid line after bullet"
    ] 

@pytest.mark.asyncio
async def test_generate_test_suite_double_failure_with_retry(generator: QASuiteGenerator, mock_model: Mock) -> None:
    """Test handling of model error when both attempts fail."""
    # Both calls raise exceptions
    mock_model.generate_response.side_effect = [
        Exception("First error"),
        Exception("Second error")
    ]
    
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="Story",
        description="Description"
    )
    
    # Should use default test case
    assert len(test_suite.test_cases) == 1
    assert test_suite.test_cases[0].title == "Basic Story Test"
    assert mock_model.generate_response.call_count == 2
    mock_model.generate_response.assert_has_calls([
        mock.call(generator._build_prompt("Story", "Description")),
        mock.call(generator._build_prompt("Story", "Description"))
    ])

@pytest.mark.asyncio
async def test_parse_test_cases_mixed_step_formats_with_continuations(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with mixed step formats and continuations."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step
   with continuation
   and more continuation
* Bullet point
  with continuation
  and more continuation
2. Second step
   also with continuation
   and even more continuation
- Another bullet point
  with continuation
  and final continuation
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == [
        "First step with continuation and more continuation",
        "Bullet point with continuation and more continuation",
        "Second step also with continuation and even more continuation",
        "Another bullet point with continuation and final continuation"
    ]

@pytest.mark.asyncio
async def test_parse_test_cases_invalid_lines_between_mixed_steps(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with invalid lines between mixed format steps."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step
Invalid line
* Bullet point
Another invalid line
2. Second step
Yet another invalid line
- Another bullet point
Final invalid line
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == [
        "First step Invalid line",
        "Bullet point Another invalid line",
        "Second step Yet another invalid line",
        "Another bullet point Final invalid line"
    ] 

@pytest.mark.asyncio
async def test_parse_test_cases_complex_mixed_formats(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with complex mixed formats and edge cases."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step
   with continuation
   and more continuation
* Bullet point
  with continuation
  and more continuation
2. Second step
   also with continuation
   and even more continuation
- Another bullet point
  with continuation
  and final continuation
Invalid line without number or bullet
3. Third step
   with continuation
* Final bullet
  with continuation
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == [
        "First step with continuation and more continuation",
        "Bullet point with continuation and more continuation",
        "Second step also with continuation and even more continuation",
        "Another bullet point with continuation and final continuation Invalid line without number or bullet",
        "Third step with continuation",
        "Final bullet with continuation"
    ] 

@pytest.mark.asyncio
async def test_parse_test_cases_no_current_step(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with invalid lines before any step."""
    response = """Title: Test Case
Description: Description
Steps:
Invalid line before any step
1. First step
* Bullet point
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == ["First step", "Bullet point"]

@pytest.mark.asyncio
async def test_parse_test_cases_empty_continuation(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with empty continuation lines."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step

   with empty line in between
* Bullet point

  with empty line in between
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == ["First step with empty line in between", "Bullet point with empty line in between"]

@pytest.mark.asyncio
async def test_parse_test_cases_mixed_indentation(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with mixed indentation in continuations."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step
  indented continuation
    more indented continuation
* Bullet point
 less indented continuation
   more indented continuation
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 1
    test_case = test_cases[0]
    assert test_case.steps == [
        "First step indented continuation more indented continuation",
        "Bullet point less indented continuation more indented continuation"
    ] 

@pytest.mark.asyncio
async def test_parse_test_cases_complex_step_handling(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with complex step handling scenarios."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step
   with continuation
   and more continuation
* Bullet point
  with continuation
  and more continuation
2. Second step
   also with continuation
   and even more continuation
- Another bullet point
  with continuation
  and final continuation
Invalid line without number or bullet
3. Third step
   with continuation
* Final bullet
  with continuation
Expected Result: Result
---
Title: Test Case 2
Description: Description 2
Steps:
1. First step
   with continuation
   and more continuation
* Bullet point
  with continuation
  and more continuation
2. Second step
   also with continuation
   and even more continuation
- Another bullet point
  with continuation
  and final continuation
Invalid line without number or bullet
3. Third step
   with continuation
* Final bullet
  with continuation
Expected Result: Result"""
    
    test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 2
    for test_case in test_cases:
        assert test_case.steps == [
            "First step with continuation and more continuation",
            "Bullet point with continuation and more continuation",
            "Second step also with continuation and even more continuation",
            "Another bullet point with continuation and final continuation Invalid line without number or bullet",
            "Third step with continuation",
            "Final bullet with continuation"
        ]

@pytest.mark.asyncio
async def test_generate_test_suite_retry_success(generator: QASuiteGenerator, mock_model: Mock) -> None:
    """Test handling of model error with successful retry."""
    # First call raises exception, second call succeeds
    mock_model.generate_response.side_effect = [
        Exception("First error"),
        """Title: Test Case
Description: Description
Steps:
1. Step one
Expected Result: Result"""
    ]
    
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="Story",
        description="Description"
    )
    
    # Should use test case from second attempt
    assert len(test_suite.test_cases) == 1
    assert test_suite.test_cases[0].title == "Test Case"
    assert mock_model.generate_response.call_count == 2
    mock_model.generate_response.assert_has_calls([
        mock.call(generator._build_prompt("Story", "Description")),
        mock.call(generator._build_prompt("Story", "Description"))
    ]) 

@pytest.mark.asyncio
async def test_parse_test_cases_step_continuation_edge_cases(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with step continuation edge cases."""
    response = """Title: Test Case
Description: Description
Steps:
1. First step
   with continuation
   and more continuation
* Bullet point
  with continuation
  and more continuation
2. Second step
   also with continuation
   and even more continuation
- Another bullet point
  with continuation
  and final continuation
Invalid line without number or bullet
3. Third step
   with continuation
* Final bullet
  with continuation
Expected Result: Result
---
Title: Test Case 2
Description: Description 2
Steps:
1. First step
   with continuation
   and more continuation
* Bullet point
  with continuation
  and more continuation
2. Second step
   also with continuation
   and even more continuation
- Another bullet point
  with continuation
  and final continuation
Invalid line without number or bullet
3. Third step
   with continuation
* Final bullet
  with continuation
Expected Result: Result"""
    
    # Mock regex search to force specific branches
    with patch('re.search', side_effect=[
        mock.Mock(group=lambda x: "Test Case"),  # First title
        mock.Mock(group=lambda x: "Description"),  # First description
        mock.Mock(group=lambda x: "1. First step\n   with continuation\n   and more continuation\n* Bullet point\n  with continuation\n  and more continuation\n2. Second step\n   also with continuation\n   and even more continuation\n- Another bullet point\n  with continuation\n  and final continuation\nInvalid line without number or bullet\n3. Third step\n   with continuation\n* Final bullet\n  with continuation"),  # First steps
        mock.Mock(group=lambda x: "Result"),  # First result
        mock.Mock(group=lambda x: "Test Case 2"),  # Second title
        mock.Mock(group=lambda x: "Description 2"),  # Second description
        mock.Mock(group=lambda x: "1. First step\n   with continuation\n   and more continuation\n* Bullet point\n  with continuation\n  and more continuation\n2. Second step\n   also with continuation\n   and even more continuation\n- Another bullet point\n  with continuation\n  and final continuation\nInvalid line without number or bullet\n3. Third step\n   with continuation\n* Final bullet\n  with continuation"),  # Second steps
        mock.Mock(group=lambda x: "Result"),  # Second result
    ]):
        test_cases = generator._parse_test_cases(response)
    
    assert len(test_cases) == 2
    for test_case in test_cases:
        assert test_case.steps == [
            "First step with continuation and more continuation",
            "Bullet point with continuation and more continuation",
            "Second step also with continuation and even more continuation",
            "Another bullet point with continuation and final continuation Invalid line without number or bullet",
            "Third step with continuation",
            "Final bullet with continuation"
        ]

@pytest.mark.asyncio
async def test_generate_test_suite_retry_edge_cases(generator: QASuiteGenerator, mock_model: Mock) -> None:
    """Test handling of model error with various retry scenarios."""
    # First call raises exception, second call succeeds with empty response, third call succeeds
    mock_model.generate_response.side_effect = [
        Exception("First error"),
        """Title: Test Case
Description: Description
Steps:
1. Step one
Expected Result: Result"""
    ]
    
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="Story",
        description="Description"
    )
    
    # Should use test case from second attempt
    assert len(test_suite.test_cases) == 1
    assert test_suite.test_cases[0].title == "Test Case"
    assert mock_model.generate_response.call_count == 2  # Only retries once
    mock_model.generate_response.assert_has_calls([
        mock.call(generator._build_prompt("Story", "Description")),
        mock.call(generator._build_prompt("Story", "Description"))
    ]) 

@pytest.mark.asyncio
async def test_parse_test_cases_step_continuation_branches(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test parsing test cases with step continuations and branching scenarios."""
    response = """Title: Test Case
Description: Test description
Steps:
1. First step
   with continuation
2. Second step
   with continuation
   and more lines
Expected Result: Expected outcome"""
    
    test_cases = generator._parse_test_cases(response)
    
    # Verify test case was parsed successfully
    assert len(test_cases) > 0
    test_case = test_cases[0]
    
    # Verify test case has expected structure
    assert test_case.title == "Test Case"
    assert test_case.description == "Test description"
    assert len(test_case.steps) > 0
    assert test_case.expected_result == "Expected outcome"
    
    # Verify steps contain the continuations
    assert any("continuation" in step for step in test_case.steps)

@pytest.mark.asyncio
async def test_generate_test_suite_retry_branches(generator: QASuiteGenerator, mock_model: Mock) -> None:
    """Test test suite generation with retry logic and branching scenarios."""
    # Mock model to fail first then succeed
    mock_model.generate_response.side_effect = [
        Exception("First attempt failed"),
        """Title: Test Story
Description: Test basic functionality
Steps:
1. Step one
2. Step two
Expected Result: Expected outcome"""
    ]
    
    # Generate test suite
    test_suite = await generator.generate_test_suite(
        story_id="story-1",
        title="Story Title",
        description="Story description"
    )
    
    # Verify test suite was generated with valid test cases
    assert len(test_suite.test_cases) > 0
    assert all(test_case.title and test_case.description and test_case.steps and test_case.expected_result 
              for test_case in test_suite.test_cases)
    
    # Verify model was called twice due to retry
    assert mock_model.generate_response.call_count == 2 

@pytest.mark.asyncio
async def test_parse_test_cases_empty_response(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test handling of empty response from model."""
    # Test with completely empty response
    test_cases = generator._parse_test_cases("")
    assert len(test_cases) == 0
    mock_base_logger.warning.assert_called_once()

    # Test with whitespace only
    test_cases = generator._parse_test_cases("   \n   \t   ")
    assert len(test_cases) == 0
    assert mock_base_logger.warning.call_count == 2

@pytest.mark.asyncio
async def test_parse_test_cases_malformed_separators(generator: QASuiteGenerator, mock_base_logger: Mock) -> None:
    """Test handling of malformed test case separators."""
    response = """Title: Test Case 1
Description: Description 1
Steps:
1. Step one
Expected Result: Result 1
--  # Malformed separator
Title: Test Case 2
Description: Description 2
Steps:
1. Step two
Expected Result: Result 2
----  # Extra long separator
Title: Test Case 3
Description: Description 3
Steps:
1. Step three
Expected Result: Result 3"""

    test_cases = generator._parse_test_cases(response)
    
    # Should still parse all valid test cases
    assert len(test_cases) == 3
    assert [tc.title for tc in test_cases] == ["Test Case 1", "Test Case 2", "Test Case 3"]
    
    # Verify warning was logged for malformed separators
    assert mock_base_logger.warning.call_count > 0 