"""Service for generating test suites from user stories."""
import re
from logging import Logger
from typing import List

from src.models.test_suite import TestSuite, TestCase
from src.utils.model import Model

class TestSuiteGenerator:
    """Service for generating test suites from user stories."""

    def __init__(self, model: Model, logger: Logger) -> None:
        """Initialize the test suite generator.
        
        Args:
            model: The model to use for generating test cases
            logger: Logger for recording events
        """
        self.model = model
        self.logger = logger

    async def generate_test_suite(self, story_id: str, title: str, description: str) -> TestSuite:
        """Generate a test suite for a user story.
        
        Args:
            story_id: The ID of the user story
            title: The title of the user story
            description: The description of the user story
            
        Returns:
            A test suite containing test cases for the story
        """
        self.logger.info(f"Generating test suite for story {story_id}: {title}")

        # Generate test cases using the model
        prompt = self._build_prompt(title, description)
        response = await self.model.generate_response(prompt)
        test_cases = self._parse_test_cases(response)

        # Create and return test suite
        test_suite = TestSuite(
            story_id=story_id,
            title=f"Test Suite for {title}",
            description=f"Test suite generated for story: {description}",
            test_cases=test_cases
        )
        
        self.logger.info(f"Generated test suite with {len(test_cases)} test cases")
        return test_suite

    def _build_prompt(self, title: str, description: str) -> str:
        """Build the prompt for generating test cases.
        
        Args:
            title: The story title
            description: The story description
            
        Returns:
            The prompt for the model
        """
        return f"""Generate test cases for the following user story:

Title: {title}
Description: {description}

For each test case, provide:
- Title
- Description
- Steps (numbered list)
- Expected Result

Format each test case like this:
Title: [test case title]
Description: [test case description]
Steps:
1. [step 1]
2. [step 2]
...
Expected Result: [expected result]
---

Generate at least 2 test cases, including both positive and negative scenarios."""

    def _parse_test_cases(self, response: str) -> List[TestCase]:
        """Parse test cases from the model response.
        
        Args:
            response: The model's response text
            
        Returns:
            List of parsed test cases
        """
        test_cases = []
        raw_cases = [case.strip() for case in response.split("---") if case.strip()]

        for raw_case in raw_cases:
            # Extract test case components using regex
            title_match = re.search(r"Title:\s*(.+?)(?=\n|Description:)", raw_case, re.DOTALL)
            desc_match = re.search(r"Description:\s*(.+?)(?=\n|Steps:)", raw_case, re.DOTALL)
            steps_section = re.search(r"Steps:\n((?:\d+\..+?\n)+)", raw_case, re.DOTALL)
            result_match = re.search(r"Expected Result:\s*(.+?)(?=\n|$)", raw_case, re.DOTALL)

            if all([title_match, desc_match, steps_section, result_match]):
                # Extract steps from the steps section
                steps = [step.strip() for step in re.findall(r"\d+\.\s*(.+?)(?=\n|$)", steps_section.group(1))]
                
                test_case = TestCase(
                    title=title_match.group(1).strip(),
                    description=desc_match.group(1).strip(),
                    steps=steps,
                    expected_result=result_match.group(1).strip()
                )
                test_cases.append(test_case)

        return test_cases 