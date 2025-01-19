"""Tests for QA suite models."""
import pytest
from datetime import datetime
from src.models.qa_suite import TestCase, TestSuite, QAResult, TestStatus

def test_test_case_validation():
    """Test validation of test case fields."""
    # Valid test case
    test_case = TestCase(
        title="Test Login",
        description="Test user login functionality",
        steps=["Enter credentials", "Click login"],
        expected_result="User is logged in"
    )
    assert test_case.title == "Test Login"
    assert test_case.status == TestStatus.NOT_STARTED
    
    # Empty title
    with pytest.raises(ValueError):
        TestCase(
            title="",
            description="Test description",
            steps=["Step 1"],
            expected_result="Expected"
        )
        
    # Empty steps
    with pytest.raises(ValueError):
        TestCase(
            title="Test",
            description="Test description",
            steps=[],
            expected_result="Expected"
        )
        
def test_test_case_execution():
    """Test test case execution state changes."""
    test_case = TestCase(
        title="Test Login",
        description="Test user login functionality",
        steps=["Enter credentials", "Click login"],
        expected_result="User is logged in"
    )
    
    # Initial state
    assert test_case.status == TestStatus.NOT_STARTED
    assert test_case.actual_result is None
    assert test_case.execution_time is None
    assert test_case.error_details is None
    
    # Start execution
    test_case.start_execution()
    assert test_case.status == TestStatus.RUNNING
    
    # Mark as passed
    test_case.mark_passed("User is logged in", 1.23)
    assert test_case.status == TestStatus.PASSED
    assert test_case.actual_result == "User is logged in"
    assert test_case.execution_time == 1.23
    assert test_case.error_details is None
    
    # Create new test case for failure path
    test_case = TestCase(
        title="Test Login",
        description="Test user login functionality",
        steps=["Enter credentials", "Click login"],
        expected_result="User is logged in"
    )
    
    # Start execution
    test_case.start_execution()
    
    # Mark as failed
    test_case.mark_failed("Login failed", 0.5)
    assert test_case.status == TestStatus.FAILED
    assert test_case.actual_result == "Login failed"
    assert test_case.execution_time == 0.5
    assert test_case.error_details is None
    
    # Create new test case for error path
    test_case = TestCase(
        title="Test Login",
        description="Test user login functionality",
        steps=["Enter credentials", "Click login"],
        expected_result="User is logged in"
    )
    
    # Start execution
    test_case.start_execution()
    
    # Mark as error
    error = ValueError("Invalid credentials")
    test_case.mark_error(error)
    assert test_case.status == TestStatus.ERROR
    assert test_case.error_details == {
        "type": "ValueError",
        "message": "Invalid credentials"
    }

def test_test_case_execution_timing():
    """Test execution timing of test cases."""
    test_case = TestCase(
        title="Test Timing",
        description="Test execution timing",
        steps=["Step 1"],
        expected_result="Expected"
    )
    
    # Initial state
    assert test_case.execution_time is None
    assert test_case.start_time is None
    assert test_case.end_time is None
    
    # Start execution
    test_case.start_execution()
    assert test_case.start_time is not None
    assert test_case.end_time is None
    assert test_case.execution_time is None
    
    # Mark as passed
    test_case.mark_passed("Actual", 1.5)
    assert test_case.end_time is not None
    assert test_case.execution_time == 1.5
    assert test_case.end_time > test_case.start_time

def test_test_case_invalid_transitions():
    """Test invalid test case status transitions."""
    test_case = TestCase(
        title="Test Transitions",
        description="Test status transitions",
        steps=["Step 1"],
        expected_result="Expected"
    )
    
    # Cannot mark as passed without starting
    with pytest.raises(ValueError):
        test_case.mark_passed("Actual", 1.0)
    
    # Cannot mark as failed without starting
    with pytest.raises(ValueError):
        test_case.mark_failed("Failed", 1.0)
    
    # Cannot mark as error without starting
    with pytest.raises(ValueError):
        test_case.mark_error(ValueError("Error"))
    
    # Start execution
    test_case.start_execution()
    
    # Cannot start again while running
    with pytest.raises(ValueError):
        test_case.start_execution()
    
    # Mark as passed
    test_case.mark_passed("Actual", 1.0)
    
    # Cannot transition from terminal state
    with pytest.raises(ValueError):
        test_case.mark_failed("Failed", 1.0)
    with pytest.raises(ValueError):
        test_case.mark_error(ValueError("Error"))
    with pytest.raises(ValueError):
        test_case.start_execution()
    
