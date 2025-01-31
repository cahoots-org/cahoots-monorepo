"""QA test suite generator service."""
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from cahoots_core.exceptions import ServiceError
from cahoots_core.models.qa_suite import (
    QASuite,
    QATest,
    QATestSuite,
    QATestType,
    QATestResult,
    QATestStatus,
    TestStatus,
    TestStep
)

logger = logging.getLogger(__name__)

class QASuiteGenerator:
    """Service for generating QA test suites."""
    
    def __init__(self):
        """Initialize QA suite generator."""
        self.test_templates = {
            QATestType.API: self._generate_api_test,
            QATestType.INTEGRATION: self._generate_integration_test,
            QATestType.PERFORMANCE: self._generate_performance_test,
            QATestType.SECURITY: self._generate_security_test,
        }
        
    async def generate_suite(
        self,
        name: str,
        description: str,
        test_types: List[QATestType],
        context: Dict[str, Any],
    ) -> QASuite:
        """Generate a QA test suite."""
        try:
            test_suites = []
            
            # Generate test suites for each type
            for test_type in test_types:
                suite = await self._generate_test_suite(test_type, context)
                if suite:
                    test_suites.append(suite)
                    
            return QASuite(
                id=uuid4(),
                name=name,
                description=description,
                test_suites=test_suites,
                context=context,
            )
            
        except Exception as e:
            logger.error(f"Error generating QA suite: {e}")
            raise ServiceError(f"Failed to generate QA suite: {e}")
            
    async def _generate_test_suite(
        self,
        test_type: QATestType,
        context: Dict[str, Any],
    ) -> Optional[QATestSuite]:
        """Generate a test suite for a specific type."""
        try:
            generator = self.test_templates.get(test_type)
            if not generator:
                logger.warning(f"No generator found for test type: {test_type}")
                return None
                
            tests = []
            
            # Generate tests based on context
            if test_type == QATestType.API:
                tests.extend(await self._generate_api_tests(context))
            elif test_type == QATestType.INTEGRATION:
                tests.extend(await self._generate_integration_tests(context))
            elif test_type == QATestType.PERFORMANCE:
                tests.extend(await self._generate_performance_tests(context))
            elif test_type == QATestType.SECURITY:
                tests.extend(await self._generate_security_tests(context))
                
            if not tests:
                return None
                
            return QATestSuite(
                id=uuid4(),
                name=f"{test_type.value} Tests",
                description=f"Generated {test_type.value} test suite",
                test_type=test_type,
                tests=tests,
                parallel=test_type in [QATestType.API, QATestType.PERFORMANCE],
            )
            
        except Exception as e:
            logger.error(f"Error generating test suite for {test_type}: {e}")
            return None
            
    async def _generate_api_tests(self, context: Dict[str, Any]) -> List[QATest]:
        """Generate API tests based on context."""
        tests = []
        
        # Extract API endpoints from context
        endpoints = context.get("endpoints", [])
        for endpoint in endpoints:
            test = await self._generate_api_test(endpoint)
            if test:
                tests.append(test)
                
        return tests
        
    async def _generate_api_test(self, endpoint: Dict[str, Any]) -> Optional[QATest]:
        """Generate an API test for an endpoint."""
        try:
            method = endpoint.get("method", "GET")
            path = endpoint.get("path")
            if not path:
                return None
                
            return QATest(
                id=uuid4(),
                name=f"{method} {path}",
                description=f"Test {method} {path} endpoint",
                test_type=QATestType.API,
                steps=[
                    {
                        "name": "request",
                        "action": "http",
                        "method": method,
                        "url": path,
                        "headers": endpoint.get("headers", {}),
                        "params": endpoint.get("params", {}),
                        "body": endpoint.get("body"),
                    },
                    {
                        "name": "validate",
                        "action": "function",
                        "validation": [
                            {
                                "type": "status",
                                "expected": endpoint.get("expected_status", 200),
                            },
                            {
                                "type": "schema",
                                "schema": endpoint.get("response_schema"),
                            },
                        ],
                    },
                ],
            )
            
        except Exception as e:
            logger.error(f"Error generating API test: {e}")
            return None
            
    async def _generate_integration_tests(self, context: Dict[str, Any]) -> List[QATest]:
        """Generate integration tests based on context."""
        tests = []
        
        # Extract integration flows from context
        flows = context.get("flows", [])
        for flow in flows:
            test = await self._generate_integration_test(flow)
            if test:
                tests.append(test)
                
        return tests
        
    async def _generate_integration_test(self, flow: Dict[str, Any]) -> Optional[QATest]:
        """Generate an integration test for a flow."""
        try:
            name = flow.get("name")
            if not name:
                return None
                
            steps = []
            for step in flow.get("steps", []):
                step_config = {
                    "name": step.get("name"),
                    "action": step.get("type"),
                }
                step_config.update(step.get("config", {}))
                steps.append(step_config)
                
            return QATest(
                id=uuid4(),
                name=f"Flow: {name}",
                description=f"Test integration flow: {name}",
                test_type=QATestType.INTEGRATION,
                steps=steps,
            )
            
        except Exception as e:
            logger.error(f"Error generating integration test: {e}")
            return None
            
    async def _generate_performance_tests(self, context: Dict[str, Any]) -> List[QATest]:
        """Generate performance tests based on context."""
        tests = []
        
        # Extract performance scenarios from context
        scenarios = context.get("performance_scenarios", [])
        for scenario in scenarios:
            test = await self._generate_performance_test(scenario)
            if test:
                tests.append(test)
                
        return tests
        
    async def _generate_performance_test(self, scenario: Dict[str, Any]) -> Optional[QATest]:
        """Generate a performance test for a scenario."""
        try:
            name = scenario.get("name")
            if not name:
                return None
                
            return QATest(
                id=uuid4(),
                name=f"Performance: {name}",
                description=f"Test performance scenario: {name}",
                test_type=QATestType.PERFORMANCE,
                steps=[
                    {
                        "name": "load_test",
                        "action": "performance",
                        "config": {
                            "duration": scenario.get("duration", 60),
                            "users": scenario.get("users", 10),
                            "ramp_up": scenario.get("ramp_up", 30),
                            "target": scenario.get("target"),
                            "thresholds": scenario.get("thresholds", {}),
                        },
                    },
                ],
            )
            
        except Exception as e:
            logger.error(f"Error generating performance test: {e}")
            return None
            
    async def _generate_security_tests(self, context: Dict[str, Any]) -> List[QATest]:
        """Generate security tests based on context."""
        tests = []
        
        # Extract security checks from context
        checks = context.get("security_checks", [])
        for check in checks:
            test = await self._generate_security_test(check)
            if test:
                tests.append(test)
                
        return tests
        
    async def _generate_security_test(self, check: Dict[str, Any]) -> Optional[QATest]:
        """Generate a security test for a check."""
        try:
            name = check.get("name")
            if not name:
                return None
                
            return QATest(
                id=uuid4(),
                name=f"Security: {name}",
                description=f"Test security check: {name}",
                test_type=QATestType.SECURITY,
                steps=[
                    {
                        "name": "security_scan",
                        "action": "security",
                        "config": {
                            "type": check.get("type"),
                            "target": check.get("target"),
                            "rules": check.get("rules", []),
                            "severity": check.get("severity", "high"),
                        },
                    },
                ],
            )
            
        except Exception as e:
            logger.error(f"Error generating security test: {e}")
            return None 