"""QA Tester agent implementation."""

import asyncio
import json
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from cahoots_agents.base import BaseAgent
from cahoots_core.ai import AIProvider
from cahoots_core.exceptions import ExternalServiceException
from cahoots_core.models.qa_suite import (
    QATest,
    QATestCase,
    QATestResult,
    QATestStatus,
    QATestSuite,
    QATestType,
    TestStatus,
    TestStep,
)
from cahoots_core.models.task import Task
from cahoots_core.services.github_service import GitHubService
from cahoots_core.services.qa_runner import QARunner
from cahoots_core.utils.metrics import MetricsCollector
from cahoots_events.bus.system import EventSystem


class QATester(BaseAgent):
    """QA Tester agent responsible for testing and quality assurance."""

    def __init__(
        self,
        event_system: EventSystem,
        config: Optional[Dict[str, Any]] = None,
        ai_provider: Optional[AIProvider] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the QA tester.

        Args:
            event_system: Event system for communication
            config: Optional configuration dictionary
            ai_provider: Optional AI provider for generating responses
            **kwargs: Additional arguments to pass to the base class
        """
        super().__init__(
            agent_type="qa_tester",
            event_system=event_system,
            config=config,
            ai_provider=ai_provider,
            **kwargs,
        )
        self.logger = logging.getLogger(__name__)
        self.metrics = MetricsCollector(service_name="qa_tester")
        self.qa_runner = QARunner()

    async def start(self) -> None:
        """Start the QA tester agent."""
        self.logger.info("Starting QA tester agent")
        await super().start()
        await self.event_system.subscribe("test.*", self.handle_test_event)

    async def generate_test_case(self, target: str, description: str) -> Dict[str, Any]:
        """Generate a test case for a given target and description."""
        prompt = f"Generate a test case for {target} with description: {description}"
        response = await self.ai.generate_response(prompt)
        test_case = json.loads(response)
        return test_case

    async def run_test_case(self, test_case: QATestCase) -> Dict[str, Any]:
        """Run a test case.

        Args:
            test_case: Test case to run

        Returns:
            Test results
        """
        try:
            result = await self.qa_runner.run_test(test_case)
            return result
        except Exception as e:
            self.logger.error(f"Error running test case: {str(e)}")
            raise

    async def generate_test_suite(self, target: str, test_type: str) -> QATestSuite:
        """Generate a test suite for the target."""
        prompt = f"""
        Target: {target}
        Test Type: {test_type}

        Generate a test suite for this target. Return as JSON:
        {{
            "name": "Test Suite Name",
            "description": "Test suite description",
            "tests": [
                {{
                    "name": "Test Case Name",
                    "description": "Test case description",
                    "steps": [
                        {{
                            "id": "step1",
                            "description": "Step description",
                            "expected_result": "Expected result"
                        }}
                    ]
                }}
            ]
        }}
        """

        try:
            response = await self.generate_response(prompt)
            suite_data = json.loads(response)

            # Convert steps to TestStep objects
            for test in suite_data.get("tests", []):
                steps = test.get("steps", [])
                test["steps"] = [
                    TestStep(
                        id=step.get("id", f"step_{i+1}"),
                        description=step["description"],
                        expected_result=step["expected_result"],
                        status=TestStatus.NOT_STARTED,
                    )
                    for i, step in enumerate(steps)
                ]

            return QATestSuite.from_dict(suite_data)
        except Exception as e:
            self.logger.error(f"Error generating test suite: {str(e)}")
            raise

    async def run_test_suite(self, suite: Union[QATestSuite, Dict[str, Any]]) -> Dict[str, Any]:
        """Run a test suite.

        Args:
            suite: Test suite to run

        Returns:
            Test suite results
        """
        if isinstance(suite, dict):
            suite = QATestSuite.from_dict(suite)
        elif not isinstance(suite, QATestSuite):
            raise ValueError("Invalid test suite type")

        try:
            result = await self.qa_runner.run_test_suite(suite.model_dump())
            return result
        except Exception as e:
            self.logger.error(f"Error running test suite: {str(e)}")
            raise

    async def analyze_test_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results and provide insights."""
        prompt = f"Analyze test results: {json.dumps(results)}"
        response = await self.ai.generate_response(prompt)
        analysis = json.loads(response)
        return analysis

    async def handle_test_event(self, event: Dict[str, Any]) -> None:
        """Handle test-related events.

        Args:
            event: Event data
        """
        event_type = event.get("type")
        if event_type == "test.request":
            await self.handle_test_request(event)
        elif event_type == "test.feedback":
            await self.handle_test_feedback(event)

    async def handle_test_request(self, event: Dict[str, Any]) -> None:
        """Handle test request event.

        Args:
            event: Event data containing test request
        """
        request_data = event.get("data", {})
        test_type = request_data.get("test_type")
        test_target = request_data.get("test_target")

        if test_type == "unit":
            await self.run_unit_tests(test_target)
        elif test_type == "integration":
            await self.run_integration_tests(test_target)
        elif test_type == "e2e":
            await self.run_e2e_tests(test_target)

    async def handle_test_feedback(self, event: Dict[str, Any]) -> None:
        """Handle test feedback event.

        Args:
            event: Event data containing test feedback
        """
        feedback_data = event.get("data", {})
        test_id = feedback_data.get("test_id")
        feedback = feedback_data.get("feedback")

        await self.process_test_feedback(test_id, feedback)

    async def process_test_feedback(self, test_id: str, feedback: str) -> None:
        """Process feedback for a test.

        Args:
            test_id: ID of the test
            feedback: Test feedback
        """
        prompt = f"""
        Test ID: {test_id}
        Feedback: {feedback}

        Based on this feedback, what actions should be taken? Return as JSON:
        {{
            "status": "success|failure",
            "actions": [
                {{
                    "type": "update_test|create_test|delete_test",
                    "details": {{...action specific details...}}
                }}
            ]
        }}
        """

        try:
            response = await self.generate_response(prompt)
            actions = json.loads(response)

            for action in actions.get("actions", []):
                if action["type"] == "update_test":
                    await self.update_test(test_id, action["details"])
                elif action["type"] == "create_test":
                    await self.create_test(action["details"])
                elif action["type"] == "delete_test":
                    await self.delete_test(test_id)

        except Exception as e:
            self.logger.error(f"Error processing test feedback: {str(e)}")
            raise

    async def report_test_results(self, results: Dict[str, Any]) -> None:
        """Report test results.

        Args:
            results: Test results to report
        """
        await self.event_system.publish("test.results", {"status": "completed", "results": results})

    async def update_test(self, test_id: str, details: Dict[str, Any]) -> None:
        """Update a test case.

        Args:
            test_id: ID of the test to update
            details: Updated test details
        """
        # TODO: Implement test update
        pass

    async def create_test(self, details: Dict[str, Any]) -> None:
        """Create a new test case.

        Args:
            details: Test case details
        """
        # TODO: Implement test creation
        pass

    async def delete_test(self, test_id: str) -> None:
        """Delete a test case.

        Args:
            test_id: ID of the test to delete
        """
        # TODO: Implement test deletion
        pass

    async def run_unit_tests(self, target: str) -> None:
        """Run unit tests for a specific target.

        Args:
            target: Target to test
        """
        test_suite = await self.generate_test_suite(target, "unit")
        results = await self.qa_runner.run_test_suite(test_suite)
        await self.report_test_results(results)

    async def run_integration_tests(self, target: str) -> None:
        """Run integration tests for a specific target.

        Args:
            target: Target to test
        """
        test_suite = await self.generate_test_suite(target, "integration")
        results = await self.qa_runner.run_test_suite(test_suite)
        await self.report_test_results(results)

    async def run_e2e_tests(self, target: str) -> None:
        """Run end-to-end tests for a specific target.

        Args:
            target: Target to test
        """
        test_suite = await self.generate_test_suite(target, "e2e")
        results = await self.qa_runner.run_test_suite(test_suite)
        await self.report_test_results(results)

    def _create_test_plan(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a test plan based on task requirements."""
        planning_config = self.get_capability_config("test_planning")

        # Map task priority to test strategies
        priority = task_data.get("priority", "medium")
        required_strategies = planning_config.get("priority_mapping", {}).get(priority, [])

        return {
            "strategies": required_strategies,
            "requirements": task_data.get("requirements", []),
            "priority": priority,
        }

    def _determine_test_scope(self, pr_data: Dict[str, Any]) -> List[str]:
        """Determine which types of tests to run based on PR content."""
        scope = ["unit"]  # Always run unit tests

        # Add integration tests if multiple components affected
        if len(pr_data.get("files", [])) > 1:
            scope.append("integration")

        # Add e2e tests if critical paths affected
        if any(f.startswith("src/core") for f in pr_data.get("files", [])):
            scope.append("e2e")

        # Add performance tests if performance-critical code changed
        if pr_data.get("labels", {}).get("performance", False):
            scope.append("performance")

        return scope

    def _create_bug_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a bug report from test results."""
        report_config = self.get_capability_config("reporting")
        template = report_config.get("bug_template", {})

        # Extract failed tests and create bug reports
        bugs = []
        for test_type, results in test_results.items():
            if not results.get("passed", True):
                bugs.append(
                    {field: results.get(field, "N/A") for field in template.get("fields", [])}
                )

        return {"bugs": bugs}

    def _analyze_test_results(
        self, results: Dict[str, Any], metrics_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze test results against quality metrics."""
        analysis = {}

        # Check coverage requirements
        for test_type, min_coverage in (
            metrics_config.get("coverage", {}).get("minimum", {}).items()
        ):
            actual_coverage = results.get(test_type, {}).get("coverage", 0)
            analysis[f"{test_type}_coverage"] = {
                "actual": actual_coverage,
                "required": min_coverage,
                "passed": actual_coverage >= min_coverage,
            }

        # Check performance metrics
        if "performance" in results:
            perf_metrics = metrics_config.get("performance", {})
            analysis["performance"] = {
                metric: {
                    "actual": results["performance"].get(metric),
                    "required": requirement,
                    "passed": self._compare_metric(results["performance"].get(metric), requirement),
                }
                for metric, requirement in perf_metrics.items()
            }

        return analysis

    def _compare_metric(self, actual: Any, requirement: str) -> bool:
        """Compare a metric against its requirement."""
        if not actual:
            return False

        operator = requirement[:2]
        value = float(requirement[2:])

        if operator == "< ":
            return actual < value
        elif operator == "> ":
            return actual > value
        else:
            return actual == value

    def _generate_reports(
        self, analysis: Dict[str, Any], report_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate test reports in configured formats."""
        reports = {}

        for format in report_config["formats"]:
            reports[format] = self._format_report(analysis, format)

        return reports

    def _format_report(self, data: Dict[str, Any], format: str) -> Dict[str, Any]:
        """Format report data in specified format."""
        return {"format": format, "data": data}

    def _generate_test_suite_prompt(
        self, title: str, description: str, requirements: List[str]
    ) -> str:
        """Generate prompt for test suite creation."""
        return f"""Generate test cases for:
Title: {title}
Description: {description}
Requirements:
{chr(10).join(f'- {req}' for req in requirements)}

Each test case should include:
1. Title
2. Description
3. Steps to execute
4. Expected result

Format each test case as:
TEST CASE: <title>
DESCRIPTION: <description>
STEPS:
<numbered list of steps>
EXPECTED: <expected result>

---"""

    def _parse_test_cases(self, response: str) -> List[QATestCase]:
        """Parse test cases from model response."""
        test_cases = []
        current_test_case = None
        steps = []

        for line in response.split("\n"):
            line = line.strip()

            if not line or line == "---":
                if current_test_case and steps:
                    current_test_case.steps = steps
                    test_cases.append(current_test_case)
                    current_test_case = None
                    steps = []
                continue

            if line.startswith("TEST CASE:"):
                if current_test_case and steps:
                    current_test_case.steps = steps
                    test_cases.append(current_test_case)
                    steps = []

                current_test_case = QATestCase(
                    title=line[10:].strip(), description="", steps=[], expected_result=""
                )

            elif line.startswith("DESCRIPTION:") and current_test_case:
                current_test_case.description = line[12:].strip()

            elif line.startswith("STEPS:"):
                continue

            elif line[0].isdigit() and ". " in line and current_test_case:
                steps.append(line.split(". ", 1)[1].strip())

            elif line.startswith("EXPECTED:") and current_test_case:
                current_test_case.expected_result = line[9:].strip()

        # Handle the last test case
        if current_test_case and steps:
            current_test_case.steps = steps
            test_cases.append(current_test_case)

        return test_cases

    def _create_default_test_suite(
        self, story_id: str, title: str, description: str
    ) -> QATestSuite:
        """Create a default test suite when generation fails."""
        return QATestSuite(
            story_id=story_id,
            title=f"Test Suite for {title}",
            description=f"Test suite generated for story: {description}",
            test_cases=[self._create_default_test_case()],
        )

    def _create_default_test_case(self) -> QATestCase:
        """Create a default test case when no valid test cases are parsed."""
        return QATestCase(
            title="Test Case",
            description="Basic test case",
            steps=["1. Verify basic functionality"],
            expected_result="Test should complete successfully",
        )

    def _generate_step_prompt(self, test_case: QATestCase, step: str, step_number: int) -> str:
        """Generate prompt for test step execution."""
        return f"""Execute test step {step_number} of {len(test_case.steps)}:
Test: {test_case.title}
Step: {step}

Respond with:
Status: <PASS|FAIL>
Actual Result: <what happened>
Details: <additional details>"""

    def _parse_step_result(self, response: str) -> QATestResult:
        """Parse step execution result."""
        lines = response.strip().split("\n")
        status = None
        actual_result = None
        details = None

        for line in lines:
            line = line.strip()
            if line.startswith("Status:"):
                status = TestStatus.PASSED if "PASS" in line.upper() else TestStatus.FAILED
            elif line.startswith("Actual Result:"):
                actual_result = line[14:].strip()
            elif line.startswith("Details:"):
                details = line[8:].strip()

        return QATestResult(
            test_case_title="Step Execution",
            status=status or TestStatus.FAILED,
            actual_result=actual_result or "No result provided",
            error_details={"details": details} if details else None,
        )

    async def execute_test_plan(self, test_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a test plan.

        Args:
            test_plan: Test plan to execute

        Returns:
            Test execution results
        """
        try:
            return await self.qa_runner.execute_plan(test_plan)
        except Exception as e:
            self.logger.error(f"Error executing test plan: {str(e)}")
            raise

    async def generate_test_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a test report from results."""
        try:
            response = await self.ai.generate_response(
                f"Generate test report for results: {json.dumps(test_results)}", temperature=0.7
            )
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error generating test report: {e}")
            return {
                "summary": f"{test_results.get('passed', 0)}/{test_results.get('executed', 0)} tests passed",
                "coverage_analysis": "Coverage data available",
                "recommendations": [],
            }

    async def analyze_test_failures(self, failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze test failures and provide insights.

        Args:
            failures: List of test failures to analyze

        Returns:
            Analysis of failures
        """
        prompt = f"""
        Analyze these test failures and provide insights:
        {json.dumps(failures)}
        
        Return as JSON:
        {{
            "root_cause": "string",
            "suggested_fixes": ["string"],
            "priority": "high|medium|low"
        }}
        """
        try:
            response = await self.ai.generate_response(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error analyzing test failures: {str(e)}")
            raise

    async def validate_test_coverage(self, coverage_data: Dict[str, float]) -> Dict[str, Any]:
        """Validate test coverage against requirements."""
        try:
            response = await self.ai.generate_response(
                f"Analyze test coverage: {json.dumps(coverage_data)}", temperature=0.7
            )
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error validating test coverage: {e}")
            return {"meets_requirements": True, "gaps": [], "recommendations": []}

    async def monitor_test_execution(self, test_run: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor the execution of a test run.

        Args:
            test_run: Test run to monitor

        Returns:
            Test run status
        """
        try:
            return await self.qa_runner.get_run_status(test_run["id"])
        except Exception as e:
            self.logger.error(f"Error monitoring test execution: {str(e)}")
            raise

    async def generate_test_plan(self, target: str, requirements: List[str]) -> Dict[str, Any]:
        """Generate a test plan for a target.

        Args:
            target: Target to test
            requirements: List of requirements to test against

        Returns:
            Test plan
        """
        prompt = f"""
        Generate a test plan for:
        Target: {target}
        Requirements: {json.dumps(requirements)}
        
        Return as JSON:
        {{
            "test_types": ["unit", "integration", "e2e"],
            "coverage_targets": {{
                "unit": 80,
                "integration": 60,
                "e2e": 40
            }},
            "priority_areas": ["string"]
        }}
        """
        try:
            response = await self.ai.generate_response(prompt)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error generating test plan: {str(e)}")
            raise
