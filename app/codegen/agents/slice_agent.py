"""
Slice Agent

A unified agent that handles the complete TDD cycle for a single slice:
1. Register with Contex to get relevant file context
2. Write tests based on slice specification
3. Write implementation code
4. Run tests via runner-service
5. Fix failures until tests pass
6. Merge to main (rebase first)

This replaces the separate TestAgent, CodeAgent, and FixAgent.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.codegen.agents.base import AgentTask, AgentResult, MAX_ITERATIONS, AGENT_TIMEOUT_SECONDS
from app.codegen.agents.tools import WORKSPACE_TOOLS
from app.codegen.agents.merge_agent import MergeAgent, MergeAgentConfig
from app.codegen.tech_stacks import get_tech_stack
from app.services.context_engine_client import ContextEngineClient


# Slice agent system prompt - handles full TDD cycle
SLICE_AGENT_SYSTEM_PROMPT = """You are a TDD developer implementing a single feature slice.

Your task is to implement a complete feature following Test-Driven Development:
1. Write comprehensive tests based on the specification
2. Write minimal code to make tests pass
3. Tests will be run automatically - if they fail, you'll receive error details to fix

You will receive:
- Slice specification with requirements and acceptance criteria
- List of relevant existing files (already fetched for you)
- Tech stack information

WORKFLOW:
1. Review the slice spec and acceptance criteria carefully
2. Review the relevant files provided to understand existing patterns
3. Write tests in the appropriate test file (tests/{slice-name}.test.ts or tests/test_{slice_name}.py)
4. Write implementation code following existing patterns
5. Call done() - tests will run automatically

CRITICAL RULES:
- You have all relevant file contents provided - don't waste iterations searching
- Follow existing code patterns exactly
- Write MINIMAL code to satisfy the spec
- Focus on the acceptance criteria (Given/When/Then scenarios)
- Call done() when implementation is complete

If tests fail after you call done(), you'll receive the error details and can fix them.
"""


@dataclass
class SliceAgentConfig:
    """Configuration for the slice agent."""
    workspace_url: str
    runner_url: str
    llm_model: str = "llama-3.3-70b"
    max_fix_attempts: int = 3


class SliceAgent:
    """
    Agent that handles the complete TDD cycle for a slice.

    Integrates with Contex for semantic file discovery and
    handles test → code → run → fix loop internally.
    """

    def __init__(
        self,
        config: SliceAgentConfig,
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
        Execute the full TDD cycle for a slice.

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

        slice_spec = task.slice_spec or {}
        slice_id = slice_spec.get("slice_id", task.task_id)

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
                summary=f"Slice {slice_id} complete: tests passing, merged to main",
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
        if not self.contex:
            return

        slice_spec = task.slice_spec or {}

        # Build semantic needs based on slice type
        needs = self._build_semantic_needs(slice_spec)

        try:
            # Register with Contex
            agent_id = f"slice-agent-{task.task_id}"
            registration = await self.contex.register_agent(
                agent_id=agent_id,
                project_id=task.project_id,
                data_needs=needs
            )

            # Query for relevant files
            query = self._build_file_query(slice_spec)
            results = await self.contex.query(
                project_id=task.project_id,
                query=query,
                limit=20
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

    def _build_semantic_needs(self, slice_spec: Dict) -> List[str]:
        """Build semantic needs list based on slice type."""
        needs = [
            "existing code patterns and conventions",
            "test file patterns and examples",
        ]

        slice_type = slice_spec.get("type", "state_change")

        if slice_type == "state_change":
            command = slice_spec.get("command", "")
            events = slice_spec.get("events", [])
            needs.extend([
                f"code related to {command} command",
                f"event handling for {', '.join(events)}",
                "command handlers and routes",
            ])
        elif slice_type == "state_view":
            read_model = slice_spec.get("read_model", "")
            needs.extend([
                f"code related to {read_model} queries",
                "read model implementations",
            ])
        elif slice_type == "automation":
            automation = slice_spec.get("automation_name", "")
            trigger = slice_spec.get("trigger_event", "")
            needs.extend([
                f"automation code for {automation}",
                f"event handlers for {trigger}",
            ])

        return needs

    def _build_file_query(self, slice_spec: Dict) -> str:
        """Build a semantic query for relevant files."""
        slice_type = slice_spec.get("type", "state_change")

        if slice_type == "state_change":
            command = slice_spec.get("command", "Unknown")
            return f"files related to {command} command handler, routes, and tests"
        elif slice_type == "state_view":
            read_model = slice_spec.get("read_model", "Unknown")
            return f"files related to {read_model} query handler and tests"
        elif slice_type == "automation":
            automation = slice_spec.get("automation_name", "Unknown")
            return f"files related to {automation} automation and event handlers"
        else:
            return "handler files, route files, and test files"

    async def _fetch_file_contents(self, task: AgentTask, paths: List[str]) -> None:
        """Fetch file contents from workspace service."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            for path in paths[:10]:  # Limit to 10 files
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
            {"role": "system", "content": SLICE_AGENT_SYSTEM_PROMPT},
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
        slice_spec = task.slice_spec or {}

        prompt = f"""Implement this feature slice using TDD.

## Slice Specification

Type: {slice_spec.get('type', 'state_change')}
"""

        if slice_spec.get('type') == 'state_change':
            prompt += f"Command: {slice_spec.get('command', 'Unknown')}\n"
            prompt += f"Events: {', '.join(slice_spec.get('events', []))}\n"
        elif slice_spec.get('type') == 'state_view':
            prompt += f"Read Model: {slice_spec.get('read_model', 'Unknown')}\n"
        elif slice_spec.get('type') == 'automation':
            prompt += f"Automation: {slice_spec.get('automation_name', 'Unknown')}\n"
            prompt += f"Trigger: {slice_spec.get('trigger_event', 'Unknown')}\n"

        # Add acceptance criteria
        gwt_scenarios = slice_spec.get('gwt_scenarios', [])
        if gwt_scenarios:
            prompt += "\n## Acceptance Criteria\n\n"
            for i, scenario in enumerate(gwt_scenarios, 1):
                prompt += f"### Scenario {i}\n"
                if scenario.get('given'):
                    prompt += f"**Given** {scenario['given']}\n"
                if scenario.get('when'):
                    prompt += f"**When** {scenario['when']}\n"
                if scenario.get('then'):
                    prompt += f"**Then** {scenario['then']}\n"
                prompt += "\n"

        # Add pre-fetched file context
        if self._relevant_files:
            prompt += "\n## Relevant Existing Files\n\n"
            prompt += "These files were identified as relevant. Use them to understand existing patterns:\n\n"
            for path, content in self._relevant_files.items():
                prompt += f"### {path}\n```\n{content[:2000]}\n```\n\n"

        # Get tech stack conventions
        tech_stack_name = slice_spec.get('tech_stack', 'nodejs-api')
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

