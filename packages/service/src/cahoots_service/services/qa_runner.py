"""QA runner service."""
import asyncio
import logging
import time
from typing import List

from src.models.qa_suite import TestSuite, TestCase, QAResult, TestStatus
from cahoots_core.exceptions import ExternalServiceError
from src.core.dependencies import ServiceDeps

logger = logging.getLogger(__name__)

class QARunner:
    """QA runner service."""
    
    def __init__(self, deps: ServiceDeps):
        """Initialize the QA runner.
        
        Args:
            deps: Service dependencies including model and event system
        """
        self.running = False
        self.model = deps.model
        self.event_system = deps.event_system
        
    async def __aenter__(self):
        """Enter async context."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        self.running = False
        
    async def check_connection(self) -> bool:
        """Check if service is available."""
        return True
        
    async def close(self):
        """Close the runner."""
        self.running = False
        
    async def run_test_suite(self, test_suite: TestSuite) -> List[QAResult]:
        """Run a test suite.
        
        Args:
            test_suite: The test suite to run
            
        Returns:
            List of test results
        """
        if self.running:
            raise ExternalServiceError(
                service="qa_runner",
                operation="run_test_suite",
                error="QA runner is already running a test suite"
            )
            
        self.running = True
        results = []
        
        try:
            for test_case in test_suite.test_cases:
                result = await self.run_test_case(test_case)
                results.append(result)
                
                # Small delay between tests
                await asyncio.sleep(0.1)
                
        finally:
            self.running = False
            
        return results
        
    async def run_test_case(self, test_case: TestCase) -> QAResult:
        """Run a single test case.
        
        Args:
            test_case: The test case to run
            
        Returns:
            QA result
        """
        if not test_case:
            raise ValueError("Test case cannot be None")
            
        if not self.model:
            raise ValueError("Model is required for test execution")
            
        test_case.start_execution()
        start_time = time.time()
        
        try:
            # Execute each test step and validate results
            step_results = []
            for step in test_case.steps:
                # Generate test execution prompt
                prompt = f"""Execute test step and validate result:
                Step: {step}
                Expected Result: {test_case.expected_result}
                
                Return format:
                Status: [PASS/FAIL]
                Actual Result: [observed behavior]
                Details: [any relevant details]
                """
                
                # Execute test step using model
                response = await self.model.generate_response(prompt)
                step_results.append(self.parse_step_result(response))
            
            execution_time = time.time() - start_time
            
            # Analyze step results to determine overall test status
            failed_steps = [r for r in step_results if r['status'] == 'FAIL']
            if not failed_steps:
                actual_result = test_case.expected_result
                test_case.mark_passed(actual_result, execution_time)
                
                return QAResult(
                    test_case_title=test_case.title,
                    status=TestStatus.PASSED,
                    actual_result=actual_result,
                    execution_time=execution_time
                )
            else:
                # Combine failure details from failed steps
                actual_result = "\n".join(
                    f"Step {i+1}: {r['actual_result']}" 
                    for i, r in enumerate(step_results) 
                    if r['status'] == 'FAIL'
                )
                test_case.mark_failed(actual_result, execution_time)
                
                return QAResult(
                    test_case_title=test_case.title,
                    status=TestStatus.FAILED,
                    actual_result=actual_result,
                    execution_time=execution_time
                )

        except Exception as e:
            execution_time = time.time() - start_time
            test_case.mark_error(str(e))
            
            return QAResult(
                test_case_title=test_case.title,
                status=TestStatus.ERROR,
                actual_result=str(e),
                execution_time=execution_time,
                error_details={
                    "type": e.__class__.__name__,
                    "message": str(e)
                }
            )
            
    def parse_step_result(self, response: str) -> dict:
        """Parse step execution result from model response.
        
        Args:
            response: Raw response from model
            
        Returns:
            Dict containing status and result details
        """
        lines = [line.strip() for line in response.strip().split('\n')]
        result = {'status': 'FAIL', 'actual_result': '', 'details': ''}
        
        for line in lines:
            if line.startswith('Status:'):
                result['status'] = line.split(':', 1)[1].strip()
            elif line.startswith('Actual Result:'):
                result['actual_result'] = line.split(':', 1)[1].strip()
            elif line.startswith('Details:'):
                result['details'] = line.split(':', 1)[1].strip()
                
        return result 