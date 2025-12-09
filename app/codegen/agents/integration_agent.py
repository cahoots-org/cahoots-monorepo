"""
Integration Agent

Wires together independently-developed slices into a cohesive application.
Called after all slices are complete to ensure everything works together.
"""

import json
from typing import List
from app.codegen.agents.base import CodeGenerationAgent, AgentTask


INTEGRATION_AGENT_SYSTEM_PROMPT = """You are integrating completed feature slices into a cohesive application.
Your task is to wire together independently-developed slices.

You will receive:
- List of completed slices
- Information about what each slice implemented

WORKFLOW - Follow this EXACTLY:
1. Read the main router/index file (src/routes/index.ts or app/routes/__init__.py)
2. List files in src/routes/ to see what routes exist
3. Update the main router to register any unregistered routes
4. Call done() immediately after wiring is complete

CRITICAL RULES:
- Maximum 8-10 tool calls: list files → read router → edit router → done
- Focus ONLY on wiring routes - don't rewrite features
- If routes are already registered, just verify and call done
- Do NOT run tests - just wire things together
- Act DECISIVELY - this is a wiring task, not a rewrite

Common integration fixes:
- Adding import statements for new routes
- Adding router.use() or include_router() calls
- Adding exports to index files
"""


class IntegrationAgent(CodeGenerationAgent):
    """Agent that integrates completed slices."""

    def _get_system_prompt(self) -> str:
        return INTEGRATION_AGENT_SYSTEM_PROMPT

    def _format_task(self, task: AgentTask) -> str:
        """Format integration task into a user prompt."""
        task_ctx = task.task_context or {}
        completed_tasks = task_ctx.get('completed_tasks', [])

        prompt = """Integrate all completed tasks into a cohesive application.

## Completed Tasks

"""

        if completed_tasks:
            for task_info in completed_tasks:
                desc = task_info.get('description', 'Unknown task')
                prompt += f"- {desc}\n"
                impl_details = task_info.get('implementation_details', '')
                if impl_details:
                    prompt += f"  Implementation: {impl_details[:100]}...\n"
                keywords = task_info.get('keywords', [])
                if keywords:
                    prompt += f"  Keywords: {', '.join(keywords[:5])}\n"
        else:
            prompt += "No specific task information provided. Read the codebase to understand what's been implemented.\n"

        prompt += """
## Integration Checklist

1. **Route Registration**
   - Read src/routes/index.ts (or app/routes/__init__.py)
   - Ensure all feature routes are imported and registered
   - Check route prefixes are correct

2. **Import Resolution**
   - Grep for import statements across the codebase
   - Fix any broken imports
   - Ensure index files export everything needed

3. **Shared Files**
   - Check app bootstrap (src/index.ts or app/main.py)
   - Verify middleware is properly configured
   - Check environment variable usage

4. **Cross-Task Dependencies**
   - Verify tasks that depend on each other work together
   - Check connections between related features are properly wired
   - Ensure shared modules are properly exported

## Instructions

1. First, list and read the main application files
2. Check each integration point from the checklist
3. Make any necessary fixes using edit_file
4. Document what you found and fixed

Signal completion with done() summarizing the integration status.
"""

        return prompt