1. Write tests first (TDD)
2. Implement minimal code to pass tests
3. Follow the conventions above
4. Call done() when complete
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
                        # Handle both "passed"/"failed" and "completed" status values
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
        tech_stack = (task.slice_spec or {}).get("tech_stack", "nodejs-api")
        commands = {
            "nodejs-api": "npm test",
            "python-api": "pytest",
        }
        return commands.get(tech_stack, "npm test")

    async def _fix_failures(self, task: AgentTask, test_result: Dict) -> AgentResult:
        """Run agent loop to fix test failures."""
        start_time = datetime.now(timezone.utc)

        error_details = test_result.get("error", "Unknown error")
        failures = test_result.get("failures", [])

        fix_prompt = f"""The tests failed. Please fix the implementation.

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
            {"role": "system", "content": SLICE_AGENT_SYSTEM_PROMPT},
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

    async def _rebase_and_merge(self, task: AgentTask, max_retries: int = 3) -> Dict:
        """Merge to main using the MergeAgent.

        The MergeAgent handles:
        - Serialized merge queue (one at a time, no race conditions)
        - Updating branch from main (detecting conflicts)
        - LLM-powered conflict resolution
        - Post-merge test verification
        - Automatic fix attempts if tests fail

        Args:
            task: The agent task containing project_id, branch, and slice_spec
            max_retries: Unused (MergeAgent handles retries internally)
        """
        import logging
        logger = logging.getLogger(__name__)

        slice_spec = task.slice_spec or {}
        slice_id = slice_spec.get("slice_id", task.task_id)
        slice_description = slice_spec.get("description", "")

        # Build description from slice spec if not provided
        if not slice_description:
            if slice_spec.get("type") == "state_change":
                slice_description = f"Implement {slice_spec.get('command', 'Unknown')} command"
            elif slice_spec.get("type") == "state_view":
                slice_description = f"Implement {slice_spec.get('read_model', 'Unknown')} read model"
            elif slice_spec.get("type") == "automation":
                slice_description = f"Implement {slice_spec.get('automation_name', 'Unknown')} automation"
            else:
                slice_description = f"Implement slice {slice_id}"

        logger.info(f"[SliceAgent] Requesting merge for {task.branch} via MergeAgent")

        # Get the shared MergeAgent singleton
        merge_agent = await self._get_merge_agent()

        # Get tech_stack from slice_spec
        tech_stack = (task.slice_spec or {}).get("tech_stack", "nodejs-api")

        # Use the MergeAgent for the complete merge workflow
        merge_result = await merge_agent.request_merge(
            project_id=task.project_id,
            branch=task.branch,
            slice_id=slice_id,
            slice_description=slice_description,
            tech_stack=tech_stack
        )

        if merge_result.ok:
            logger.info(f"[SliceAgent] MergeAgent successfully merged {task.branch}")
            return {
                "ok": True,
                "commit": merge_result.commit_sha,
                "conflicts_resolved": merge_result.conflicts_resolved
            }
        else:
            logger.warning(f"[SliceAgent] MergeAgent failed to merge {task.branch}: {merge_result.error}")
            return {
                "ok": False,
                "error": merge_result.error
            }
