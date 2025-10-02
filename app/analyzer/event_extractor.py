"""Event Extraction Analyzer

Extracts domain events from task decomposition trees.
Events represent things that happen in the system - user actions,
system responses, state changes, and integration points.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from app.models import Task
from app.analyzer.llm_client import LLMClient


class EventType(str, Enum):
    """Types of events in the system"""
    USER_ACTION = "user_action"        # User initiates something
    SYSTEM_EVENT = "system_event"      # System responds/reacts
    INTEGRATION = "integration"        # External system interaction
    STATE_CHANGE = "state_change"      # Entity state transition


@dataclass
class DomainEvent:
    """Represents a domain event extracted from tasks"""
    name: str                          # e.g., "UserRegistered", "EmailSent"
    event_type: EventType
    description: str
    source_task_id: str               # Which task this came from
    actor: Optional[str] = None       # Who/what triggers it (User, System, External)
    affected_entity: Optional[str] = None  # What entity is affected
    triggers: List[str] = None        # What events this triggers
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.triggers is None:
            self.triggers = []
        if self.metadata is None:
            self.metadata = {}


class EventExtractor:
    """Extracts domain events from task trees"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def extract_events(self, task_tree: List[Task]) -> List[DomainEvent]:
        """
        Extract all domain events from a task tree.

        Args:
            task_tree: Complete task tree (root + all descendants)

        Returns:
            List of extracted domain events
        """
        # Collect all atomic tasks (leaf nodes with implementation details)
        atomic_tasks = [t for t in task_tree if t.is_atomic and t.implementation_details]

        if not atomic_tasks:
            return []

        # Build context about the overall system
        root_task = next((t for t in task_tree if t.parent_id is None), None)
        system_context = {
            "project_description": root_task.description if root_task else "",
            "total_tasks": len(task_tree),
            "atomic_tasks": len(atomic_tasks)
        }

        # Extract events from atomic tasks
        all_events = []
        for task in atomic_tasks:
            events = await self._extract_events_from_task(task, system_context)
            all_events.extend(events)

        # Deduplicate similar events
        deduplicated = self._deduplicate_events(all_events)

        # Identify event triggers/chains
        enriched = self._identify_event_chains(deduplicated)

        return enriched

    async def _extract_events_from_task(
        self,
        task: Task,
        context: Dict[str, Any]
    ) -> List[DomainEvent]:
        """Extract events from a single atomic task"""

        prompt = f"""Analyze this task and extract all domain events (things that happen in the system).

Project Context: {context['project_description']}

Task: {task.description}

Implementation Details:
{task.implementation_details}

For each event, identify:
1. Event name (PastTense format like "UserRegistered", "EmailSent", "PaymentProcessed")
2. Event type (user_action, system_event, integration, state_change)
3. Actor (who/what triggers it: User, System, or specific external service)
4. Affected entity (what domain object is affected: User, Order, Payment, etc.)
5. Brief description

Format as JSON array:
[
  {{
    "name": "UserRegistered",
    "event_type": "user_action",
    "actor": "User",
    "affected_entity": "User",
    "description": "User completes registration form and submits"
  }},
  {{
    "name": "EmailVerificationSent",
    "event_type": "system_event",
    "actor": "System",
    "affected_entity": "User",
    "description": "System sends verification email to user"
  }}
]

Extract ALL events - don't skip intermediate steps."""

        try:
            response = await self.llm.chat_completion([
                {"role": "user", "content": prompt}
            ])

            # Extract content from response
            import json
            if isinstance(response, dict) and "choices" in response:
                # Standard OpenAI/Cerebras API response format
                content = response["choices"][0]["message"]["content"]
                print(f"[EventExtractor] Raw content: {content[:500]}...")
                events_data = self.llm._parse_json(content)
            elif isinstance(response, dict):
                # Already parsed dict
                events_data = response if isinstance(response, list) else [response]
            else:
                # String response
                events_data = json.loads(response.strip())

            # Ensure we have a list
            if not isinstance(events_data, list):
                events_data = [events_data]

            # Debug: Print what we got
            print(f"[EventExtractor] Parsed {len(events_data)} events")
            print(f"[EventExtractor] First event keys: {list(events_data[0].keys()) if events_data else 'None'}")

            # Convert to DomainEvent objects
            events = []
            for event_data in events_data:
                event = DomainEvent(
                    name=event_data["name"],
                    event_type=EventType(event_data["event_type"]),
                    description=event_data["description"],
                    source_task_id=task.id,
                    actor=event_data.get("actor"),
                    affected_entity=event_data.get("affected_entity"),
                    metadata={
                        "task_description": task.description,
                        "confidence": "high"
                    }
                )
                events.append(event)

            return events

        except Exception as e:
            import traceback
            print(f"Error extracting events from task {task.id}: {e}")
            traceback.print_exc()
            return []

    def _deduplicate_events(self, events: List[DomainEvent]) -> List[DomainEvent]:
        """Remove duplicate events based on name and type"""
        seen = {}
        deduplicated = []

        for event in events:
            key = (event.name, event.event_type)
            if key not in seen:
                seen[key] = event
                deduplicated.append(event)
            else:
                # Merge metadata from duplicate
                existing = seen[key]
                existing.metadata.setdefault("source_tasks", []).append(event.source_task_id)

        return deduplicated

    def _identify_event_chains(self, events: List[DomainEvent]) -> List[DomainEvent]:
        """Identify which events trigger other events"""

        # Simple heuristic: system_events often follow user_actions
        # Integration events often follow system_events
        # This can be enhanced with LLM analysis

        for i, event in enumerate(events):
            if event.event_type == EventType.USER_ACTION:
                # Look for system events that might be triggered
                for other in events[i+1:]:
                    if other.event_type == EventType.SYSTEM_EVENT:
                        if other.affected_entity == event.affected_entity:
                            event.triggers.append(other.name)

        return events
