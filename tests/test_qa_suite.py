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
    
    # Reset and mark as failed
    test_case.start_execution()
    test_case.mark_failed("Login failed", 0.5)
    assert test_case.status == TestStatus.FAILED
    assert test_case.actual_result == "Login failed"
    assert test_case.execution_time == 0.5
    assert test_case.error_details is None
    
    # Reset and mark as error
    test_case.start_execution()
    error = ValueError("Invalid credentials")
    test_case.mark_error(error)
    assert test_case.status == TestStatus.ERROR
    assert test_case.error_details == {
        "type": "ValueError",
        "message": "Invalid credentials"
    }
    
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
    
    # All passed
    test_case2.mark_passed("Actual 2", 1.0)
    assert test_suite.get_status() == TestStatus.PASSED
    
    # One failed
    test_case2.mark_failed("Failed", 1.0)
    assert test_suite.get_status() == TestStatus.FAILED
    
    # One error
    test_case2.mark_error(ValueError("Error"))
    assert test_suite.get_status() == TestStatus.ERROR 