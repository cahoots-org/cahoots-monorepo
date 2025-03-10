"""QA suite models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
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
                "error_details": None,
            }
        }
    )

    id: str
    description: str
    expected_result: str
    status: TestStatus = TestStatus.NOT_STARTED
    actual_result: Optional[str] = None
    error_details: Optional[Dict[str, str]] = None

    @field_validator("id", "description", "expected_result")
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
    steps: List[TestStep]
    status: TestStatus = TestStatus.NOT_STARTED
    error_details: Dict[str, str] = {}
    _is_running: bool = False

    def start_execution(self) -> None:
        """Start test execution."""
        self.status = TestStatus.RUNNING
        self._is_running = True

    def mark_passed(self) -> None:
        """Mark test as passed."""
        if not self._is_running:
            raise ValueError("Cannot mark as passed - test is not running")
        self.status = TestStatus.PASSED
        self._is_running = False

    def mark_failed(self, error: str) -> None:
        """Mark test as failed."""
        if not self._is_running:
            raise ValueError("Cannot mark as failed - test is not running")
        self.status = TestStatus.FAILED
        self.error_details = {"message": error}
        self._is_running = False

    def mark_error(self, error: str) -> None:
        """Mark test as errored."""
        if not self._is_running:
            raise ValueError("Cannot mark as error - test is not running")
        self.status = TestStatus.ERROR
        self.error_details = {"message": error}
        self._is_running = False


class QATestResult(BaseModel):
    """Test result model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_case_title": "Login Test",
                "status": "passed",
                "actual_result": "User successfully logged in",
                "execution_time": 1.23,
                "error_details": None,
            }
        }
    )

    test_case_title: str
    status: TestStatus
    actual_result: Optional[str] = None
    execution_time: Optional[float] = None
    error_details: Optional[Dict[str, str]] = None


class QATestCase:
    """A test case in a test suite."""

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        steps: List[TestStep],
        expected_result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.steps = steps
        self.expected_result = expected_result
        self.metadata = metadata or {}
        self.status = TestStatus.NOT_STARTED
        self.error_details = {}
        self._is_running = False

    def start_execution(self) -> None:
        """Start test execution."""
        self.status = TestStatus.RUNNING
        self._is_running = True

    def mark_passed(self) -> None:
        """Mark test as passed."""
        if not self._is_running:
            raise ValueError("Cannot mark as passed - test is not running")
        self.status = TestStatus.PASSED
        self._is_running = False

    def mark_failed(self, error: str) -> None:
        """Mark test as failed."""
        if not self._is_running:
            raise ValueError("Cannot mark as failed - test is not running")
        self.status = TestStatus.FAILED
        self.error_details = {"message": error}
        self._is_running = False

    def mark_error(self, error: str) -> None:
        """Mark test as errored."""
        if not self._is_running:
            raise ValueError("Cannot mark as error - test is not running")
        self.status = TestStatus.ERROR
        self.error_details = {"message": error}
        self._is_running = False

    def to_result(self) -> QATestResult:
        """Convert test case to test result."""
        return QATestResult(
            test_case_title=self.title,
            status=self.status,
            error_details=(
                self.error_details if self.status in [TestStatus.FAILED, TestStatus.ERROR] else None
            ),
        )


class QATestSuite(BaseModel):
    """Test suite model."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Allow TestCase and other custom types
        json_schema_extra={
            "example": {
                "id": "suite1",
                "title": "Authentication Test Suite",
                "description": "Test user authentication features",
                "test_cases": [],
                "metadata": {"priority": "high", "area": "security"},
            }
        },
    )

    id: UUID
    title: str
    description: str
    test_type: QATestType
    test_cases: List[QATestCase]
    metadata: Dict[str, Any] = {}
    status: TestStatus = TestStatus.NOT_STARTED
    execution_time: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    parallel: bool = False

    @field_validator("id", "title", "description")
    def validate_string_fields(cls, v: str) -> str:
        if not v:
            raise ValueError("Field must not be empty")
        return v

    def reset(self) -> None:
        """Reset test suite to initial state."""
        self.status = TestStatus.NOT_STARTED
        self.execution_time = None
        self.start_time = None
        self.end_time = None
        for test_case in self.test_cases:
            test_case.reset()

    def start_execution(self) -> None:
        """Mark test suite as running."""
        if self.status == TestStatus.RUNNING:
            raise ValueError("Test suite is already running")
        if self.status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR]:
            raise ValueError(f"Cannot start execution from {self.status.value} state")

        self.reset()  # Reset state before starting
        self.status = TestStatus.RUNNING
        self.start_time = datetime.now()

    def mark_completed(self, execution_time: float) -> None:
        """Mark test suite as completed."""
        if self.status != TestStatus.RUNNING:
            raise ValueError("Cannot mark as completed - test suite is not running")

        # Calculate overall status based on test cases
        failed = any(tc.status in [TestStatus.FAILED, TestStatus.ERROR] for tc in self.test_cases)
        self.status = TestStatus.FAILED if failed else TestStatus.PASSED
        self.execution_time = execution_time
        self.end_time = datetime.now()

    def to_dict(self) -> Dict:
        """Convert test suite to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
            "metadata": self.metadata,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "QATestSuite":
        """Create test suite from dictionary."""
        if "id" in data and isinstance(data["id"], str):
            data["id"] = UUID(data["id"])
        if "start_time" in data and data["start_time"]:
            data["start_time"] = datetime.fromisoformat(data["start_time"])
        if "end_time" in data and data["end_time"]:
            data["end_time"] = datetime.fromisoformat(data["end_time"])
        if "test_cases" in data:
            data["test_cases"] = [QATestCase(**tc) for tc in data["test_cases"]]
        return cls(**data)


class QAResult(BaseModel):
    """QA result model."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "passed",
                "execution_time": 1.23,
                "error_details": None,
                "metadata": {},
            }
        }
    )

    test_id: UUID
    status: QATestStatus
    execution_time: Optional[float] = None
    error_details: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = {}


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
                        "test_cases": [],
                    }
                ],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }
    )

    project_id: str
    title: str
    description: str
    test_suites: List[QATestSuite] = []
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    @field_validator("project_id", "title", "description")
    def validate_string_fields(cls, v: str) -> str:
        if not v:
            raise ValueError("Field must not be empty")
        return v

    @field_validator("test_suites")
    def validate_test_suites(cls, v: List[QATestSuite]) -> List[QATestSuite]:
        if not v:
            raise ValueError("QA suite must contain at least one test suite")
        return v

    def add_test_suite(self, test_suite: QATestSuite) -> None:
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

    def get_test_suite(self, title: str) -> Optional[QATestSuite]:
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
                "error_details": None,
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