def test_test_suite_validation():
    """Test validation of test suite fields."""
    test_case = TestCase(
        title="Test Login",
        description="Test user login functionality",
        steps=["Enter credentials", "Click login"],
        expected_result="User is logged in"
    )
    
    # Valid test suite
    test_suite = TestSuite(
        story_id="STORY-123",
        title="Login Test Suite",
        description="Test suite for login functionality",
        test_cases=[test_case]
    )
    assert test_suite.story_id == "STORY-123"
    assert len(test_suite.test_cases) == 1
    
    # Empty story ID
    with pytest.raises(ValueError):
        TestSuite(
            story_id="",
            title="Test Suite",
            description="Description",
            test_cases=[test_case]
        )
        
    # No test cases
    with pytest.raises(ValueError):
        TestSuite(
            story_id="STORY-123",
            title="Test Suite",
            description="Description",
            test_cases=[]
        )
        
def test_test_suite_management():
    """Test test suite management functions."""
    test_case1 = TestCase(
        title="Test Login",
        description="Test user login functionality",
        steps=["Enter credentials", "Click login"],
        expected_result="User is logged in"
    )
    
    test_case2 = TestCase(
        title="Test Logout",
        description="Test user logout functionality",
        steps=["Click logout"],
        expected_result="User is logged out"
    )
    
    test_suite = TestSuite(
        story_id="STORY-123",
        title="Login Test Suite",
        description="Test suite for login functionality",
        test_cases=[test_case1]
    )
    
    # Add test case
    test_suite.add_test_case(test_case2)
    assert len(test_suite.test_cases) == 2
    
    # Get test case
    found_case = test_suite.get_test_case("Test Login")
    assert found_case is test_case1
    
    # Remove test case
    test_suite.remove_test_case("Test Login")
    assert len(test_suite.test_cases) == 1
    assert test_suite.get_test_case("Test Login") is None
    
def test_test_suite_status():
    """Test test suite status calculation."""
    test_case1 = TestCase(
        title="Test 1",
        description="Test 1",
        steps=["Step 1"],
        expected_result="Expected 1"
    )
    
    test_case2 = TestCase(
        title="Test 2",
        description="Test 2",
        steps=["Step 2"],
        expected_result="Expected 2"
    )
    
    test_suite = TestSuite(
        story_id="STORY-123",
        title="Test Suite",
        description="Description",
        test_cases=[test_case1, test_case2]
    )
    
    # Initial state
    assert test_suite.get_status() == TestStatus.NOT_STARTED
    
    # One test running
    test_case1.start_execution()
    assert test_suite.get_status() == TestStatus.RUNNING
    
    # One passed, one not started
    test_case1.mark_passed("Actual 1", 1.0)
    assert test_suite.get_status() == TestStatus.NOT_STARTED
    
    # Start second test
    test_case2.start_execution()
    
    # All passed
    test_case2.mark_passed("Actual 2", 1.0)
    assert test_suite.get_status() == TestStatus.PASSED
    
    # Create new test suite for failure path
    test_case1 = TestCase(
        title="Test 1",
        description="Test 1",
        steps=["Step 1"],
        expected_result="Expected 1"
    )
    
    test_case2 = TestCase(
        title="Test 2",
        description="Test 2",
        steps=["Step 2"],
        expected_result="Expected 2"
    )
    
    test_suite = TestSuite(
        story_id="STORY-123",
        title="Test Suite",
        description="Description",
        test_cases=[test_case1, test_case2]
    )
    
    # Start and fail one test
    test_case1.start_execution()
    test_case1.mark_failed("Failed", 1.0)
    assert test_suite.get_status() == TestStatus.FAILED
    
    # Create new test suite for error path
    test_case1 = TestCase(
        title="Test 1",
        description="Test 1",
        steps=["Step 1"],
        expected_result="Expected 1"
    )
    
    test_case2 = TestCase(
        title="Test 2",
        description="Test 2",
        steps=["Step 2"],
        expected_result="Expected 2"
    )
    
    test_suite = TestSuite(
        story_id="STORY-123",
        title="Test Suite",
        description="Description",
        test_cases=[test_case1, test_case2]
    )
    
    # Start and error one test
    test_case1.start_execution()
    test_case1.mark_error(ValueError("Error"))
    assert test_suite.get_status() == TestStatus.ERROR

