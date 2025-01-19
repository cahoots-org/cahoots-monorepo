"""Unit tests for test reporting functionality."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from agent_qa.reporting import TestReporter
from agent_qa.models import TestCase, TestResult, TestSuite

@pytest.fixture
def test_reporter():
    """Create a test reporter instance."""
    return TestReporter()

@pytest.fixture
def sample_test_results():
    """Create sample test results for testing."""
    return [
        TestResult(
            test_case_id="test-1",
            status="passed",
            coverage=85.5,
            metadata={
                "execution_time": 1.2,
                "assertions": {
                    "total": 5,
                    "passed": 5,
                    "failed": 0
                }
            }
        ),
        TestResult(
            test_case_id="test-2",
            status="failed",
            coverage=0.0,
            metadata={
                "execution_time": 0.8,
                "error": "AssertionError: Expected 200, got 404",
                "assertions": {
                    "total": 3,
                    "passed": 2,
                    "failed": 1
                }
            }
        ),
        TestResult(
            test_case_id="test-3",
            status="error",
            coverage=0.0,
            metadata={
                "execution_time": 0.5,
                "error": "ConnectionError: Failed to connect to API",
                "assertions": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0
                }
            }
        )
    ]

def test_generate_summary_report(test_reporter, sample_test_results):
    """Test generation of summary report."""
    report = test_reporter.generate_summary_report(sample_test_results)
    
    assert "total_tests" in report
    assert report["total_tests"] == 3
    assert report["passed_tests"] == 1
    assert report["failed_tests"] == 1
    assert report["error_tests"] == 1
    assert "total_coverage" in report
    assert report["total_coverage"] == pytest.approx(28.5, rel=0.01)

def test_generate_detailed_report(test_reporter, sample_test_results):
    """Test generation of detailed report."""
    report = test_reporter.generate_detailed_report(sample_test_results)
    
    assert "results" in report
    assert len(report["results"]) == 3
    assert "summary" in report
    assert "execution_time" in report
    
    for result in report["results"]:
        assert "test_case_id" in result
        assert "status" in result
        assert "coverage" in result
        assert "metadata" in result

def test_generate_coverage_report(test_reporter, sample_test_results):
    """Test generation of coverage report."""
    report = test_reporter.generate_coverage_report(sample_test_results)
    
    assert "total_coverage" in report
    assert "coverage_by_type" in report
    assert "coverage_by_module" in report
    assert "uncovered_lines" in report

def test_generate_error_report(test_reporter, sample_test_results):
    """Test generation of error report."""
    report = test_reporter.generate_error_report(sample_test_results)
    
    assert "total_errors" in report
    assert report["total_errors"] == 2  # One failed, one error
    assert "errors" in report
    assert len(report["errors"]) == 2
    
    for error in report["errors"]:
        assert "test_case_id" in error
        assert "status" in error
        assert "error_message" in error

def test_generate_performance_report(test_reporter, sample_test_results):
    """Test generation of performance report."""
    report = test_reporter.generate_performance_report(sample_test_results)
    
    assert "total_execution_time" in report
    assert report["total_execution_time"] == pytest.approx(2.5, rel=0.01)
    assert "average_execution_time" in report
    assert "execution_time_by_test" in report
    assert len(report["execution_time_by_test"]) == 3

def test_generate_assertion_report(test_reporter, sample_test_results):
    """Test generation of assertion report."""
    report = test_reporter.generate_assertion_report(sample_test_results)
    
    assert "total_assertions" in report
    assert report["total_assertions"] == 8
    assert "passed_assertions" in report
    assert report["passed_assertions"] == 7
    assert "failed_assertions" in report
    assert report["failed_assertions"] == 1

def test_generate_trend_report(test_reporter):
    """Test generation of trend report."""
    historical_results = [
        {
            "timestamp": "2024-01-01",
            "results": [
                TestResult(
                    test_case_id="test-1",
                    status="passed",
                    coverage=80.0,
                    metadata={"execution_time": 1.0}
                )
            ]
        },
        {
            "timestamp": "2024-01-02",
            "results": [
                TestResult(
                    test_case_id="test-1",
                    status="failed",
                    coverage=0.0,
                    metadata={"execution_time": 1.1}
                )
            ]
        }
    ]
    
    report = test_reporter.generate_trend_report(historical_results)
    
    assert "coverage_trend" in report
    assert "execution_time_trend" in report
    assert "status_trend" in report
    assert len(report["coverage_trend"]) == 2

def test_generate_comparison_report(test_reporter, sample_test_results):
    """Test generation of comparison report."""
    previous_results = [
        TestResult(
            test_case_id="test-1",
            status="failed",
            coverage=75.0,
            metadata={"execution_time": 1.5}
        )
    ]
    
    report = test_reporter.generate_comparison_report(
        sample_test_results,
        previous_results
    )
    
    assert "improved_tests" in report
    assert "degraded_tests" in report
    assert "coverage_change" in report
    assert "execution_time_change" in report

def test_export_report_json(test_reporter, sample_test_results):
    """Test exporting report as JSON."""
    with patch("builtins.open", mock_open()) as mock_file:
        test_reporter.export_report_json(
            sample_test_results,
            "report.json"
        )
        mock_file.assert_called_once_with("report.json", "w")

def test_export_report_html(test_reporter, sample_test_results):
    """Test exporting report as HTML."""
    with patch("builtins.open", mock_open()) as mock_file:
        test_reporter.export_report_html(
            sample_test_results,
            "report.html"
        )
        mock_file.assert_called_once_with("report.html", "w") 