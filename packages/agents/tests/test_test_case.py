"""Unit tests for test case validation functionality."""
import pytest
from unittest.mock import Mock, patch
from agent_qa.models import TestCase, TestResult
from agent_qa.validation import TestCaseValidator

@pytest.fixture
def test_case_validator():
    """Create a test case validator instance."""
    return TestCaseValidator()

@pytest.fixture
def sample_test_cases():
    """Create sample test cases for testing."""
    return [
        TestCase(
            id="test-1",
            title="Test User Model",
            description="Test user model validation",
            type="unit",
            priority="high",
            metadata={"validation_rules": ["required_fields", "unique_email"]}
        ),
        TestCase(
            id="test-2",
            title="Test API Response",
            description="Test API response format",
            type="integration",
            priority="medium",
            metadata={"validation_rules": ["status_code", "response_schema"]}
        ),
        TestCase(
            id="test-3",
            title="Test Form Submission",
            description="Test form validation",
            type="e2e",
            priority="low",
            metadata={"validation_rules": ["required_inputs", "error_messages"]}
        )
    ]

def test_validate_test_case_id(test_case_validator, sample_test_cases):
    """Test validation of test case ID."""
    assert test_case_validator.validate_id(sample_test_cases[0].id)
    
    with pytest.raises(ValueError):
        test_case_validator.validate_id("")
    
    with pytest.raises(ValueError):
        test_case_validator.validate_id("invalid id")

def test_validate_test_case_type(test_case_validator, sample_test_cases):
    """Test validation of test case type."""
    assert test_case_validator.validate_type(sample_test_cases[0].type)
    
    with pytest.raises(ValueError):
        test_case_validator.validate_type("unknown")
    
    with pytest.raises(ValueError):
        test_case_validator.validate_type("")

def test_validate_test_case_priority(test_case_validator, sample_test_cases):
    """Test validation of test case priority."""
    assert test_case_validator.validate_priority(sample_test_cases[0].priority)
    
    with pytest.raises(ValueError):
        test_case_validator.validate_priority("critical")
    
    with pytest.raises(ValueError):
        test_case_validator.validate_priority("")

def test_validate_test_case_metadata(test_case_validator, sample_test_cases):
    """Test validation of test case metadata."""
    assert test_case_validator.validate_metadata(sample_test_cases[0].metadata)
    
    with pytest.raises(ValueError):
        test_case_validator.validate_metadata({"invalid_key": []})
    
    with pytest.raises(ValueError):
        test_case_validator.validate_metadata({"validation_rules": "not_a_list"})

def test_validate_test_case_dependencies(test_case_validator):
    """Test validation of test case dependencies."""
    test_case = TestCase(
        id="test-4",
        title="Test User Deletion",
        description="Test user deletion with dependencies",
        type="integration",
        priority="high",
        metadata={
            "dependencies": ["test-1", "test-2"],
            "validation_rules": ["user_exists"]
        }
    )
    
    assert test_case_validator.validate_dependencies(test_case.metadata.get("dependencies"))
    
    with pytest.raises(ValueError):
        test_case_validator.validate_dependencies([""])
    
    with pytest.raises(ValueError):
        test_case_validator.validate_dependencies("not_a_list")

def test_validate_test_case_prerequisites(test_case_validator):
    """Test validation of test case prerequisites."""
    test_case = TestCase(
        id="test-5",
        title="Test User Update",
        description="Test user update with prerequisites",
        type="integration",
        priority="medium",
        metadata={
            "prerequisites": ["user_created", "user_authenticated"],
            "validation_rules": ["user_exists"]
        }
    )
    
    assert test_case_validator.validate_prerequisites(test_case.metadata.get("prerequisites"))
    
    with pytest.raises(ValueError):
        test_case_validator.validate_prerequisites([""])
    
    with pytest.raises(ValueError):
        test_case_validator.validate_prerequisites("not_a_list")

def test_validate_test_case_validation_rules(test_case_validator, sample_test_cases):
    """Test validation of test case validation rules."""
    assert test_case_validator.validate_validation_rules(
        sample_test_cases[0].metadata["validation_rules"]
    )
    
    with pytest.raises(ValueError):
        test_case_validator.validate_validation_rules(["invalid_rule"])
    
    with pytest.raises(ValueError):
        test_case_validator.validate_validation_rules("not_a_list")

def test_validate_test_case_expected_results(test_case_validator):
    """Test validation of test case expected results."""
    test_case = TestCase(
        id="test-6",
        title="Test User Login",
        description="Test user login with expected results",
        type="integration",
        priority="high",
        metadata={
            "expected_results": {
                "status_code": 200,
                "response": {"token": "string", "user_id": "string"}
            },
            "validation_rules": ["response_format"]
        }
    )
    
    assert test_case_validator.validate_expected_results(
        test_case.metadata.get("expected_results")
    )
    
    with pytest.raises(ValueError):
        test_case_validator.validate_expected_results([])
    
    with pytest.raises(ValueError):
        test_case_validator.validate_expected_results({"invalid": None})

def test_validate_complete_test_case(test_case_validator, sample_test_cases):
    """Test complete validation of test case."""
    assert test_case_validator.validate(sample_test_cases[0])
    
    invalid_case = TestCase(
        id="",
        title="",
        description="",
        type="unknown",
        priority="invalid",
        metadata={"validation_rules": "not_a_list"}
    )
    
    with pytest.raises(ValueError):
        test_case_validator.validate(invalid_case)

def test_validate_test_case_result(test_case_validator):
    """Test validation of test case result."""
    result = TestResult(
        test_case_id="test-1",
        status="passed",
        coverage=85.5,
        metadata={"execution_time": 1.2}
    )
    
    assert test_case_validator.validate_result(result)
    
    invalid_result = TestResult(
        test_case_id="",
        status="unknown",
        coverage=-1.0,
        metadata={}
    )
    
    with pytest.raises(ValueError):
        test_case_validator.validate_result(invalid_result) 