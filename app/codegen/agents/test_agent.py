"""
Test Agent

Generates tests from slice specifications BEFORE any implementation.
This is the TDD approach - tests first, then code.
"""

import json
from typing import List, Dict
from app.codegen.agents.base import CodeGenerationAgent, AgentTask


TEST_AGENT_SYSTEM_PROMPT = """You are a TDD expert writing tests from specifications.
Your task is to generate comprehensive tests for a feature slice BEFORE any implementation exists.

You will receive:
- User story describing the feature
- Acceptance criteria in Given/When/Then format
- Event model details (commands, events, read models)

Your tests should:
1. Test each acceptance criterion exactly
2. Include edge cases and error scenarios
3. Follow the existing test patterns in the codebase
4. Use descriptive test names that explain the behavior

WORKFLOW - Follow this EXACTLY:
1. List files in tests/ to see existing patterns (if any exist)
2. If no tests exist yet, create them based on standard patterns for the tech stack
3. Use write_file to CREATE your test file - DON'T try to read files that don't exist yet
4. Call done() immediately after writing the test file

CRITICAL RULES:
- Do NOT spend iterations searching for files - act decisively
- If a file doesn't exist, CREATE it instead of searching more
- Your test file may be the FIRST test in this branch - that's fine
- Maximum 5-6 tool calls: list_files → read (optional) → write_file → done
- Write tests that will FAIL initially (since no implementation exists yet)
- Do NOT write any implementation code - tests only

Test file naming convention:
- Node.js: tests/{command-name}.test.ts
- Python: tests/test_{command_name}.py
"""


class TestAgent(CodeGenerationAgent):
    """Agent that generates tests from slice specifications."""

    def _get_system_prompt(self) -> str:
        return TEST_AGENT_SYSTEM_PROMPT

    def _format_task(self, task: AgentTask) -> str:
        """Format test generation task into a user prompt."""
        slice_spec = task.slice_spec or {}
        tech_stack = task.tech_stack or "nodejs-api"

        # Build the prompt
        prompt = f"""Generate tests for this feature slice.

## Slice Specification

Type: {slice_spec.get('type', 'state_change')}
"""

        if slice_spec.get('type') == 'state_change':
            prompt += f"Command: {slice_spec.get('command', 'Unknown')}\n"
            prompt += f"Events: {', '.join(slice_spec.get('events', []))}\n"
        elif slice_spec.get('type') == 'state_view':
            prompt += f"Read Model: {slice_spec.get('read_model', 'Unknown')}\n"
            prompt += f"Source Events: {', '.join(slice_spec.get('source_events', []))}\n"
        elif slice_spec.get('type') == 'automation':
            prompt += f"Automation: {slice_spec.get('automation_name', 'Unknown')}\n"
            prompt += f"Trigger Event: {slice_spec.get('trigger_event', 'Unknown')}\n"
            prompt += f"Result Events: {', '.join(slice_spec.get('result_events', []))}\n"

        # Add user story if available
        if slice_spec.get('user_story'):
            prompt += f"""
## User Story

{slice_spec.get('user_story')}
"""

        # Add acceptance criteria
        gwt_scenarios = slice_spec.get('gwt_scenarios', [])
        if gwt_scenarios:
            prompt += """
## Acceptance Criteria (Given/When/Then)

"""
            prompt += self._format_gwt_scenarios(gwt_scenarios)

        # Add instructions based on tech stack
        test_path = self._get_test_path(slice_spec, tech_stack)
        prompt += f"""
## Instructions

1. First, read existing test files to understand the project's testing patterns:
   - List files in the tests/ directory
   - Read any existing test file to understand patterns
2. Create a new test file at: {test_path}
3. Write tests for EACH acceptance criterion above
4. Include edge cases and error scenarios
5. Do NOT write any implementation code - tests only

Signal completion with the done() tool when finished, summarizing the tests created.
"""

        return prompt

    def _format_gwt_scenarios(self, scenarios: List[Dict]) -> str:
        """Format Given/When/Then scenarios."""
        lines = []
        for i, scenario in enumerate(scenarios, 1):
            lines.append(f"### Scenario {i}")
            if scenario.get('given'):
                lines.append(f"**Given** {scenario['given']}")
            if scenario.get('when'):
                lines.append(f"**When** {scenario['when']}")
            if scenario.get('then'):
                lines.append(f"**Then** {scenario['then']}")
            lines.append("")
        return "\n".join(lines)

    def _get_test_path(self, slice_spec: Dict, tech_stack: str) -> str:
        """Generate test file path from slice spec."""
        # Get the name from slice spec
        if slice_spec.get('type') == 'state_change':
            name = slice_spec.get('command', 'unknown')
        elif slice_spec.get('type') == 'state_view':
            name = slice_spec.get('read_model', 'unknown')
        else:
            name = slice_spec.get('automation_name', 'unknown')

        # Convert CamelCase to kebab-case
        import re
        kebab = re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()

        if tech_stack.startswith("node"):
            return f"tests/{kebab}.test.ts"
        else:
            # Python uses snake_case
            snake = kebab.replace('-', '_')
            return f"tests/test_{snake}.py"
