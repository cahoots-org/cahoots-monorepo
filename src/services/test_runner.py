"""Service for executing test suites."""
from logging import Logger
from typing import List
import time

from src.models.test_suite import TestSuite, TestCase, TestResult
from src.utils.model import Model
from src.core.exceptions import ValidationError

class TestRunner:
    """Service for executing test suites."""

    def __init__(self, model: Model, logger: Logger) -> None:
        """Initialize the test runner.
        
        Args:
            model: The model to use for test execution
            logger: Logger for recording events
        """
        self.model = model
        self.logger = logger

    async def run_test_suite(self, test_suite: TestSuite) -> List[TestResult]:
        """Execute all test cases in a test suite.
        
        Args:
            test_suite: The test suite to execute
            
        Returns:
            List of test results for each test case
            
        Raises:
            ValidationError: If the test suite is invalid
        """
        self.logger.info(f"Running test suite: {test_suite.title}")
        
        # Validate test suite
        if not test_suite.story_id:
            raise ValidationError("Test suite must have a story ID")
        if not test_suite.test_cases:
            raise ValidationError("Test suite must have at least one test case")
            
        results = []

        for test_case in test_suite.test_cases:
            result = await self.run_test_case(test_case)
            results.append(result)

        passed_count = sum(1 for r in results if r.passed)
        self.logger.info(f"Test suite complete. {passed_count}/{len(results)} tests passed")
        return results

    async def run_test_case(self, test_case: TestCase) -> TestResult:
        """Execute a single test case.
        
        Args:
            test_case: The test case to execute
            
        Returns:
            The result of the test execution
        """
        self.logger.info(f"Running test case: {test_case.title}")
        start_time = time.time()

        try:
            # Execute test and get actual result
            actual_result, execution_time = await self.execute_test(test_case)
            
            # Compare with expected result
            passed = actual_result == test_case.expected_result
            
            # Update test case status
            if passed:
                test_case.mark_passed(actual_result, execution_time)
            else:
                test_case.mark_failed(actual_result, execution_time)

            result = TestResult(
                test_case=test_case,
                passed=passed,
                details=f"Actual result: {actual_result}",
                execution_time=execution_time
            )

            self.logger.info(f"Test case complete. Passed: {passed}")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            test_case.mark_error(e)  # Pass the actual exception
            return TestResult(
                test_case=test_case,
                passed=False,
                details=f"Error: {str(e)}",
                execution_time=execution_time
            )

    async def execute_test(self, test_case: TestCase) -> tuple[str, float]:
        """Execute a test case and return the actual result.
        
        Args:
            test_case: The test case to execute
            
        Returns:
            Tuple of (actual_result, execution_time)
        """
        start_time = time.time()
        
        # Generate prompt for test execution
        prompt = self._build_execution_prompt(test_case)
        response = await self.model.generate_response(prompt)
        
        execution_time = time.time() - start_time
        return response, execution_time

    def _build_execution_prompt(self, test_case: TestCase) -> str:
        """Build the prompt for test case execution.
        
        Args:
            test_case: The test case to execute
            
        Returns:
            The prompt for the model
        """
        steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(test_case.steps))
        
        return f"""Execute test case:

Title: {test_case.title}
Description: {test_case.description}

Steps:
{steps_text}

Expected Result: {test_case.expected_result}

Verify if the test passes or fails. If it passes, explain how the actual result matches the expected result.
If it fails, explain why it fails and what the actual result was."""

    def _evaluate_test_result(self, response: str, expected_result: str) -> bool:
        """Evaluate if a test passed based on the model's response.
        
        Args:
            response: The model's response text
            expected_result: The expected result from the test case
            
        Returns:
            True if the test passed, False otherwise
        """
        # Look for clear pass/fail indicators
        response_lower = response.lower()
        if "test passed" in response_lower:
            return True
        if "test failed" in response_lower:
            return False

        # Check if expected result is mentioned positively
        expected_phrases = [
            "matches expected",
            "as expected",
            "successfully",
            "correct",
            "verified"
        ]
        return any(phrase in response_lower for phrase in expected_phrases) 