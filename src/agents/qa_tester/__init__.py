# src/agents/qa_tester/__init__.py
"""QATester agent for test suite generation and execution."""
import uuid
from logging import Logger
from typing import Dict, Any, Optional, List

from src.agents.base_agent import BaseAgent
from src.services.qa_suite_generator import QASuiteGenerator
from src.services.qa_runner import QARunner
from src.utils.event_system import EventSystem
from src.utils.model import Model
from src.models.qa_suite import TestStatus, TestSuite, QAResult

class QATester(BaseAgent):
    """Agent responsible for test suite generation and execution."""

    def __init__(self, event_system: Optional[EventSystem] = None, start_listening: bool = True) -> None:
        """Initialize the QATester agent.
        
        Args:
            event_system: Optional event system instance. If not provided, will get from singleton.
            start_listening: Whether to start listening for events immediately
        """
        # Initialize base class first
        super().__init__(model_name="gpt-4-1106-preview", start_listening=start_listening, event_system=event_system)
        
        # Initialize services
        self.tester_id = str(uuid.uuid4())
        self.model = Model(model_name="gpt-4-1106-preview", event_system=self.event_system)  # Pass event system
        self.test_suite_generator = QASuiteGenerator(self.model, self.logger)
        self.test_runner = QARunner(self.model)
        
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        await super().setup_events()  # This handles system and story_assigned subscriptions
        self.logger.info("QATester agent setup complete")

    async def handle_system_message(self, message: Dict[str, Any]) -> None:
        """Handle system messages.
        
        Args:
            message: System message data
        """
        # Log system messages but no specific handling needed
        self.logger.info(f"Received system message: {message}")
        
    async def handle_story_assigned(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a story being assigned for testing.
        
        Args:
            data: Event data containing story details
            
        Returns:
            Dict containing status and any error details
        """
        story_id = data["story_id"]
        title = data["title"]
        description = data["description"]
        
        self.logger.info(f"Handling story assignment: {title}")

        try:
            # Generate test suite
            test_suite = await self.test_suite_generator.generate_test_suite(
                story_id=story_id,
                title=title,
                description=description
            )

            # Execute test suite
            test_results = await self.run_test_suite(test_suite)

            # Calculate summary metrics
            total_tests = len(test_results)
            passed_tests = sum(1 for r in test_results if r.status == TestStatus.PASSED)
            coverage = (passed_tests / total_tests * 100) if total_tests > 0 else 0

            # Format results for event
            results_data = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "coverage": f"{coverage:.1f}%",
                "test_cases": [
                    {
                        "title": r.test_case_title,
                        "status": r.status.value.upper(),
                        "actual_result": r.actual_result,
                        "execution_time": r.execution_time,
                        "error_details": r.error_details
                    }
                    for r in test_results
                ]
            }

            # Publish results
            await self.event_system.publish(
                "test_results_ready",
                {
                    "story_id": story_id,
                    "test_results": results_data
                }
            )

            self.logger.info(f"Published test results for story {story_id}")
            return {"status": "success", "data": results_data}
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error handling story assignment: {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "error": error_msg
            }

    async def start(self) -> None:
        """Start the QATester agent."""
        await super().start()
        await self.event_system.subscribe("story_assigned", self.handle_story_assigned)
        self.logger.info("QATester agent started")

    async def run_test_suite(self, test_suite: TestSuite) -> List[QAResult]:
        """Run a test suite.
        
        Args:
            test_suite: Test suite to run
            
        Returns:
            List of test results
            
        Raises:
            ExternalServiceException: If test execution fails
        """
        self.logger.info(f"Running test suite for story {test_suite.story_id}")
        return await self.test_runner.run_test_suite(test_suite) 