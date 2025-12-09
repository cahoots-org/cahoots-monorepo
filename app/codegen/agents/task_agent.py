"""
Task Agent

Implements a single task from the decomposition using TDD:
1. Register with Contex to get relevant file context
2. Write tests based on task description and implementation details
3. Write implementation code
4. Run tests via runner-service
5. Fix failures until tests pass
6. Merge to main
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.codegen.agents.base import AgentTask, AgentResult, MAX_ITERATIONS, AGENT_TIMEOUT_SECONDS
from app.codegen.agents.tools import WORKSPACE_TOOLS
from app.codegen.agents.merge_agent import MergeAgent, MergeAgentConfig
from app.codegen.tech_stacks import get_tech_stack
from app.services.context_engine_client import ContextEngineClient


# Task agent system prompt - uses task description and implementation details
TASK_AGENT_SYSTEM_PROMPT = """You are a TDD developer implementing a specific feature task.

Your job is to implement a single task following Test-Driven Development:
1. Write comprehensive tests based on the task description
2. Write minimal code to make tests pass
3. Tests will be run automatically - if they fail, you'll receive error details to fix

You will receive:
- Task description: What needs to be implemented
- Implementation details: How to implement it (technical approach)
- Related files: Context from previously completed tasks
- Tech stack information

WORKFLOW:
1. Review the task description and implementation details carefully
2. Review the relevant files provided to understand existing patterns
3. Write tests that verify the task requirements are met
4. Write implementation code following existing patterns
5. Call done() - tests will run automatically

CRITICAL RULES:
- The implementation_details contain specific technical guidance - follow it closely
- You have relevant file contents provided - use them to understand patterns
- Follow existing code patterns exactly
- Write MINIMAL code to satisfy the task
- Focus on what the task description asks for
- Call done() when implementation is complete

