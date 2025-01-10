"""Service for generating test suites from user stories."""
import re
from logging import Logger
from typing import List

from src.models.qa_suite import TestSuite, TestCase
from src.utils.model import Model

class QASuiteGenerator:
    """Service for generating test suites from user stories."""
    
    def __init__(self, model: Model, logger: Logger) -> None:
        """Initialize the QA suite generator.
        
        Args:
            model: Model for generating test cases
            logger: Logger instance
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
        
        try:
            # Generate test cases using the model
            prompt = self._build_prompt(title, description)
            try:
                response = await self.model.generate_response(prompt)
                test_cases = self._parse_test_cases(response)
            except Exception as e:
                self.logger.warning(f"First attempt failed: {str(e)}, retrying...")
                response = await self.model.generate_response(prompt)
                test_cases = self._parse_test_cases(response)
            
            if not test_cases:
                # If no valid test cases were parsed, create a default test case
                test_cases = [self._create_default_test_case(title)]
                self.logger.warning("No valid test cases parsed, using default test case")
            
        except Exception as e:
            # Handle any errors by creating a default test case
            self.logger.error(f"Error generating test cases: {str(e)}")
            test_cases = [self._create_default_test_case(title)]
            
        # Create and return test suite
        test_suite = TestSuite(
            story_id=story_id,
            title=f"Test Suite for {title}",
            description=f"Test suite generated for story: {description}",
            test_cases=test_cases
        )
        
        self.logger.info(f"Generated test suite with {len(test_cases)} test cases")
        return test_suite
        
    def _create_default_test_case(self, title: str) -> TestCase:
        """Create a default test case when generation fails.
        
        Args:
            title: The story title
            
        Returns:
            A default test case
        """
        return TestCase(
            title=f"Basic {title} Test",
            description=f"Basic test case for {title}",
            steps=["Verify basic functionality"],
            expected_result="Basic functionality works as expected"
        )
        
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
        
        # Split into sections, handling missing section markers
        sections = []
        current_section = []
        for line in response.splitlines():
            if line.strip() == "---":
                if current_section:
                    sections.append("\n".join(current_section))
                    current_section = []
            elif line.strip().startswith("Title:") and current_section:
                # New test case without section marker
                sections.append("\n".join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        if current_section:
            sections.append("\n".join(current_section))
        
        for raw_case in sections:
            try:
                # Extract test case components using regex
                title_match = re.search(r"Title:\s*(.+?)(?=\n|Description:|Steps:|Expected Result:|$)", raw_case, re.DOTALL)
                desc_match = re.search(r"Description:\s*(.+?)(?=\n|Steps:|Expected Result:|$)", raw_case, re.DOTALL)
                steps_section = re.search(r"Steps:\n(.*?)(?=Expected Result:|$)", raw_case, re.DOTALL)
                result_match = re.search(r"Expected Result:\s*(.+?)(?=\n|$)", raw_case, re.DOTALL)
                
                # Log warning and skip if any required field is missing
                if not title_match:
                    self.logger.warning(f"Missing title in test case: {raw_case[:100]}...")
                    continue
                if not desc_match:
                    self.logger.warning(f"Missing description in test case: {raw_case[:100]}...")
                    continue
                if not steps_section:
                    self.logger.warning(f"Missing or invalid steps in test case: {raw_case[:100]}...")
                    continue
                if not result_match:
                    self.logger.warning(f"Missing expected result in test case: {raw_case[:100]}...")
                    continue
                
                # Extract steps from the steps section
                steps = []
                steps_text = steps_section.group(1).strip()
                
                # Split steps by line and process each line
                current_step = []
                for line in steps_text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Check if this is a new step
                    step_match = re.match(r"(\d+\.)\s*(.+)", line)
                    bullet_match = re.match(r"[-*]\s*(.+)", line)
                    if step_match:
                        # Save previous step if exists
                        if current_step:
                            step_text = " ".join(current_step)
                            step_text = step_text.replace("\\n", "\n").replace("\\t", "\t")
                            steps.append(step_text)
                            current_step = []
                        
                        # Start new step
                        current_step.append(step_match.group(2))
                    elif bullet_match:
                        # Save previous step if exists
                        if current_step:
                            step_text = " ".join(current_step)
                            step_text = step_text.replace("\\n", "\n").replace("\\t", "\t")
                            steps.append(step_text)
                            current_step = []
                        
                        # Start new step
                        current_step.append(bullet_match.group(1))
                    else:
                        # Continue previous step
                        if current_step:
                            current_step.append(line)
                        else:
                            # Skip invalid step format
                            continue
                
                # Add last step if exists
                if current_step:
                    step_text = " ".join(current_step)
                    step_text = step_text.replace("\\n", "\n").replace("\\t", "\t")
                    steps.append(step_text)
                
                if not steps:
                    self.logger.warning(f"No valid steps found in test case: {raw_case[:100]}...")
                    continue
                
                test_case = TestCase(
                    title=title_match.group(1).strip(),
                    description=desc_match.group(1).strip(),
                    steps=steps,
                    expected_result=result_match.group(1).strip()
                )
                test_cases.append(test_case)
                
            except Exception as e:
                self.logger.warning(f"Error parsing test case: {str(e)}\nCase content: {raw_case[:100]}...")
                continue
                
        return test_cases 