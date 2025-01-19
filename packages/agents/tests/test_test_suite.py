"""Unit tests for test suite model functionality."""
import pytest
from unittest.mock import Mock, patch
from core.models import Task
from agent_qa.models import TestSuite, TestCase, TestResult

@pytest.fixture
def sample_test_cases():
    """Create sample test cases for testing."""
    return [
        TestCase(
            id="test-1",
            title="Test User Creation",
            description="Test user model creation functionality",
            type="unit",
            priority="high",
            metadata={"coverage_target": "models.user"}
        ),
        TestCase(
            id="test-2",
            title="Test User API",
            description="Test user API endpoints",
            type="integration",
            priority="medium",
            metadata={"coverage_target": "api.user"}
        ),
        TestCase(
            id="test-3",
            title="Test User Interface",
            description="Test user interface components",
            type="e2e",
            priority="low",
            metadata={"coverage_target": "ui.user"}
        )
    ]

@pytest.fixture
def test_suite(sample_test_cases):
    """Create a test suite instance."""
    return TestSuite(
        id="suite-1",
        title="User System Tests",
        description="Test suite for user system",
        test_cases=sample_test_cases,
        metadata={"priority": "high"}
    )

def test_test_suite_creation(test_suite, sample_test_cases):
    """Test test suite creation."""
    assert test_suite.id == "suite-1"
    assert test_suite.title == "User System Tests"
    assert len(test_suite.test_cases) == 3
    assert test_suite.metadata["priority"] == "high"

def test_add_test_case(test_suite):
    """Test adding a test case to suite."""
    new_case = TestCase(
        id="test-4",
        title="Test User Deletion",
        description="Test user deletion functionality",
        type="unit",
        priority="high",
        metadata={"coverage_target": "models.user"}
    )
    
    test_suite.add_test_case(new_case)
    assert len(test_suite.test_cases) == 4
    assert test_suite.test_cases[-1].id == "test-4"

def test_remove_test_case(test_suite):
    """Test removing a test case from suite."""
    test_suite.remove_test_case("test-1")
    assert len(test_suite.test_cases) == 2
    assert all(tc.id != "test-1" for tc in test_suite.test_cases)

def test_get_test_case(test_suite):
    """Test retrieving a test case from suite."""
    test_case = test_suite.get_test_case("test-1")
    assert test_case is not None
    assert test_case.id == "test-1"
    
    test_case = test_suite.get_test_case("nonexistent")
    assert test_case is None

def test_filter_test_cases(test_suite):
    """Test filtering test cases."""
    unit_tests = test_suite.filter_test_cases(type="unit")
    assert len(unit_tests) == 1
    assert unit_tests[0].id == "test-1"
    
    high_priority = test_suite.filter_test_cases(priority="high")
    assert len(high_priority) == 1
    assert high_priority[0].id == "test-1"

def test_get_coverage_targets(test_suite):
    """Test getting coverage targets."""
    targets = test_suite.get_coverage_targets()
    assert len(targets) == 3
    assert "models.user" in targets
    assert "api.user" in targets
    assert "ui.user" in targets

def test_calculate_coverage(test_suite):
    """Test coverage calculation."""
    results = [
        TestResult(
            test_case_id="test-1",
            status="passed",
            coverage=80.0,
            metadata={}
        ),
        TestResult(
            test_case_id="test-2",
            status="passed",
            coverage=90.0,
            metadata={}
        ),
        TestResult(
            test_case_id="test-3",
            status="failed",
            coverage=0.0,
            metadata={}
        )
    ]
    
    coverage = test_suite.calculate_coverage(results)
    assert coverage == pytest.approx(56.67, rel=0.01)

def test_get_test_status(test_suite):
    """Test getting test status."""
    results = [
        TestResult(
            test_case_id="test-1",
            status="passed",
            coverage=80.0,
            metadata={}
        ),
        TestResult(
            test_case_id="test-2",
            status="failed",
            coverage=0.0,
            metadata={"error": "API error"}
        )
    ]
    
    status = test_suite.get_test_status(results)
    assert status == "failed"
    assert status != "passed"

def test_merge_test_suites(test_suite):
    """Test merging test suites."""
    other_cases = [
        TestCase(
            id="test-4",
            title="Test User Search",
            description="Test user search functionality",
            type="integration",
            priority="medium",
            metadata={"coverage_target": "api.search"}
        )
    ]
    
    other_suite = TestSuite(
        id="suite-2",
        title="User Search Tests",
        description="Test suite for user search",
        test_cases=other_cases,
        metadata={"priority": "medium"}
    )
    
    merged = test_suite.merge(other_suite)
    assert len(merged.test_cases) == 4
    assert any(tc.id == "test-4" for tc in merged.test_cases)

def test_validate_test_suite(test_suite):
    """Test test suite validation."""
    assert test_suite.validate()
    
    # Test with invalid test case
    invalid_case = TestCase(
        id="",  # Invalid empty ID
        title="Invalid Test",
        description="Invalid test case",
        type="unknown",  # Invalid type
        priority="invalid",  # Invalid priority
        metadata={}
    )
    
    with pytest.raises(ValueError):
        TestSuite(
            id="invalid-suite",
            title="Invalid Suite",
            description="Invalid test suite",
            test_cases=[invalid_case],
            metadata={}
        ) 