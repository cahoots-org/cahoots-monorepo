"""
Base Agent Class

Provides the foundation for all code generation agents:
- Tool-calling loop with LLM
- Workspace service communication
- Completion detection
- Error handling and timeouts
"""

import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

import httpx

from app.codegen.agents.tools import WORKSPACE_TOOLS


# Configuration constants
MAX_ITERATIONS = 25  # Max tool calls per agent run
AGENT_TIMEOUT_SECONDS = 300  # 5 minutes per agent
LLM_MAX_TOKENS = 4000
LLM_TEMPERATURE = 0.1


@dataclass
class AgentTask:
    """Task input for an agent."""
    task_id: str
    task_type: str  # "scaffold", "generate_tests", "generate_code", "fix", "integrate", "merge"
    project_id: str

    # Context - task_context contains task-specific data like description, implementation_details
    task_context: Optional[Dict] = None
    test_file_path: Optional[str] = None
    test_error: Optional[Dict] = None
    tech_stack: str = "nodejs-api"

    # Pre-fetched file context (reduces agent iterations)
    # Dict of {file_path: file_content} for relevant files
    file_context: Optional[Dict[str, str]] = None

    # Workspace
    repo_url: str = ""
    branch: str = "main"


@dataclass
class AgentResult:
    """Result from an agent run."""
    success: bool
    summary: Optional[str] = None
    error: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)
    iterations: int = 0
    duration_seconds: float = 0.0


@dataclass
class ToolCall:
    """Represents a single tool call from the LLM."""
    id: str
    name: str
    arguments: str  # JSON string


