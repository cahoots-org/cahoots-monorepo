"""QA test runner service."""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from uuid import UUID

from cahoots_core.exceptions import ServiceError
from cahoots_core.models.qa_suite import (
    QASuite,
    QATest,
    QATestResult,
    QATestStatus,
    QATestSuite,
    QATestSuiteResult,
)
from cahoots_core.utils.metrics.performance import PerformanceMetrics

logger = logging.getLogger(__name__)

class QARunner:
    """Service for running QA tests."""
    
    def __init__(self, metrics: Optional[PerformanceMetrics] = None):
        """Initialize QA runner."""
        self.metrics = metrics or PerformanceMetrics()
        
    async def run_test(self, test: QATest, context: Dict[str, Any]) -> QATestResult:
        """Run a single test."""
        try:
            with self.metrics.measure_time(f"qa_test.{test.name}"):
                # Execute test steps
                result = await self._execute_test_steps(test, context)
                
                # Record metrics
                self.metrics.increment(f"qa_test.{test.name}.{result.status.value}")
                
                return result
        except Exception as e:
            logger.error(f"Error running test {test.name}: {e}")
            return QATestResult(
                test_id=test.id,
                status=QATestStatus.ERROR,
                error=str(e),
                duration=0,
                output={},
            )
            
    async def _execute_test_steps(self, test: QATest, context: Dict[str, Any]) -> QATestResult:
        """Execute test steps."""
        start_time = self.metrics.current_time()
        
        try:
            # Initialize test environment
            env = await self._setup_test_env(test, context)
            
            # Run test steps
            output = {}
            for step in test.steps:
                step_result = await self._run_test_step(step, env)
                output[step.name] = step_result
                
                if step_result.get("status") == "failed":
                    return QATestResult(
                        test_id=test.id,
                        status=QATestStatus.FAILED,
                        error=step_result.get("error"),
                        duration=self.metrics.elapsed_time(start_time),
                        output=output,
                    )
                    
            return QATestResult(
                test_id=test.id,
                status=QATestStatus.PASSED,
                error=None,
                duration=self.metrics.elapsed_time(start_time),
                output=output,
            )
            
        except Exception as e:
            return QATestResult(
                test_id=test.id,
                status=QATestStatus.ERROR,
                error=str(e),
                duration=self.metrics.elapsed_time(start_time),
                output={},
            )
            
    async def _setup_test_env(self, test: QATest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Set up test environment."""
        env = context.copy()
        env.update(test.setup or {})
        return env
        
    async def _run_test_step(self, step: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test step."""
        try:
            # Execute step action
            result = await self._execute_step_action(step, env)
            
            # Validate step result
            if not await self._validate_step_result(step, result, env):
                return {
                    "status": "failed",
                    "error": f"Step validation failed: {step.get('name')}",
                    "result": result,
                }
                
            return {
                "status": "passed",
                "result": result,
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "result": None,
            }
            
    async def _execute_step_action(self, step: Dict[str, Any], env: Dict[str, Any]) -> Any:
        """Execute step action."""
        action = step.get("action")
        if not action:
            raise ValueError("Step action not specified")
            
        # Execute action based on type
        if action == "http":
            return await self._execute_http_action(step, env)
        elif action == "function":
            return await self._execute_function_action(step, env)
        else:
            raise ValueError(f"Unknown action type: {action}")
            
    async def _validate_step_result(self, step: Dict[str, Any], result: Any, env: Dict[str, Any]) -> bool:
        """Validate step result."""
        validation = step.get("validation")
        if not validation:
            return True
            
        try:
            # Execute validation rules
            for rule in validation:
                if not await self._check_validation_rule(rule, result, env):
                    return False
            return True
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
            
    async def run_suite(self, suite: QATestSuite, context: Dict[str, Any]) -> QATestSuiteResult:
        """Run a test suite."""
        try:
            with self.metrics.measure_time(f"qa_suite.{suite.name}"):
                results = []
                
                # Run tests in parallel if specified
                if suite.parallel:
                    tasks = [
                        self.run_test(test, context)
                        for test in suite.tests
                    ]
                    results = await asyncio.gather(*tasks)
                else:
                    for test in suite.tests:
                        result = await self.run_test(test, context)
                        results.append(result)
                        
                # Calculate suite status
                failed = any(r.status in [QATestStatus.FAILED, QATestStatus.ERROR] for r in results)
                status = QATestStatus.FAILED if failed else QATestStatus.PASSED
                
                return QATestSuiteResult(
                    suite_id=suite.id,
                    status=status,
                    test_results=results,
                )
                
        except Exception as e:
            logger.error(f"Error running suite {suite.name}: {e}")
            raise ServiceError(f"Failed to run test suite: {e}")
            
    async def run_qa_suite(self, qa_suite: QASuite) -> List[QATestSuiteResult]:
        """Run all test suites in a QA suite."""
        try:
            with self.metrics.measure_time(f"qa.{qa_suite.name}"):
                results = []
                
                # Initialize context
                context = await self._initialize_qa_context(qa_suite)
                
                # Run each test suite
                for suite in qa_suite.test_suites:
                    result = await self.run_suite(suite, context)
                    results.append(result)
                    
                return results
                
        except Exception as e:
            logger.error(f"Error running QA suite {qa_suite.name}: {e}")
            raise ServiceError(f"Failed to run QA suite: {e}")
            
    async def _initialize_qa_context(self, qa_suite: QASuite) -> Dict[str, Any]:
        """Initialize QA context."""
        try:
            context = qa_suite.context or {}
            
            # Add any global setup
            if qa_suite.setup:
                context.update(await self._execute_qa_setup(qa_suite.setup))
                
            return context
            
        except Exception as e:
            logger.error(f"Error initializing QA context: {e}")
            raise ServiceError(f"Failed to initialize QA context: {e}")
            
    async def _execute_qa_setup(self, setup: Dict[str, Any]) -> Dict[str, Any]:
        """Execute QA setup steps."""
        try:
            result = {}
            for key, value in setup.items():
                if isinstance(value, dict) and "action" in value:
                    result[key] = await self._execute_step_action(value, {})
                else:
                    result[key] = value
            return result
            
        except Exception as e:
            logger.error(f"Error executing QA setup: {e}")
            raise ServiceError(f"Failed to execute QA setup: {e}") 