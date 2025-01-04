# src/agents/tester/__init__.py
"""Tester agent for test suite generation and execution."""
import uuid
from logging import Logger
from typing import Dict, Any, Optional

from src.agents.base_agent import BaseAgent
from src.services.test_suite_generator import TestSuiteGenerator
from src.services.test_runner import TestRunner
from src.utils.event_system import EventSystem
from src.utils.model import Model

class Tester(BaseAgent):
    """Agent responsible for test suite generation and execution."""

    def __init__(self, event_system: Optional[EventSystem] = None, start_listening: bool = True) -> None:
        """Initialize the Tester agent.
        
        Args:
            event_system: Optional event system instance. If not provided, will get from singleton.
            start_listening: Whether to start listening for events immediately
        """
        # Initialize base class first
        super().__init__(model_name="gpt-4-1106-preview", start_listening=start_listening, event_system=event_system)
        
        # Initialize services
        self.tester_id = str(uuid.uuid4())
        self.test_suite_generator = TestSuiteGenerator(self.model, self.logger)
        self.test_runner = TestRunner(self.model, self.logger)
        
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        await super().setup_events()  # This handles system and story_assigned subscriptions
        self.logger.info("Tester agent setup complete")

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
            test_results = await self.test_runner.run_test_suite(test_suite)

            # Calculate summary metrics
            total_tests = len(test_results)
            passed_tests = sum(1 for r in test_results if r.passed)
            coverage = (passed_tests / total_tests * 100) if total_tests > 0 else 0

            # Format results for event
            results_data = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "coverage": f"{coverage:.1f}%",
                "test_cases": [
                    {
                        "title": r.test_case.title,
                        "status": "PASSED" if r.passed else "FAILED",
                        "details": r.details
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
        """Start the Tester agent."""
        await super().start()
        await self.event_system.subscribe("story_assigned", self.handle_story_assigned)
        self.logger.info("Tester agent started") 