def test_test_case_status_transitions():
    """Test all possible test case status transitions."""
    test_case = TestCase(
        title="Status Test",
        description="Test status transitions",
        steps=["Step 1"],
        expected_result="Expected"
    )
    
    # Initial state
    assert test_case.status == TestStatus.NOT_STARTED
    assert test_case.actual_result is None
    assert test_case.execution_time is None
    
    # Start execution
    test_case.start_execution()
    assert test_case.status == TestStatus.RUNNING
    
    # Pass
    test_case.mark_passed("Test passed", 1.5)
    assert test_case.status == TestStatus.PASSED
    assert test_case.actual_result == "Test passed"
    assert test_case.execution_time == 1.5
    
    # Cannot transition from PASSED to RUNNING
    with pytest.raises(ValueError):
        test_case.start_execution()
    
    # Create new test case for failure path
    test_case = TestCase(
        title="Failure Test",
        description="Test failure transition",
        steps=["Step 1"],
        expected_result="Expected"
    )
    
    test_case.start_execution()
    test_case.mark_failed("Test failed", 0.5)
    assert test_case.status == TestStatus.FAILED
    assert test_case.actual_result == "Test failed"
    assert test_case.execution_time == 0.5
    
    # Create new test case for error path
    test_case = TestCase(
        title="Error Test",
        description="Test error transition",
        steps=["Step 1"],
        expected_result="Expected"
    )
    
    test_case.start_execution()
    error = ValueError("Test error")
    test_case.mark_error(error)
    assert test_case.status == TestStatus.ERROR
    assert isinstance(test_case.error, ValueError)
    assert str(test_case.error) == "Test error"

def test_test_suite_serialization():
    """Test serialization and deserialization of test suite."""
    test_case = TestCase(
        title="Test Case",
        description="Test description",
        steps=["Step 1", "Step 2"],
        expected_result="Expected result"
    )
    
    test_suite = TestSuite(
        story_id="STORY-123",
        title="Test Suite",
        description="Test description",
        test_cases=[test_case]
    )
    
    # Serialize
    serialized = test_suite.to_dict()
    assert isinstance(serialized, dict)
    assert serialized["story_id"] == "STORY-123"
    assert serialized["title"] == "Test Suite"
    assert isinstance(serialized["test_cases"], list)
    assert len(serialized["test_cases"]) == 1
    
    # Deserialize
    deserialized = TestSuite.from_dict(serialized)
    assert isinstance(deserialized, TestSuite)
    assert deserialized.story_id == test_suite.story_id
    assert deserialized.title == test_suite.title
    assert len(deserialized.test_cases) == len(test_suite.test_cases)
    
    # Verify test case was properly deserialized
    deserialized_case = deserialized.test_cases[0]
    assert deserialized_case.title == test_case.title
    assert deserialized_case.steps == test_case.steps
    assert deserialized_case.status == test_case.status

def test_test_suite_edge_cases():
    """Test edge cases in test suite management."""
    test_case = TestCase(
        title="Test Case",
        description="Description",
        steps=["Step 1"],
        expected_result="Expected"
    )
    
    test_suite = TestSuite(
        story_id="STORY-123",
        title="Test Suite",
        description="Description",
        test_cases=[test_case]
    )
    
    # Try to add duplicate test case
    with pytest.raises(ValueError):
        test_suite.add_test_case(test_case)
    
    # Try to add test case with duplicate title
    duplicate_case = TestCase(
        title="Test Case",  # Same title
        description="Different description",
        steps=["Different step"],
        expected_result="Different expected"
    )
    with pytest.raises(ValueError):
        test_suite.add_test_case(duplicate_case)
    
    # Try to remove non-existent test case
    test_suite.remove_test_case("Non-existent")  # Should not raise
    assert len(test_suite.test_cases) == 1
    
    # Try to get non-existent test case
    assert test_suite.get_test_case("Non-existent") is None
    
    # Verify original test case is unchanged
    assert test_suite.get_test_case("Test Case") is test_case 