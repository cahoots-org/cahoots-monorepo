"""Test suite models."""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict, field_validator

class TestStatus(Enum):
    """Test status enum."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"

class TestCase(BaseModel):
    """Test case model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Login Test",
                "description": "Test user login functionality",
                "steps": ["Enter credentials", "Click login"],
                "expected_result": "User is logged in",
                "status": "not_started"
            }
        }
    )
    
    title: str
    description: str
    steps: List[str]
    expected_result: str
    status: TestStatus = TestStatus.NOT_STARTED
    actual_result: Optional[str] = None
    execution_time: Optional[float] = None
    error_details: Optional[Dict[str, str]] = None
    
    @field_validator('title', 'description', 'expected_result')
    def validate_string_fields(cls, v: str) -> str:
        if not v:
            raise ValueError("Field must not be empty")
        return v
    
    @field_validator('steps')
    def validate_steps(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Steps must not be empty")
        if not all(step for step in v):
            raise ValueError("All steps must be non-empty strings")
        return v
        
    def start_execution(self) -> None:
        """Mark test as running."""
        self.status = TestStatus.RUNNING
        self.actual_result = None
        self.execution_time = None
        self.error_details = None
    
    def mark_passed(self, actual_result: str, execution_time: float) -> None:
        """Mark test as passed."""
        self.status = TestStatus.PASSED
        self.actual_result = actual_result
        self.execution_time = execution_time
        self.error_details = None
    
    def mark_failed(self, actual_result: str, execution_time: float) -> None:
        """Mark test as failed."""
        self.status = TestStatus.FAILED
        self.actual_result = actual_result
        self.execution_time = execution_time
        self.error_details = None
    
    def mark_error(self, error: Exception) -> None:
        """Mark test as errored."""
        self.status = TestStatus.ERROR
        if isinstance(error, Exception):
            self.error_details = {
                "type": error.__class__.__name__,
                "message": str(error)
            }
            
    def complete_execution(self, actual_result: str, execution_time: float) -> None:
        """Complete test execution.
        
        Args:
            actual_result: The actual test result
            execution_time: Time taken to execute test
        """
        if actual_result == self.expected_result:
            self.mark_passed(actual_result, execution_time)
        else:
            self.mark_failed(actual_result, execution_time)

class TestSuite(BaseModel):
    """Test suite model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "story_id": "story-123",
                "title": "Login Test Suite",
                "description": "Test suite for login functionality",
                "test_cases": [
                    {
                        "title": "Login Test",
                        "description": "Test user login functionality",
                        "steps": ["Enter credentials", "Click login"],
                        "expected_result": "User is logged in",
                        "status": "not_started"
                    }
                ],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
    
    story_id: str
    title: str
    description: str
    test_cases: List[TestCase]
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    @field_validator('story_id', 'title', 'description')
    def validate_string_fields(cls, v: str) -> str:
        if not v:
            raise ValueError("Field must not be empty")
        return v
    
    @field_validator('test_cases')
    def validate_test_cases(cls, v: List[TestCase]) -> List[TestCase]:
        if not v:
            raise ValueError("Test cases must not be empty")
        return v
        
    def add_test_case(self, test_case: TestCase) -> None:
        """Add a test case to the suite."""
        self.test_cases.append(test_case)
        self.updated_at = datetime.now()
    
    def remove_test_case(self, title: str) -> None:
        """Remove a test case from the suite."""
        self.test_cases = [tc for tc in self.test_cases if tc.title != title]
        self.updated_at = datetime.now()
    
    def get_test_case(self, title: str) -> Optional[TestCase]:
        """Get test case by title."""
        for test_case in self.test_cases:
            if test_case.title == title:
                return test_case
        return None
    
    def get_status(self) -> TestStatus:
        """Get overall suite status."""
        if not self.test_cases:
            return TestStatus.NOT_STARTED
            
        statuses = {tc.status for tc in self.test_cases}
        
        if TestStatus.ERROR in statuses:
            return TestStatus.ERROR
        if TestStatus.RUNNING in statuses:
            return TestStatus.RUNNING
        if TestStatus.FAILED in statuses:
            return TestStatus.FAILED
        if all(s == TestStatus.PASSED for s in statuses):
            return TestStatus.PASSED
        return TestStatus.NOT_STARTED

class TestResult(BaseModel):
    """Test result model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_case": {
                    "title": "Login Test",
                    "description": "Test user login functionality",
                    "steps": ["Enter credentials", "Click login"],
                    "expected_result": "User is logged in",
                    "status": "passed"
                },
                "passed": True,
                "details": "Test passed successfully",
                "execution_time": 1.23,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    )
    
    test_case: TestCase
    passed: bool
    details: str
    execution_time: float
    timestamp: datetime = datetime.now() 