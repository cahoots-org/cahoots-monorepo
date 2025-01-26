"""QA suite models."""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

class QATestType(Enum):
    """Test type enum."""
    API = "api"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"

class TestStatus(Enum):
    """Test status enum."""
    __test__ = False
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"

class QATestStatus(Enum):
    """QA test status enum."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    BLOCKED = "blocked"

class TestStep(BaseModel):
    """Test step model."""
    __test__ = False  # Prevent pytest from collecting this as a test class
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "step1",
                "description": "Enter valid credentials",
                "expected_result": "User is logged in successfully",
                "status": "not_started",
                "actual_result": None,
                "error_details": None
            }
        }
    )
    
    id: str
    description: str
    expected_result: str
    status: TestStatus = TestStatus.NOT_STARTED
    actual_result: Optional[str] = None
    error_details: Optional[Dict[str, str]] = None
    
    @field_validator('id', 'description', 'expected_result')
    def validate_string_fields(cls, v: str) -> str:
        if not v:
            raise ValueError("Field must not be empty")
        return v

class QATest(BaseModel):
    """QA test model."""
    id: UUID
    name: str
    description: str
    test_type: QATestType
    steps: List[Dict[str, Any]]

class QATestSuite(BaseModel):
    """QA test suite model."""
    id: UUID
    name: str
    description: str
    test_type: QATestType
    tests: List[QATest]
    parallel: bool = False

class QASuite(BaseModel):
    """QA suite model."""
    id: UUID
    name: str
    description: str
    test_suites: List[QATestSuite]
    context: Dict[str, Any]

class QATestResult(BaseModel):
    """Test result model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_case_title": "Login Test",
                "status": "passed",
                "actual_result": "User successfully logged in",
                "execution_time": 1.23,
                "error_details": None
            }
        }
    )
    
    test_case_title: str
    status: TestStatus
    actual_result: Optional[str] = None
    execution_time: Optional[float] = None
    error_details: Optional[Dict[str, str]] = None

