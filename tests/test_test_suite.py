"""Tests for test suite models."""
import pytest
from datetime import datetime
from src.models.test_suite import TestCase, TestSuite, TestResult, TestStatus

def test_test_case_validation():
    """Test TestCase validation."""
    # Valid case
    test_case = TestCase(
        title="Test Login",
        description="Verify user login functionality",
        steps=["Enter credentials", "Click login"],
        expected_result="User is logged in"
    )
    
    # Should validate without errors
    assert test_case.model_dump()

    # Invalid cases
    with pytest.raises(ValueError):
        TestCase(
            title="",  # Empty title
            description="Test description",
            steps=["Step 1"],
            expected_result="Result"
        )

    with pytest.raises(ValueError):
        TestCase(
            title="Test Case",
            description="Test description",
            steps=[],  # Empty steps
            expected_result="Result"
        )

    with pytest.raises(ValueError):
        TestCase(
            title="Test Case",
            description="Test description",
            steps=["Step 1"],
            expected_result=""  # Empty expected result
        )

def test_test_case_execution():
    """Test TestCase execution flow."""
    test_case = TestCase(
        title="Test Feature",
        description="Test description",
        steps=["Step 1", "Step 2"],
        expected_result="Expected result"
    )

    # Initial state
    assert test_case.status == TestStatus.NOT_STARTED
    assert test_case.actual_result is None
    assert test_case.execution_time is None
    assert test_case.error_details is None

    # Start execution
    test_case.start_execution()
    assert test_case.status == TestStatus.RUNNING

    # Complete with success
    test_case.complete_execution("Expected result", 1.5)
    assert test_case.status == TestStatus.PASSED
    assert test_case.actual_result == "Expected result"
    assert test_case.execution_time == 1.5

    # Reset and complete with failure
    test_case.start_execution()
    test_case.complete_execution("Unexpected result", 1.0)
    assert test_case.status == TestStatus.FAILED
    assert test_case.actual_result == "Unexpected result"
    assert test_case.execution_time == 1.0

    # Test error handling
    test_case.start_execution()
    test_case.mark_error(ValueError("Test error"))
    assert test_case.status == TestStatus.ERROR
    assert test_case.error_details["type"] == "ValueError"
    assert test_case.error_details["message"] == "Test error"

def test_test_suite_validation():
    """Test TestSuite validation."""
    # Valid case
    test_case = TestCase(
        title="Test Case",
        description="Test description",
        steps=["Step 1"],
        expected_result="Result"
    )

    test_suite = TestSuite(
        story_id="story123",
        title="Login Test Suite",
        description="Login functionality tests",
        test_cases=[test_case]
    )
    
    # Should validate without errors
    assert test_suite.model_dump()

    # Invalid cases
    with pytest.raises(ValueError):
        TestSuite(
            story_id="",  # Empty story ID
            title="Test Suite",
            description="Test description",
            test_cases=[test_case]
        )

    with pytest.raises(ValueError):
        TestSuite(
            story_id="story123",
            title="",  # Empty title
            description="Test description",
            test_cases=[test_case]
        )

    with pytest.raises(ValueError):
        TestSuite(
            story_id="story123",
            title="Test Suite",
            description="Test description",
            test_cases=[]  # Empty test cases
        )

def test_test_suite_management():
    """Test TestSuite management functions."""
    test_case1 = TestCase(
        title="Test 1",
        description="First test",
        steps=["Step 1"],
        expected_result="Result 1"
    )

    test_case2 = TestCase(
        title="Test 2",
        description="Second test",
        steps=["Step 1"],
        expected_result="Result 2"
    )

    test_suite = TestSuite(
        story_id="story123",
        title="Test Suite",
        description="Test description",
        test_cases=[test_case1]
    )

    # Test adding test case
    test_suite.add_test_case(test_case2)
    assert len(test_suite.test_cases) == 2
    assert test_suite.get_test_case("Test 2") == test_case2

    # Test removing test case
    test_suite.remove_test_case("Test 1")
    assert len(test_suite.test_cases) == 1
    assert test_suite.get_test_case("Test 1") is None

def test_test_suite_status():
    """Test TestSuite status calculation."""
    test_case1 = TestCase(
        title="Test 1",
        description="First test",
        steps=["Step 1"],
        expected_result="Result 1"
    )

    test_case2 = TestCase(
        title="Test 2",
        description="Second test",
        steps=["Step 1"],
        expected_result="Result 2"
    )

    test_suite = TestSuite(
        story_id="story123",
        title="Test Suite",
        description="Test description",
        test_cases=[test_case1, test_case2]
    )

    # Initial state
    assert test_suite.get_status() == TestStatus.NOT_STARTED

    # One test running
    test_case1.start_execution()
    assert test_suite.get_status() == TestStatus.RUNNING

    # One passed, one not started
    test_case1.complete_execution("Result 1", 1.0)
    assert test_suite.get_status() == TestStatus.NOT_STARTED

    # All passed
    test_case2.complete_execution("Result 2", 1.0)
    assert test_suite.get_status() == TestStatus.PASSED

    # One failed
    test_case1.complete_execution("Wrong result", 1.0)
    assert test_suite.get_status() == TestStatus.FAILED

    # One error
    test_case2.mark_error(ValueError("Test error"))
    assert test_suite.get_status() == TestStatus.ERROR

def test_test_result():
    """Test TestResult functionality."""
    test_case = TestCase(
        title="Test Case",
        description="Test description",
        steps=["Step 1"],
        expected_result="Result"
    )

    result = TestResult(
        test_case=test_case,
        passed=True,
        details="Test passed successfully",
        execution_time=1.5,
        timestamp=datetime.now()
    )

    data = result.model_dump()
    assert data["passed"] is True
    assert data["details"] == "Test passed successfully"
    assert data["execution_time"] == 1.5
    assert "timestamp" in data 