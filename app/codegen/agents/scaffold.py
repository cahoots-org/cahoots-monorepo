"""
Scaffold Agent

Creates the initial project structure including:
- Package configuration (package.json, pyproject.toml, etc.)
- Project structure (src/, tests/, etc.)
- Test framework configuration
- Hello World tests to verify setup

Uses conventions from tech stack config to guide LLM generation.
"""

from app.codegen.agents.base import CodeGenerationAgent, AgentTask
from app.codegen.tech_stacks import get_tech_stack


SCAFFOLD_SYSTEM_PROMPT = """You are a senior software engineer setting up a new project.
Your task is to create a complete, working project scaffold from scratch.

You MUST create:
1. Package/dependency configuration file
2. Project structure with source and test directories
3. Test framework configuration
4. A simple "Hello World" test that verifies the setup works
5. Basic application entry point

IMPORTANT:
- Use the write_file tool to create each file
- Create files one at a time
- Do NOT use placeholder content - write complete, working code
- Follow the tech stack conventions EXACTLY
- When done, call the done() tool with a summary

Your goal is to have a project where running the test command succeeds.
"""


class ScaffoldAgent(CodeGenerationAgent):
    """Agent that creates initial project scaffolding."""

    def _get_system_prompt(self) -> str:
        return SCAFFOLD_SYSTEM_PROMPT

    def _format_task(self, task: AgentTask) -> str:
        """Format scaffold task using tech stack conventions."""
        # Tech stack is passed in task_context during generation
        tech_stack_name = (
            task.task_context.get("tech_stack") if task.task_context else None
        ) or task.tech_stack or "nodejs-api"
        tech_stack = get_tech_stack(tech_stack_name)

        if not tech_stack:
            # Fallback for unknown stacks
            return self._format_generic_task(task, tech_stack_name)

        return self._format_convention_based_task(task, tech_stack)

    def _format_convention_based_task(self, task: AgentTask, tech_stack) -> str:
        """Format task using conventions from tech stack config."""

        # Build config files section
        config_files_section = ""
        if tech_stack.config_files:
            config_files_section = "\n\nConfiguration files to create (use these exact contents):\n"
            for filename, content in tech_stack.config_files.items():
                # Replace template variables
                content = content.replace("{{project_name}}", task.project_id)
                content = content.replace("{{project_description}}", f"Project {task.project_id}")
                config_files_section += f"\n{filename}:\n```\n{content.strip()}\n```\n"

        return f"""Create a new project with the following tech stack.

Project ID: {task.project_id}
Tech Stack: {tech_stack.display_name}
Description: {tech_stack.description}
Category: {tech_stack.category}

Source Directory: {tech_stack.src_dir}/
Test Directory: {tech_stack.test_dir}/
Test Command: {tech_stack.test_command}
{config_files_section}
CONVENTIONS (follow these exactly):
{tech_stack.conventions}

REQUIREMENTS:
1. Create the configuration files listed above
2. Create the directory structure as described in conventions
3. Create a minimal entry point that demonstrates the stack works
4. Create a simple test that passes when running: {tech_stack.test_command}

Start by creating the package/dependency file, then other config files, then source files.
Signal completion with done() when finished.
"""

    def _format_generic_task(self, task: AgentTask, tech_stack_name: str) -> str:
        """Fallback for unknown tech stacks."""
        return f"""Create a new project scaffold.

Project ID: {task.project_id}
Tech Stack: {tech_stack_name}

Create a minimal working project with:
1. Appropriate package/dependency configuration
2. Source directory structure
3. Test directory structure
4. A simple test that verifies the setup works

Use best practices for the {tech_stack_name} ecosystem.
Signal completion with done() when finished.
"""
