"""Service for generating test suites from user stories."""
import re
from typing import List, Optional

from src.models.qa_suite import TestSuite, TestCase, TestStatus
from src.utils.model import Model
from src.utils.base_logger import BaseLogger

class QASuiteGenerator:
    """Service for generating test suites from user stories."""
    
    def __init__(self, model: Model, logger: BaseLogger) -> None:
        """Initialize the QA suite generator."""
        self.model = model
        self.logger = logger

    async def generate_test_suite(
        self,
        story_id: str,
        title: str,
        description: str
    ) -> TestSuite:
        """Generate a test suite for a user story."""
        self.logger.info(f"Generating test suite for story {story_id}")
        
        try:
            response = await self.model.generate_response(
                self._build_prompt(story_id, description)
            )
            if not response.strip():
                self.logger.warning("Empty response received from model")
                return self._create_default_test_suite(story_id, title, description)
                
            test_cases = self._parse_test_cases(response)
            if not test_cases:
                self.logger.warning("No valid test cases parsed from response")
                return self._create_default_test_suite(story_id, title, description)
                
            return TestSuite(
                story_id=story_id,
                title=f"Test Suite for {title}",
                description=f"Test suite generated for story: {description}",
                test_cases=test_cases
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate test suite: {str(e)}")
            return self._create_default_test_suite(story_id, title, description)

    def _build_prompt(self, story_id: str, description: str) -> str:
        """Build the prompt for test case generation."""
        return f"""Generate test cases for story {story_id}: {description}

Please provide test cases in the following format:

Title: [Test case title]
Description: [Test case description]
Steps:
1. [First step]
2. [Second step]
...
Expected Result: [Expected outcome]

---
[Additional test cases in the same format]"""

    def _parse_test_cases(self, response: str) -> List[TestCase]:
        """Parse test cases from model response."""
        test_cases = []
        current_test_case = None
        current_section = None
        steps = []
        
        for line in response.split('\n'):
            line = line.strip()
            
            if not line:
                continue
                
            if line.startswith('---'):
                if current_test_case and steps:
                    current_test_case.steps = steps
                    test_cases.append(current_test_case)
                current_test_case = None
                current_section = None
                steps = []
                continue

            if line.startswith('Title:'):
                if current_test_case and steps:
                    current_test_case.steps = steps
                    test_cases.append(current_test_case)
                
                current_test_case = TestCase(
                    title=line[6:].strip() or "Test Case",
                    description="",
                    steps=[],
                    expected_result=""
                )
                current_section = 'title'
                steps = []
                
            elif line.startswith('Description:'):
                if current_test_case:
                    current_test_case.description = line[12:].strip() or "Test case description"
                current_section = 'description'
                
            elif line.startswith('Steps:'):
                current_section = 'steps'
                steps = []
                
            elif line.startswith('Expected Result:'):
                if current_test_case:
                    current_test_case.expected_result = line[15:].strip() or "Test should complete successfully"
                current_section = 'expected_result'
                
            elif current_section == 'steps':
                if line[0].isdigit() or line[0] in ['*', '-']:
                    steps.append(line)

        # Handle the last test case
        if current_test_case and steps:
            current_test_case.steps = steps
            test_cases.append(current_test_case)

        return test_cases

    def _create_default_test_suite(self, story_id: str, title: str, description: str) -> TestSuite:
        """Create a default test suite when generation fails."""
        return TestSuite(
            story_id=story_id,
            title=f"Test Suite for {title}",
            description=f"Test suite generated for story: {description}",
            test_cases=[self._create_default_test_case()]
        )

    def _create_default_test_case(self) -> TestCase:
        """Create a default test case when no valid test cases are parsed."""
        return TestCase(
            title="Test Case",
            description="Basic test case",
            steps=["1. Verify basic functionality"],
            expected_result="Test should complete successfully"
        ) 