class TestCase(BaseModel):
    """Test case model."""
    __test__ = False
    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Allow Exception and other arbitrary types
        json_schema_extra={
            "example": {
                "id": "test1",
                "title": "Login Test",
                "description": "Test user login functionality",
                "steps": [
                    {
                        "id": "step1",
                        "description": "Enter valid credentials",
                        "expected_result": "User is logged in successfully"
                    }
                ],
                "metadata": {
                    "priority": "high",
                    "type": "functional"
                },
                "status": "not_started"
            }
        }
    )
    
    id: str
    title: str
    description: str
    steps: List[TestStep]
    metadata: Dict[str, Any] = {}
    status: TestStatus = TestStatus.NOT_STARTED
    actual_result: Optional[str] = None
    execution_time: Optional[float] = None
    error_details: Optional[Dict[str, str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[Exception] = None  # Store the raw error object
    
    @field_validator('id', 'title', 'description')
    def validate_string_fields(cls, v: str) -> str:
        if not v:
            raise ValueError("Field must not be empty")
        return v
    
    @field_validator('steps')
    def validate_steps(cls, v: List[TestStep]) -> List[TestStep]:
        if not v:
            raise ValueError("Steps must not be empty")
        return v
        
    def reset(self) -> None:
        """Reset test case to initial state."""
        self.status = TestStatus.NOT_STARTED
        self.actual_result = None
        self.execution_time = None
        self.error_details = None
        self.start_time = None
        self.end_time = None
        self.error = None
        
    def start_execution(self) -> None:
        """Mark test as running."""
        if self.status == TestStatus.RUNNING:
            raise ValueError("Test is already running")
        if self.status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR]:
            raise ValueError(f"Cannot start execution from {self.status.value} state")
            
        self.reset()  # Reset state before starting
        self.status = TestStatus.RUNNING
        self.start_time = datetime.now()
        
    def mark_passed(self, actual_result: str, execution_time: float) -> None:
        """Mark test as passed."""
        if self.status != TestStatus.RUNNING:
            raise ValueError("Cannot mark as passed - test is not running")
            
        self.status = TestStatus.PASSED
        self.actual_result = actual_result
        self.execution_time = execution_time
        self.error_details = None
        self.error = None
        self.end_time = datetime.now()
        
    def mark_failed(self, actual_result: str, execution_time: float) -> None:
        """Mark test as failed."""
        if self.status != TestStatus.RUNNING:
            raise ValueError("Cannot mark as failed - test is not running")
            
        self.status = TestStatus.FAILED
        self.actual_result = actual_result
        self.execution_time = execution_time
        self.error_details = None
        self.error = None
        self.end_time = datetime.now()
        
    def mark_error(self, error: Exception | str) -> None:
        """Mark test as errored."""
        if self.status != TestStatus.RUNNING:
            raise ValueError("Cannot mark as error - test is not running")
            
        self.status = TestStatus.ERROR
        error_msg = str(error)
        self.actual_result = error_msg
        if isinstance(error, Exception):
            self.error = error  # Store the raw error
            self.error_details = {
                "type": error.__class__.__name__,
                "message": error_msg
            }
        else:
            self.error = None
            self.error_details = {
                "type": "Error",
                "message": error_msg
            }
        self.end_time = datetime.now()

    def to_dict(self) -> Dict:
        """Convert test case to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "expected_result": self.steps[-1].expected_result if self.steps else None,
            "status": self.status.value,
            "actual_result": self.actual_result,
            "execution_time": self.execution_time,
            "error_details": self.error_details,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestCase':
        """Create test case from dictionary."""
        if "start_time" in data and data["start_time"]:
            data["start_time"] = datetime.fromisoformat(data["start_time"])
        if "end_time" in data and data["end_time"]:
            data["end_time"] = datetime.fromisoformat(data["end_time"])
        return cls(**data)

class TestSuite(BaseModel):
    """Test suite model."""
    __test__ = False
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
    test_cases: List[TestCase] = []  # Default to empty list
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
            raise ValueError("Test suite must contain at least one test case")
        return v
        
    def add_test_case(self, test_case: TestCase) -> None:
        """Add a test case to the suite."""
        # Check for duplicate test case
        if test_case in self.test_cases:
            raise ValueError("Test case already exists in suite")
            
        # Check for duplicate title
        if any(tc.title == test_case.title for tc in self.test_cases):
            raise ValueError(f"Test case with title '{test_case.title}' already exists")
            
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
        """Get overall suite status.
        
        Returns:
            TestStatus: The overall status of the test suite based on the following rules:
            - ERROR if any test has errored
            - RUNNING if any test is running
            - FAILED if any test has failed
            - PASSED if all tests have passed
            - NOT_STARTED if any test is not started or if there are no tests
        """
        if not self.test_cases:
            return TestStatus.NOT_STARTED
            
        statuses = [tc.status for tc in self.test_cases]
        
        if TestStatus.ERROR in statuses:
            return TestStatus.ERROR
        if TestStatus.RUNNING in statuses:
            return TestStatus.RUNNING
        if TestStatus.FAILED in statuses:
            return TestStatus.FAILED
        if all(s == TestStatus.PASSED for s in statuses):
            return TestStatus.PASSED
        return TestStatus.NOT_STARTED 

    def to_dict(self) -> Dict:
        """Convert test suite to dictionary."""
        return {
            "story_id": self.story_id,
            "title": self.title,
            "description": self.description,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestSuite':
        """Create test suite from dictionary."""
        # Convert test cases
        if "test_cases" in data:
            data["test_cases"] = [TestCase.from_dict(tc) for tc in data["test_cases"]]
            
        # Convert timestamps
        if "created_at" in data and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and data["updated_at"]:
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            
        return cls(**data) 

class QASuite(BaseModel):
    """QA suite model that contains multiple test suites."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "project-123",
                "title": "Project QA Suite",
                "description": "Complete QA suite for the project",
                "test_suites": [
                    {
                        "story_id": "story-123",
                        "title": "Login Test Suite",
                        "description": "Test suite for login functionality",
                        "test_cases": []
                    }
                ],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
    )
    
    project_id: str
    title: str
    description: str
    test_suites: List[TestSuite] = []
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    @field_validator('project_id', 'title', 'description')
    def validate_string_fields(cls, v: str) -> str:
        if not v:
            raise ValueError("Field must not be empty")
        return v
        
    @field_validator('test_suites')
    def validate_test_suites(cls, v: List[TestSuite]) -> List[TestSuite]:
        if not v:
            raise ValueError("QA suite must contain at least one test suite")
        return v
        
    def add_test_suite(self, test_suite: TestSuite) -> None:
        """Add a test suite."""
        if test_suite in self.test_suites:
            raise ValueError("Test suite already exists")
        if any(ts.title == test_suite.title for ts in self.test_suites):
            raise ValueError(f"Test suite with title '{test_suite.title}' already exists")
        self.test_suites.append(test_suite)
        self.updated_at = datetime.now()
    
    def remove_test_suite(self, title: str) -> None:
        """Remove a test suite."""
        self.test_suites = [ts for ts in self.test_suites if ts.title != title]
        self.updated_at = datetime.now()
    
    def get_test_suite(self, title: str) -> Optional[TestSuite]:
        """Get test suite by title."""
        for test_suite in self.test_suites:
            if test_suite.title == title:
                return test_suite
        return None
    
    def get_status(self) -> TestStatus:
        """Get overall QA suite status."""
        if not self.test_suites:
            return TestStatus.NOT_STARTED
            
        statuses = [ts.get_status() for ts in self.test_suites]
        if TestStatus.ERROR in statuses:
            return TestStatus.ERROR
        if TestStatus.RUNNING in statuses:
            return TestStatus.RUNNING
        if TestStatus.FAILED in statuses:
            return TestStatus.FAILED
        if all(s == TestStatus.PASSED for s in statuses):
            return TestStatus.PASSED
        return TestStatus.NOT_STARTED 

class QATestSuiteResult(BaseModel):
    """QA test suite result model."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suite_id": "suite-123",
                "status": "passed",
                "test_results": [],
                "execution_time": 1.23,
                "error_details": None
            }
        }
    )
    
    suite_id: UUID
    status: TestStatus
    test_results: List[QATestResult] = []
    execution_time: Optional[float] = None
    error_details: Optional[Dict[str, str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None 