class CodeGenerationAgent(ABC):
    """
    Base class for code generation agents.

    Agents receive tasks and use tools to interact with the workspace,
    similar to how a human developer would work.
    """

    def __init__(
        self,
        workspace_url: str,
        llm_client: Any = None,  # LLMClient from app.analyzer.llm_client
        llm_model: str = "llama-3.3-70b",  # Model name for creating LLM client
    ):
        self.workspace_url = workspace_url.rstrip("/")
        self.llm_model = llm_model
        self._llm_client = llm_client
        self.system_prompt = self._get_system_prompt()

        # Track files modified during this run
        self._files_created: List[str] = []
        self._files_modified: List[str] = []
        self._commits: List[str] = []

    @property
    def llm(self):
        """Get or create the LLM client."""
        if self._llm_client is None:
            # Lazy initialization of LLM client
            import os
            from app.analyzer.llm_client import CerebrasLLMClient

            api_key = os.getenv("CEREBRAS_API_KEY")
            if api_key:
                self._llm_client = CerebrasLLMClient(
                    api_key=api_key,
                    model=os.getenv("CEREBRAS_MODEL", self.llm_model)
                )
            else:
                # Fallback to mock client for testing
                from app.analyzer import MockLLMClient
                self._llm_client = MockLLMClient()

        return self._llm_client

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Return the system prompt for this agent type."""
        pass

    @abstractmethod
    def _format_task(self, task: AgentTask) -> str:
        """Format the task into a user prompt for the LLM."""
        pass

    async def run(self, task: AgentTask) -> AgentResult:
        """
        Execute the agent loop until completion or max iterations.

        The agent:
        1. Sends task to LLM with available tools
        2. Executes any tool calls from the LLM
        3. Sends tool results back to LLM
        4. Repeats until LLM calls done() or max iterations reached
        """
        start_time = datetime.now(timezone.utc)
        self._files_created = []
        self._files_modified = []
        self._commits = []

        # Set task context for tool execution
        self.project_id = task.project_id
        self.branch = task.branch

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._format_task(task)}
        ]

        try:
            async with asyncio.timeout(AGENT_TIMEOUT_SECONDS):
                for iteration in range(MAX_ITERATIONS):
                    # Call LLM with tools
                    response = await self._call_llm(messages)

                    # Debug: log response structure
                    import logging
                    logger = logging.getLogger(__name__)
                    content = self._get_response_content(response)
                    logger.info(f"[Agent] Iteration {iteration + 1}: content length={len(content)}, has_choices={'choices' in response}")

                    # Check for tool calls
                    tool_calls = self._parse_tool_calls(response)
                    if tool_calls:
                        logger.info(f"[Agent] Iteration {iteration + 1}: found {len(tool_calls)} tool calls: {[tc.name for tc in tool_calls]}")
                    else:
                        logger.info(f"[Agent] Iteration {iteration + 1}: found 0 tool calls")

                    if not tool_calls:
                        # No tool calls - check if this looks like completion
                        content = self._get_response_content(response)
                        logger.info(f"[Agent] No tool calls. Content preview: {content[:200] if content else '(empty)'}...")

                        # Check for various completion indicators
                        content_lower = content.lower()
                        is_complete = any(phrase in content_lower for phrase in [
                            "complete", "finished", "done", "all files created",
                            "task is complete", "implementation complete", "implemented",
                            "created the", "summary", "the tests cover", "test suite"
                        ])

                        if is_complete:
                            logger.info(f"[Agent] Detected completion phrase in content")
                            return AgentResult(
                                success=True,
                                summary=content or "Task completed",
                                files_created=self._files_created,
                                files_modified=self._files_modified,
                                commits=self._commits,
                                iterations=iteration + 1,
                                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
                            )
                        # Continue conversation
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": "You must use the tools to complete this task. If you are done, call the done() tool with a summary. Do not just output text."})
                        continue

                    # Append assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": self._get_response_content(response),
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.name, "arguments": tc.arguments}
                            }
                            for tc in tool_calls
                        ]
                    })

                    # Execute each tool and append results
                    for tool_call in tool_calls:
                        # Check for completion
                        if tool_call.name == "done":
                            args = json.loads(tool_call.arguments)
                            return AgentResult(
                                success=True,
                                summary=args.get("summary", "Task completed"),
                                files_created=self._files_created,
                                files_modified=self._files_modified,
                                commits=self._commits,
                                iterations=iteration + 1,
                                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds()
                            )

                        # Execute tool
                        result = await self._execute_tool(tool_call)

                        # Add iteration awareness for urgent completion
                        if iteration >= MAX_ITERATIONS - 5:
                            remaining = MAX_ITERATIONS - iteration - 1
                            result += f"\n\n⚠️ WARNING: Only {remaining} iterations remaining! You MUST call done() soon or your work will be lost."
                        elif iteration >= MAX_ITERATIONS - 10:
                            remaining = MAX_ITERATIONS - iteration - 1
                            result += f"\n\n📢 Note: {remaining} iterations remaining. Start wrapping up."

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })

                # Max iterations reached
                return AgentResult(
                    success=False,
                    error="Max iterations reached - agent may be stuck in a loop",
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
                files_created=self._files_created,
                files_modified=self._files_modified,
                commits=self._commits,
                iterations=0,
                duration_seconds=AGENT_TIMEOUT_SECONDS
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

    async def _call_llm(self, messages: List[Dict]) -> Dict:
        """Call the LLM with tool support."""
        # Use the existing LLM client's chat_completion method
        # This needs to support tool calling
        try:
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
                tools=WORKSPACE_TOOLS
            )
            return response
        except Exception as e:
            # If tool calling not supported, try without tools
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS
            )
            return {"content": response.get("content", str(response))}

    def _get_response_content(self, response: Dict) -> str:
        """Extract content from LLM response (handles OpenAI format)."""
        if "choices" in response:
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "") or ""
        return response.get("content", "") or ""

    def _parse_tool_calls(self, response: Dict) -> List[ToolCall]:
        """Parse tool calls from LLM response."""
        tool_calls = []

        # Extract message from OpenAI format response
        message = response
        if "choices" in response:
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})

        # Handle different response formats
        raw_calls = message.get("tool_calls", [])
        if not raw_calls:
            # Check for function_call format (older API)
            if "function_call" in message:
                fc = message["function_call"]
                tool_calls.append(ToolCall(
                    id="call_0",
                    name=fc.get("name", ""),
                    arguments=fc.get("arguments", "{}")
                ))
            return tool_calls

        for tc in raw_calls:
            if isinstance(tc, dict):
                func = tc.get("function", {})
                tool_calls.append(ToolCall(
                    id=tc.get("id", f"call_{len(tool_calls)}"),
                    name=func.get("name", ""),
                    arguments=func.get("arguments", "{}")
                ))

        return tool_calls

    async def _execute_tool(self, tool_call: ToolCall) -> str:
        """Execute a tool call by calling the Workspace Service API."""
        try:
            args = json.loads(tool_call.arguments)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments: {tool_call.arguments}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if tool_call.name == "read_file":
                    response = await client.post(
                        f"{self.workspace_url}/workspace/{self.project_id}/files/read",
                        params={"branch": self.branch},
                        json={"path": args.get("path", "")}
                    )
                    if response.status_code == 200:
                        return response.json().get("content", "")
                    elif response.status_code == 404:
                        return f"File not found: {args.get('path')}. If you need to create this file, use write_file instead. If you're looking for an existing file, try list_files to see what exists."
                    else:
                        return f"Error: {response.json().get('detail', 'Unknown error')}"

                elif tool_call.name == "write_file":
                    path = args.get("path", "")
                    response = await client.post(
                        f"{self.workspace_url}/workspace/{self.project_id}/files/write",
                        params={"branch": self.branch},
                        json={"path": path, "content": args.get("content", "")}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        commit = data.get("commit", "")
                        if commit:
                            self._commits.append(commit)
                        if path not in self._files_created and path not in self._files_modified:
                            self._files_created.append(path)
                        return f"File written: {path} (commit: {commit})"
                    else:
                        return f"Error writing file: {response.json().get('detail', 'Unknown error')}"

                elif tool_call.name == "edit_file":
                    path = args.get("path", "")
                    response = await client.post(
                        f"{self.workspace_url}/workspace/{self.project_id}/files/edit",
                        params={"branch": self.branch},
                        json={
                            "path": path,
                            "old": args.get("old_text", ""),
                            "new": args.get("new_text", "")
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        commit = data.get("commit", "")
                        if commit:
                            self._commits.append(commit)
                        if path not in self._files_modified and path not in self._files_created:
                            self._files_modified.append(path)
                        return f"File edited: {path} (commit: {commit})"
                    elif response.status_code == 400:
                        return f"Error: Could not find text to replace in {path}"
                    else:
                        return f"Error editing file: {response.json().get('detail', 'Unknown error')}"

                elif tool_call.name == "list_files":
                    response = await client.post(
                        f"{self.workspace_url}/workspace/{self.project_id}/files/list",
                        params={"branch": self.branch},
                        json={
                            "path": args.get("path", "."),
                            "pattern": args.get("pattern", "*")
                        }
                    )
                    if response.status_code == 200:
                        files = response.json().get("files", [])
                        if not files:
                            return f"No files found in {args.get('path', '.')}. This may be a new directory - you can create files here directly using write_file."
                        return f"Files in {args.get('path', '.')}:\n" + "\n".join(f"  - {f}" for f in files)
                    elif response.status_code == 404:
                        return f"Directory {args.get('path', '.')} does not exist. You can create files in it directly using write_file - parent directories will be created automatically."
                    else:
                        return f"Error listing files: {response.json().get('detail', 'Unknown error')}"

                elif tool_call.name == "grep":
                    response = await client.post(
                        f"{self.workspace_url}/workspace/{self.project_id}/files/grep",
                        params={"branch": self.branch},
                        json={
                            "pattern": args.get("pattern", ""),
                            "path": args.get("path", ".")
                        }
                    )
                    if response.status_code == 200:
                        matches = response.json().get("matches", [])
                        if not matches:
                            return f"No matches found for '{args.get('pattern')}' in {args.get('path', '.')}. The pattern may not exist yet - proceed with creating your files."
                        result = f"Found {len(matches)} matches:\n"
                        for match in matches[:20]:  # Limit display
                            result += f"  {match['file']}:{match['line']}: {match['content']}\n"
                        if len(matches) > 20:
                            result += f"  ... and {len(matches) - 20} more matches"
                        return result
                    else:
                        return f"Error searching: {response.json().get('detail', 'Unknown error')}"

                elif tool_call.name == "done":
                    # Handled in run() loop
                    return f"Task complete: {args.get('summary', '')}"

                else:
                    return f"Error: Unknown tool: {tool_call.name}"

            except httpx.RequestError as e:
                return f"Error: Failed to connect to workspace service: {e}"
