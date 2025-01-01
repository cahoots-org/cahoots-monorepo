# src/agents/tester.py
from .base_agent import BaseAgent
from ..services.github_service import GitHubService
from ..models.project import Project
from ..utils.event_system import EventSystem, CHANNELS
from typing import List, Dict, Optional, Any
import asyncio
import os
import uuid

class TestCase:
    def __init__(self, id: str, title: str, description: str, steps: List[str], expected_result: str):
        self.id = id
        self.title = title
        self.description = description
        self.steps = steps
        self.expected_result = expected_result
        self.actual_result = None
        self.status = "NOT_RUN"

class TestSuite:
    def __init__(self, id: str, title: str, description: str, test_cases: List[TestCase]):
        self.id = id
        self.title = title
        self.description = description
        self.test_cases = test_cases

class Tester(BaseAgent):
    def __init__(self):
        """Initialize the tester agent."""
        super().__init__("gpt-4-1106-preview")
        self.github = GitHubService()
        self.tester_id = os.getenv("TESTER_ID")
        
        if not self.tester_id:
            raise RuntimeError("TESTER_ID environment variable is required")
            
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        self.logger.info("Setting up event system")
        await self.event_system.connect()
        await self.event_system.subscribe("system", self.handle_system_message)
        await self.event_system.subscribe("story_assigned", self.handle_story_assigned)
        self._listening_task = asyncio.create_task(self.start_listening())
        self.logger.info("Event system setup complete")
        
    async def _handle_message(self, message: dict) -> Dict[str, Any]:
        """Handle a specific message type.
        
        Args:
            message: The message to handle, already decoded if it was a string.
            
        Returns:
            Dict[str, Any]: The response to the message.
            
        Raises:
            ValueError: If the message has an unknown type
        """
        if message["type"] == "test_request":
            return self.handle_test_request(message)
        else:
            error_msg = f"Unknown message type: {message['type']}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    async def handle_story_assigned(self, data: Dict):
        """Handle story assignment event"""
        self.logger.info(f"Received story assignment: {data}")
        
        # Ensure we have all required fields
        required_fields = ["story_id", "title", "description", "assigned_to"]
        if not all(field in data for field in required_fields):
            self.logger.error(f"Missing required fields in story assignment. Required: {required_fields}, Got: {list(data.keys())}")
            return
            
        if data.get("assigned_to") != self.tester_id:
            self.logger.info(f"Story assigned to {data.get('assigned_to')}, but I am {self.tester_id}. Ignoring.")
            return
            
        try:
            # Generate test suite for the story
            test_suite = self.create_test_suite(data["story_id"], data["title"], data["description"])
            
            # Run the tests
            test_results = self.run_test_suite(test_suite)
            
            # Notify about test completion
            await self.event_system.publish("tests_completed", {
                "story_id": data["story_id"],
                "tester_id": self.tester_id,
                "test_suite": test_suite.__dict__,
                "results": test_results
            })
            
        except Exception as e:
            self.logger.error(f"Failed to handle story assignment: {str(e)}")
            self.logger.error(f"Stack trace:", exc_info=True)
    
    def handle_test_request(self, message: dict) -> dict:
        """Handle test request"""
        project = Project.from_dict(message["project"])
        test_suite = self.generate_test_suite(project)
        test_results = self.run_tests(test_suite)
        
        return {
            "status": "success",
            "passed": test_results["passed"],
            "coverage": test_results["coverage"],
            "report": test_results["report"]
        }
    
    def create_test_suite(self, story_id: str, title: str, description: str) -> TestSuite:
        """Create a test suite for a story"""
        self.logger.info(f"Creating test suite for story: {title}")
        
        prompt = f"""Generate test cases for this user story:
        Title: {title}
        Description: {description}
        
        Include:
        - Unit tests
        - Integration tests
        - End-to-end tests
        - Edge cases
        - Performance tests
        
        Format each test case as:
        Title: <title>
        Description: <description>
        Steps:
        1. <step1>
        2. <step2>
        ...
        Expected Result: <expected>
        ---
        """
        
        test_cases_response = self.generate_response(prompt)
        test_cases = []
        
        for test_case_text in test_cases_response.split("---"):
            if not test_case_text.strip():
                continue
                
            lines = test_case_text.strip().split("\n")
            tc_title = lines[0].replace("Title:", "").strip()
            tc_description = lines[1].replace("Description:", "").strip()
            
            steps = []
            expected_result = ""
            
            for line in lines[2:]:
                if line.startswith("Expected Result:"):
                    expected_result = line.replace("Expected Result:", "").strip()
                elif line.strip() and not line.startswith("Steps:"):
                    steps.append(line.strip())
            
            test_case = TestCase(
                id=str(uuid.uuid4()),
                title=tc_title,
                description=tc_description,
                steps=steps,
                expected_result=expected_result
            )
            test_cases.append(test_case)
        
        return TestSuite(
            id=str(uuid.uuid4()),
            title=f"Test Suite for {title}",
            description=f"Test suite generated for story: {description}",
            test_cases=test_cases
        )
    
    def run_test_suite(self, test_suite: TestSuite) -> dict:
        """Run a test suite and collect results"""
        self.logger.info(f"Running test suite: {test_suite.title}")
        
        total_tests = len(test_suite.test_cases)
        passed_tests = 0
        test_results = {}
        
        for test_case in test_suite.test_cases:
            prompt = f"""Execute and evaluate this test case:
            Title: {test_case.title}
            Description: {test_case.description}
            Steps:
            {chr(10).join(test_case.steps)}
            Expected Result: {test_case.expected_result}
            
            Provide:
            - Pass/fail status
            - Actual result
            - Error messages (if any)
            - Performance metrics
            """
            
            result = self.generate_response(prompt)
            
            # Update test case with results
            test_case.actual_result = result
            test_case.status = "PASSED" if "PASS" in result.upper() else "FAILED"
            
            if test_case.status == "PASSED":
                passed_tests += 1
            
            test_results[test_case.id] = {
                "title": test_case.title,
                "status": test_case.status,
                "actual_result": test_case.actual_result
            }
        
        coverage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "coverage": f"{coverage:.1f}%",
            "test_cases": test_results
        }
    
    def generate_test_suite(self, project: Project) -> dict:
        """Generate a comprehensive test suite for the project."""
        self.logger.info(f"Generating test suite for project: {project.name}")
        
        test_suite = {}
        for story in project.stories:
            prompt = f"""Generate test cases for this user story:
            Title: {story.title}
            Description: {story.description}
            
            Include:
            - Unit tests
            - Integration tests
            - End-to-end tests
            - Edge cases
            - Performance tests
            """
            
            test_cases = self.generate_response(prompt)
            test_suite[story.id] = {
                "story": story.to_dict(),
                "test_cases": test_cases
            }
            
        return test_suite
    
    def run_tests(self, test_suite: dict) -> dict:
        """Run the test suite and generate a test report."""
        self.logger.info("Running test suite")
        
        total_tests = 0
        passed_tests = 0
        test_results = {}
        
        for story_id, details in test_suite.items():
            prompt = f"""Execute and evaluate these test cases:
            {details['test_cases']}
            
            Provide:
            - Pass/fail status
            - Error messages
            - Performance metrics
            """
            
            results = self.generate_response(prompt)
            
            # Parse results
            story_total = len(results.split("\n"))
            story_passed = len([r for r in results.split("\n") if "PASS" in r])
            
            total_tests += story_total
            passed_tests += story_passed
            
            test_results[story_id] = {
                "story": details['story'],
                "results": results,
                "passed": story_passed,
                "total": story_total
            }
        
        coverage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "passed": passed_tests == total_tests,
            "coverage": coverage,
            "report": test_results
        }