"""Command/Query Identification (CQRS Pattern Detection)

Analyzes domain events to identify Commands (write operations) and Queries (read operations).
Helps identify CQRS boundaries and separation opportunities.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from app.analyzer.event_extractor import DomainEvent, EventType
from app.analyzer.llm_client import LLMClient


class OperationType(str, Enum):
    """Type of operation"""
    COMMAND = "command"  # Write/mutate operation
    QUERY = "query"      # Read operation
    HYBRID = "hybrid"    # Both read and write


@dataclass
class Command:
    """Represents a command (write operation)"""
    name: str
    description: str
    input_data: List[str] = field(default_factory=list)  # Required inputs
    triggers_events: List[str] = field(default_factory=list)  # Events triggered
    affects_entities: List[str] = field(default_factory=list)  # Entities modified
    validation_rules: List[str] = field(default_factory=list)  # Business rules
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Query:
    """Represents a query (read operation)"""
    name: str
    description: str
    input_params: List[str] = field(default_factory=list)  # Query parameters
    returns_data: str = ""  # What data is returned
    reads_from: List[str] = field(default_factory=list)  # Entities/tables read
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CQRSAnalysis:
    """Complete CQRS analysis"""
    commands: List[Command] = field(default_factory=list)
    queries: List[Query] = field(default_factory=list)
    command_query_pairs: List[Dict[str, Any]] = field(default_factory=list)  # Related command/query pairs
    cqrs_boundaries: List[str] = field(default_factory=list)  # Suggested CQRS boundaries
    metadata: Dict[str, Any] = field(default_factory=dict)


class CQRSDetector:
    """Detects Commands and Queries from domain events"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def analyze_cqrs(self, events: List[DomainEvent]) -> CQRSAnalysis:
        """
        Analyze events to identify Commands and Queries.

        Args:
            events: List of domain events

        Returns:
            CQRS analysis with commands and queries
        """
        if not events:
            return CQRSAnalysis()

        # Separate events by type
        user_actions = [e for e in events if e.event_type == EventType.USER_ACTION]
        system_events = [e for e in events if e.event_type == EventType.SYSTEM_EVENT]
        integrations = [e for e in events if e.event_type == EventType.INTEGRATION]

        # Build event summary
        event_summary = {
            "user_actions": [{"name": e.name, "description": e.description, "actor": e.actor} for e in user_actions],
            "system_events": [{"name": e.name, "description": e.description} for e in system_events],
            "integrations": [{"name": e.name, "description": e.description} for e in integrations]
        }

        prompt = f"""Analyze these domain events and identify Commands (write operations) and Queries (read operations).

Events:
{event_summary}

For each Command (operations that change state), provide:
- Name (imperative form: "CreateUser", "UpdateOrder", "DeleteItem")
- Description
- Input data required
- Events triggered
- Entities affected
- Validation rules

For each Query (operations that read data), provide:
- Name (question form: "GetUser", "ListOrders", "FindItem")
- Description
- Input parameters
- What data is returned
- Entities/tables read from

Also identify:
- Related command/query pairs (e.g., CreateUser command + GetUser query)
- Suggested CQRS boundaries (logical groupings of commands/queries)

Format as JSON:
{{
  "commands": [
    {{
      "name": "CreateUser",
      "description": "Creates a new user account",
      "input_data": ["email", "password", "name"],
      "triggers_events": ["UserCreated", "EmailVerificationSent"],
      "affects_entities": ["User"],
      "validation_rules": ["Email must be unique", "Password must meet strength requirements"]
    }}
  ],
  "queries": [
    {{
      "name": "GetUser",
      "description": "Retrieves user details by ID",
      "input_params": ["user_id"],
      "returns_data": "User object with profile information",
      "reads_from": ["User"]
    }}
  ],
  "command_query_pairs": [
    {{
      "command": "CreateUser",
      "query": "GetUser",
      "relationship": "Command creates what query retrieves"
    }}
  ],
  "cqrs_boundaries": [
    "User Management: CreateUser, UpdateUser, DeleteUser, GetUser, ListUsers",
    "Game Management: StartGame, PauseGame, EndGame, GetGameState"
  ]
}}
"""

        try:
            response = await self.llm.chat_completion([
                {"role": "user", "content": prompt}
            ])

            # Extract content from response
            import json
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                data = self.llm._parse_json(content)
            elif isinstance(response, dict):
                data = response
            else:
                data = json.loads(response.strip())

            # Build Commands
            commands = []
            for cmd_data in data.get("commands", []):
                command = Command(
                    name=cmd_data["name"],
                    description=cmd_data["description"],
                    input_data=cmd_data.get("input_data", []),
                    triggers_events=cmd_data.get("triggers_events", []),
                    affects_entities=cmd_data.get("affects_entities", []),
                    validation_rules=cmd_data.get("validation_rules", [])
                )
                commands.append(command)

            # Build Queries
            queries = []
            for query_data in data.get("queries", []):
                query = Query(
                    name=query_data["name"],
                    description=query_data["description"],
                    input_params=query_data.get("input_params", []),
                    returns_data=query_data.get("returns_data", ""),
                    reads_from=query_data.get("reads_from", [])
                )
                queries.append(query)

            analysis = CQRSAnalysis(
                commands=commands,
                queries=queries,
                command_query_pairs=data.get("command_query_pairs", []),
                cqrs_boundaries=data.get("cqrs_boundaries", []),
                metadata={
                    "total_events": len(events),
                    "commands_identified": len(commands),
                    "queries_identified": len(queries)
                }
            )

            return analysis

        except Exception as e:
            import traceback
            print(f"Error analyzing CQRS patterns: {e}")
            traceback.print_exc()
            return CQRSAnalysis()

    def generate_api_skeleton(self, analysis: CQRSAnalysis) -> str:
        """Generate API skeleton from CQRS analysis"""
        lines = ["# API Endpoints (generated from CQRS analysis)", ""]

        # Commands (POST/PUT/DELETE)
        if analysis.commands:
            lines.append("## Commands (Write Operations)")
            for cmd in analysis.commands:
                method = "POST"
                if "Update" in cmd.name:
                    method = "PUT"
                elif "Delete" in cmd.name:
                    method = "DELETE"

                endpoint = f"/{cmd.name.lower()}"
                lines.append(f"{method} {endpoint}")
                lines.append(f"  Description: {cmd.description}")
                if cmd.input_data:
                    lines.append(f"  Input: {', '.join(cmd.input_data)}")
                if cmd.triggers_events:
                    lines.append(f"  Triggers: {', '.join(cmd.triggers_events)}")
                lines.append("")

        # Queries (GET)
        if analysis.queries:
            lines.append("## Queries (Read Operations)")
            for query in analysis.queries:
                endpoint = f"/{query.name.lower()}"
                lines.append(f"GET {endpoint}")
                lines.append(f"  Description: {query.description}")
                if query.input_params:
                    lines.append(f"  Params: {', '.join(query.input_params)}")
                lines.append(f"  Returns: {query.returns_data}")
                lines.append("")

        return "\n".join(lines)
