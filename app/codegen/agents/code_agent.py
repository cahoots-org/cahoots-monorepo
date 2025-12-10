"""
Code Agent

Implements code to make tests pass.
This is the second step of TDD - write minimum code to pass tests.
"""

import json
from app.codegen.agents.base import CodeGenerationAgent, AgentTask


CODE_AGENT_SYSTEM_PROMPT = """You are a senior developer implementing code to pass tests.
Your task is to write the MINIMUM code needed to make all tests pass.

You will receive:
- Path to the test file
- Slice specification with requirements
- Context from existing codebase

WORKFLOW - Follow this EXACTLY:
1. Read the test file to understand what needs to be implemented
2. Read ONE existing handler/route file to see the code patterns
3. Write your implementation files (handler + route)
4. Update the main router/index to register your new route
5. Call done() immediately after writing all files

CRITICAL RULES:
- Maximum 8-10 tool calls total: read test → read pattern → write files → done
- Do NOT search extensively - you have the test file path, start there
- If you can't find a pattern file, use standard patterns for the tech stack
- Write MINIMAL code - only what's needed to pass the tests
- Do NOT modify tests unless they have obvious bugs
- Do NOT over-engineer or add extra features
- Act DECISIVELY - don't spend iterations exploring

File organization:
- Node.js: src/handlers/{feature}.ts, src/routes/{feature}.ts
- Python: app/handlers/{feature}.py, app/routes/{feature}.py
"""


class CodeAgent(CodeGenerationAgent):
    """Agent that implements code to pass tests."""

    def _get_system_prompt(self) -> str:
        return CODE_AGENT_SYSTEM_PROMPT

    def _format_task(self, task: AgentTask) -> str:
        """Format code generation task into a user prompt."""
        slice_spec = task.slice_spec or {}
        tech_stack = task.tech_stack or "nodejs-api"

        prompt = f"""Implement code to make the tests pass.

## Test File

{task.test_file_path or 'tests/unknown.test.ts'}

## Slice Specification

```json
{json.dumps(slice_spec, indent=2)}
```

## Instructions

1. Read the test file to understand what needs to be implemented:
   - Use read_file to get the test content
   - Identify all test cases and their expectations

2. Read existing code to understand patterns:
   - List files in src/ (or app/ for Python)
   - Read existing handlers/routes to match patterns

3. Implement the feature:
   - Create handler/service files for business logic
   - Create route files for HTTP endpoints
   - Follow existing patterns exactly

4. Update shared files:
   - Add route registration in the main router
   - Add any necessary exports

Do NOT over-engineer. Write only what's needed for the tests to pass.

Signal completion with done() when finished, summarizing files created/modified.
"""

        return prompt
