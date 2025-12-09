"""
Fix Agent

Analyzes failing tests and fixes the implementation.
This agent is called when tests fail after code generation.
"""

import json
from app.codegen.agents.base import CodeGenerationAgent, AgentTask


FIX_AGENT_SYSTEM_PROMPT = """You are debugging failing tests.
Your task is to analyze test failures and fix the implementation code.

You will receive:
- Test error details (test name, file, line, error message)
- Slice specification for context

WORKFLOW - Follow this EXACTLY:
1. Read the error message carefully - it tells you what's wrong
2. Read the failing test to understand the expectation
3. Read the implementation file to find the bug
4. Make ONE targeted fix using edit_file
5. Call done() immediately after fixing

CRITICAL RULES:
- Maximum 5-6 tool calls: read test → read impl → edit_file → done
- The error message is your PRIMARY diagnostic - use it
- Do NOT search extensively - you have the file paths in the error
- Make the SMALLEST change that fixes the issue
- Do NOT modify tests unless they're clearly wrong
- If you can't find the bug quickly, make your best guess fix and move on
- Act DECISIVELY - don't spend iterations exploring

Common issues (check these first):
- Missing exports or imports
- Incorrect response format (JSON structure)
- Wrong HTTP status codes
- Missing error handling
- Typos in endpoint paths or property names
- Async/await issues
"""


class FixAgent(CodeGenerationAgent):
    """Agent that fixes failing tests."""

    def _get_system_prompt(self) -> str:
        return FIX_AGENT_SYSTEM_PROMPT

    def _format_task(self, task: AgentTask) -> str:
        """Format fix task into a user prompt."""
        test_error = task.test_error or {}

        prompt = """Fix the failing tests.

## Test Error

"""

        if test_error:
            prompt += f"""```
{test_error.get('error', 'Unknown error')}
```

Failed test: {test_error.get('test', 'Unknown test')}
File: {test_error.get('file', 'Unknown file')}
Line: {test_error.get('line', 0)}
"""
        else:
            prompt += "Error details not available. Please read the test file to understand what's failing.\n"

        prompt += """
## Instructions

1. Read the failing test to understand the expectation:
   - Use read_file to get the test content
   - Focus on the specific test that failed

2. Read the implementation to find the bug:
   - Use grep to find relevant code
   - Read the handler/route files

3. Fix the issue:
   - Use edit_file for small changes
   - Use write_file only if major rewrites needed
   - Make minimal changes

4. Do NOT change the test unless it's clearly wrong:
   - If you must change a test, explain why first
   - Test expectations usually reflect requirements

Signal completion with done() when the issue is fixed.
"""

        return prompt