If tests fail after you call done(), you'll receive the error details and can fix them.
"""


@dataclass
class TaskAgentConfig:
    """Configuration for the task agent."""
    workspace_url: str
    runner_url: str
    llm_model: str = "llama-3.3-70b"
    max_fix_attempts: int = 3


class TaskAgent:
    """
    Agent that handles the complete TDD cycle for a task.

    Uses task_context containing description and implementation_details
    to guide code generation.
    """

    def __init__(
        self,
        config: TaskAgentConfig,
        contex_client: Optional[ContextEngineClient] = None,
        llm_client: Any = None,
    ):
        self.config = config
        self.contex = contex_client
        self._llm_client = llm_client

        # MergeAgent will be fetched lazily as singleton
        self._merge_agent: Optional[MergeAgent] = None

        # Track state during run
        self._files_created: List[str] = []
        self._files_modified: List[str] = []
        self._commits: List[str] = []
        self._relevant_files: Dict[str, str] = {}  # path -> content

    async def _get_merge_agent(self) -> MergeAgent:
        """Get the shared MergeAgent singleton instance."""
        if self._merge_agent is None:
            merge_config = MergeAgentConfig(
                workspace_url=self.config.workspace_url,
                runner_url=self.config.runner_url,
                llm_model=self.config.llm_model
            )
            self._merge_agent = await MergeAgent.get_instance(
                config=merge_config,
                contex_client=self.contex,
                llm_client=self._llm_client
            )
        return self._merge_agent

    @property
    def llm(self):
        """Get or create the LLM client."""
        if self._llm_client is None:
            import os
            from app.analyzer.llm_client import CerebrasLLMClient

            api_key = os.getenv("CEREBRAS_API_KEY")
            if api_key:
                self._llm_client = CerebrasLLMClient(
                    api_key=api_key,
                    model=os.getenv("CEREBRAS_MODEL", self.config.llm_model)
                )
        return self._llm_client

    async def run(self, task: AgentTask) -> AgentResult:
        """
        Execute the full TDD cycle for a task.

        1. Register with Contex and get relevant files
        2. Run agent loop to generate tests + code
        3. Run tests
        4. If tests fail, fix and retry
        5. Rebase and merge to main
        """
        start_time = datetime.now(timezone.utc)
        self._files_created = []
        self._files_modified = []
        self._commits = []

        task_ctx = task.task_context or {}
        task_id = task_ctx.get("task_id", task.task_id)
        task_desc = task_ctx.get("description", "Unknown task")[:60]

        try:
            # Step 1: Register with Contex and get relevant files
            await self._register_and_fetch_context(task)

            # Step 2: Run agent loop to generate tests + code
            agent_result = await self._run_agent_loop(task)

            if not agent_result.success:
                return agent_result

            # Step 3: Run tests and fix loop
            for attempt in range(self.config.max_fix_attempts):
                test_result = await self._run_tests(task)

                if test_result.get("passed", False):
                    # Tests pass! Proceed to merge
                    break

                # Tests failed - try to fix
                if attempt < self.config.max_fix_attempts - 1:
                    fix_result = await self._fix_failures(task, test_result)
                    if not fix_result.success:
                        return AgentResult(
                            success=False,
                            error=f"Failed to fix tests after {attempt + 1} attempts: {fix_result.error}",
                            files_created=self._files_created,
                            files_modified=self._files_modified,
                            commits=self._commits,
                            iterations=agent_result.iterations,
                            duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
                        )
            else:
                # Exhausted fix attempts
                return AgentResult(
                    success=False,
                    error=f"Tests still failing after {self.config.max_fix_attempts} fix attempts",
                    files_created=self._files_created,
                    files_modified=self._files_modified,
                    commits=self._commits,
                    iterations=agent_result.iterations,
                    duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
                )

            # Step 4: Rebase and merge
            merge_result = await self._rebase_and_merge(task)

            if not merge_result.get("ok"):
                return AgentResult(
                    success=False,
                    error=f"Merge failed: {merge_result.get('error', 'Unknown error')}",
                    files_created=self._files_created,
                    files_modified=self._files_modified,
                    commits=self._commits,
                    iterations=agent_result.iterations,
                    duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
                )

            return AgentResult(
                success=True,
                summary=f"Task '{task_desc}' complete: tests passing, merged to main",
                files_created=self._files_created,
                files_modified=self._files_modified,
                commits=self._commits,
                iterations=agent_result.iterations,
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
            )

        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                files_created=self._files_created,
                files_modified=self._files_modified,
                commits=self._commits,
                iterations=0,
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
            )

    async def _register_and_fetch_context(self, task: AgentTask) -> None:
        """Register with Contex and fetch relevant files."""
        task_ctx = task.task_context or {}

        # Get any files passed from dependencies
        related_files = task_ctx.get("related_files", [])

        # Fetch related files from workspace if provided
        if related_files:
            await self._fetch_file_contents(task, related_files[:10])

        if not self.contex:
            return

        # Build semantic needs based on task keywords
        keywords = task_ctx.get("keywords", [])
        description = task_ctx.get("description", "")
        implementation_details = task_ctx.get("implementation_details", "")

        try:
            # Register with Contex
            agent_id = f"task-agent-{task.task_id}"
            needs = self._build_semantic_needs(description, implementation_details, keywords)

            await self.contex.register_agent(
                agent_id=agent_id,
                project_id=task.project_id,
                data_needs=needs
            )

            # Query for relevant files using description
            query = f"files related to: {description[:200]}"
            results = await self.contex.query(
                project_id=task.project_id,
                query=query,
                limit=15
            )

            # Extract file paths from results
            relevant_paths = []
            for result in results:
                data = result.get("data", {})
                if "file_path" in data:
                    relevant_paths.append(data["file_path"])
                elif "path" in data:
                    relevant_paths.append(data["path"])

            # Fetch file contents from workspace
            if relevant_paths:
                await self._fetch_file_contents(task, relevant_paths)

        except Exception as e:
            # Contex failure is not fatal - agent can still work
            import logging
            logging.warning(f"Contex registration failed: {e}")

    def _build_semantic_needs(
        self,
        description: str,
        implementation_details: str,
        keywords: List[str]
    ) -> List[str]:
        """Build semantic needs list based on task details."""
        needs = [
            "existing code patterns and conventions",
            "test file patterns and examples",
            description[:100],
        ]

        if implementation_details:
            needs.append(f"code related to: {implementation_details[:100]}")

        # Add keyword-based needs
        for keyword in keywords[:5]:
            needs.append(f"files related to {keyword}")

        return needs

    async def _fetch_file_contents(self, task: AgentTask, paths: List[str]) -> None:
        """Fetch file contents from workspace service."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            for path in paths[:10]:  # Limit to 10 files
                if path in self._relevant_files:
                    continue  # Already fetched

                try:
                    response = await client.post(
                        f"{self.config.workspace_url}/workspace/{task.project_id}/files/read",
                        params={"branch": task.branch},
                        json={"path": path}
                    )
                    if response.status_code == 200:
                        content = response.json().get("content", "")
                        self._relevant_files[path] = content
                except Exception:
                    pass  # Skip files that can't be read

    async def _run_agent_loop(self, task: AgentTask) -> AgentResult:
        """Run the LLM agent loop to generate tests and code."""
        start_time = datetime.now(timezone.utc)

        # Build the prompt with pre-fetched context
        user_prompt = self._format_task_prompt(task)

        messages = [
            {"role": "system", "content": TASK_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            async with asyncio.timeout(AGENT_TIMEOUT_SECONDS):
                for iteration in range(MAX_ITERATIONS):
                    response = await self._call_llm(messages)
                    tool_calls = self._parse_tool_calls(response)

                    if not tool_calls:
                        # Check for completion
                        content = self._get_response_content(response)
                        if self._looks_complete(content):
                            return AgentResult(
                                success=True,
                                summary=content,
                                files_created=self._files_created,
                                files_modified=self._files_modified,
                                commits=self._commits,
                                iterations=iteration + 1,
                                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
                            )
                        # Prompt to continue
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": "Use the tools to complete the task. Call done() when finished."})
                        continue

                    # Process tool calls
                    messages.append({
                        "role": "assistant",
                        "content": self._get_response_content(response),
                        "tool_calls": [
                            {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                            for tc in tool_calls
                        ]
                    })

                    for tc in tool_calls:
                        if tc["name"] == "done":
                            args = json.loads(tc["arguments"])
                            return AgentResult(
                                success=True,
                                summary=args.get("summary", "Task completed"),
                                files_created=self._files_created,
                                files_modified=self._files_modified,
                                commits=self._commits,
                                iterations=iteration + 1,
                                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
                            )

                        result = await self._execute_tool(task, tc)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result
                        })

                return AgentResult(
                    success=False,
                    error="Max iterations reached",
                    files_created=self._files_created,
                    files_modified=self._files_modified,
                    commits=self._commits,
                    iterations=MAX_ITERATIONS,
                    duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
                )

        except asyncio.TimeoutError:
            return AgentResult(
                success=False,
                error=f"Agent timeout after {AGENT_TIMEOUT_SECONDS} seconds",
                iterations=0,
                duration_seconds=AGENT_TIMEOUT_SECONDS
            )

    def _format_task_prompt(self, task: AgentTask) -> str:
        """Format the task prompt including pre-fetched context."""
        task_ctx = task.task_context or {}

        description = task_ctx.get("description", "No description provided")
        implementation_details = task_ctx.get("implementation_details", "")
        story_points = task_ctx.get("story_points", 0)
        keywords = task_ctx.get("keywords", [])

        prompt = f"""Implement this feature task using TDD.

## Task Description

{description}
"""

        if implementation_details:
            prompt += f"""
## Implementation Details

{implementation_details}
"""

        if story_points:
            prompt += f"""
## Complexity

Story Points: {story_points} (1-3: small, 4-5: medium, 6+: larger feature)
"""

        if keywords:
            prompt += f"""
## Keywords

{', '.join(keywords)}
"""

        # Add pre-fetched file context
        if self._relevant_files:
            prompt += "\n## Relevant Existing Files\n\n"
            prompt += "These files were identified as relevant. Use them to understand existing patterns:\n\n"
            for path, content in self._relevant_files.items():
                # Truncate very long files
                content_preview = content[:3000] if len(content) > 3000 else content
                prompt += f"### {path}\n```\n{content_preview}\n```\n\n"

        # Add related code from dependencies
        related_code = task_ctx.get("related_code", [])
        if related_code:
            prompt += "\n## Code from Completed Dependencies\n\n"
            prompt += "This code was created by tasks that this task depends on:\n\n"
            for code_block in related_code[:3]:  # Limit to 3 blocks
                prompt += f"```\n{code_block[:1500]}\n```\n\n"

        # Get tech stack conventions
        tech_stack_name = task_ctx.get("tech_stack", "nodejs-api")
        tech_stack = get_tech_stack(tech_stack_name)

        prompt += f"""
## Tech Stack

{tech_stack.display_name if tech_stack else tech_stack_name}
"""

        if tech_stack and tech_stack.conventions:
            prompt += f"""
## Conventions (FOLLOW THESE EXACTLY)

{tech_stack.conventions}
"""

        prompt += """
## Instructions

1. Write tests first (TDD) - tests should verify the task requirements
2. Implement minimal code to pass tests
3. Follow the conventions above
4. The implementation_details tell you HOW to implement - follow them closely
5. Call done() when complete
"""

        return prompt

    async def _call_llm(self, messages: List[Dict]) -> Dict:
        """Call the LLM with tools."""
        return await self.llm.chat_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=4000,
            tools=WORKSPACE_TOOLS
        )

    def _get_response_content(self, response: Dict) -> str:
        """Extract content from LLM response."""
        if "choices" in response:
            choices = response.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "") or ""
        return response.get("content", "") or ""

    def _parse_tool_calls(self, response: Dict) -> List[Dict]:
        """Parse tool calls from LLM response."""
        message = response
        if "choices" in response:
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})

        raw_calls = message.get("tool_calls", [])
        return [
            {
                "id": tc.get("id", f"call_{i}"),
                "name": tc.get("function", {}).get("name", ""),
                "arguments": tc.get("function", {}).get("arguments", "{}")
            }
            for i, tc in enumerate(raw_calls)
        ]

    def _looks_complete(self, content: str) -> bool:
        """Check if response indicates completion."""
        lower = content.lower()
        return any(phrase in lower for phrase in [
            "complete", "finished", "done", "implemented",
            "all tests", "tests cover", "task complete"
        ])

    async def _execute_tool(self, task: AgentTask, tool_call: Dict) -> str:
        """Execute a tool call."""
        name = tool_call["name"]
        try:
            args = json.loads(tool_call["arguments"])
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments"

        async with httpx.AsyncClient(timeout=30.0) as client:
            if name == "read_file":
                response = await client.post(
                    f"{self.config.workspace_url}/workspace/{task.project_id}/files/read",
                    params={"branch": task.branch},
                    json={"path": args.get("path", "")}
                )
                if response.status_code == 200:
                    return response.json().get("content", "")
                return f"File not found: {args.get('path')}"

            elif name == "write_file":
                path = args.get("path", "")
                response = await client.post(
                    f"{self.config.workspace_url}/workspace/{task.project_id}/files/write",
                    params={"branch": task.branch},
                    json={"path": path, "content": args.get("content", "")}
                )
                if response.status_code == 200:
                    data = response.json()
                    if path not in self._files_created:
                        self._files_created.append(path)
                    if data.get("commit"):
                        self._commits.append(data["commit"])
                    return f"File written: {path}"
                return f"Error writing file: {response.text}"

            elif name == "edit_file":
                path = args.get("path", "")
                response = await client.post(
                    f"{self.config.workspace_url}/workspace/{task.project_id}/files/edit",
                    params={"branch": task.branch},
                    json={
                        "path": path,
                        "old": args.get("old_text", ""),
                        "new": args.get("new_text", "")
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if path not in self._files_modified:
                        self._files_modified.append(path)
                    if data.get("commit"):
                        self._commits.append(data["commit"])
                    return f"File edited: {path}"
                return f"Error editing file: {response.text}"

            elif name == "list_files":
                response = await client.post(
                    f"{self.config.workspace_url}/workspace/{task.project_id}/files/list",
                    params={"branch": task.branch},
                    json={"path": args.get("path", "."), "pattern": args.get("pattern", "*")}
                )
                if response.status_code == 200:
                    files = response.json().get("files", [])
                    return "Files:\n" + "\n".join(f"  - {f}" for f in files)
                return "Error listing files"

            elif name == "grep":
                response = await client.post(
                    f"{self.config.workspace_url}/workspace/{task.project_id}/files/grep",
                    params={"branch": task.branch},
                    json={"pattern": args.get("pattern", ""), "path": args.get("path", ".")}
                )
                if response.status_code == 200:
                    matches = response.json().get("matches", [])
                    if not matches:
                        return "No matches found"
                    return "Matches:\n" + "\n".join(f"  {m['file']}:{m['line']}: {m['content']}" for m in matches[:20])
                return "Error searching"

            else:
                return f"Unknown tool: {name}"

    async def _run_tests(self, task: AgentTask) -> Dict:
        """Run tests via the runner service."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                # Create test run
                response = await client.post(
                    f"{self.config.runner_url}/runs",
                    json={
                        "project_id": task.project_id,
                        "command": self._get_test_command(task),
                        "branch": task.branch,
                    }
                )

                if response.status_code != 200:
                    return {"passed": False, "error": "Failed to create test run"}

                run_id = response.json().get("run_id")

                # Poll for completion
                for _ in range(60):
                    await asyncio.sleep(5)
                    status = await client.get(f"{self.config.runner_url}/runs/{run_id}")
                    if status.status_code == 200:
                        data = status.json()
                        run_status = data.get("status", "").lower()
                        if run_status == "passed":
                            return {"passed": True, "results": data}
                        elif run_status in ("completed",):
                            return data.get("results", {"passed": True})
                        elif run_status in ("failed", "error", "timeout"):
                            return {"passed": False, "error": data.get("error", f"Test run {run_status}")}

                return {"passed": False, "error": "Test run timed out"}

            except Exception as e:
                return {"passed": False, "error": str(e)}

    def _get_test_command(self, task: AgentTask) -> str:
        """Get test command for tech stack."""
        tech_stack = (task.task_context or {}).get("tech_stack", "nodejs-api")
        commands = {
            "nodejs-api": "npm test",
            "python-api": "pytest",
            "go-api": "go test -v ./...",
        }
        return commands.get(tech_stack, "npm test")

    async def _fix_failures(self, task: AgentTask, test_result: Dict) -> AgentResult:
        """Run agent loop to fix test failures."""
        start_time = datetime.now(timezone.utc)
        task_ctx = task.task_context or {}
        description = task_ctx.get("description", "")[:100]

        error_details = test_result.get("error", "Unknown error")
        failures = test_result.get("failures", [])

        fix_prompt = f"""The tests failed for task: "{description}"

Please fix the implementation.

## Test Failures

{error_details}

{json.dumps(failures, indent=2) if failures else "No detailed failure info available."}

## Instructions

1. Read the error messages carefully
2. Identify the bug in your implementation
3. Fix the code using edit_file
4. Call done() when the fix is complete
"""

        messages = [
            {"role": "system", "content": TASK_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": fix_prompt}
        ]

        try:
            async with asyncio.timeout(AGENT_TIMEOUT_SECONDS):
                for iteration in range(MAX_ITERATIONS // 2):  # Fewer iterations for fixes
                    response = await self._call_llm(messages)
                    tool_calls = self._parse_tool_calls(response)

                    if not tool_calls:
                        content = self._get_response_content(response)
                        if self._looks_complete(content):
                            return AgentResult(success=True, summary="Fix applied", iterations=iteration + 1)
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": "Use edit_file to fix the code, then call done()."})
                        continue

                    messages.append({
                        "role": "assistant",
                        "content": self._get_response_content(response),
                        "tool_calls": [
                            {"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}
                            for tc in tool_calls
                        ]
                    })

                    for tc in tool_calls:
                        if tc["name"] == "done":
                            return AgentResult(success=True, summary="Fix applied", iterations=iteration + 1)

                        result = await self._execute_tool(task, tc)
                        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

                return AgentResult(success=False, error="Max fix iterations reached", iterations=MAX_ITERATIONS // 2)

        except asyncio.TimeoutError:
            return AgentResult(success=False, error="Fix timeout", iterations=0)

    async def _rebase_and_merge(self, task: AgentTask) -> Dict:
        """Merge to main using the MergeAgent."""
        import logging
        logger = logging.getLogger(__name__)

        task_ctx = task.task_context or {}
        task_id = task_ctx.get("task_id", task.task_id)
        description = task_ctx.get("description", f"Task {task_id}")

        logger.info(f"[TaskAgent] Requesting merge for {task.branch} via MergeAgent")

        # Get the shared MergeAgent singleton
        merge_agent = await self._get_merge_agent()

        # Get tech_stack from task_ctx
        tech_stack = task_ctx.get("tech_stack", "nodejs-api")

        # Use the MergeAgent for the complete merge workflow
        # Pass file lists to enable fast-path optimization for new-file-only tasks
        merge_result = await merge_agent.request_merge(
            project_id=task.project_id,
            branch=task.branch,
            task_id=task_id,
            task_description=description,
            tech_stack=tech_stack,
            files_created=self._files_created,
            files_modified=self._files_modified
        )

        if merge_result.ok:
            logger.info(f"[TaskAgent] MergeAgent successfully merged {task.branch}")
            return {
                "ok": True,
                "commit": merge_result.commit_sha,
                "conflicts_resolved": merge_result.conflicts_resolved
            }
        else:
            logger.warning(f"[TaskAgent] MergeAgent failed to merge {task.branch}: {merge_result.error}")
            return {
                "ok": False,
                "error": merge_result.error
            }
