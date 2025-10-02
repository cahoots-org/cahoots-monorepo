"""State Machine Detection Analyzer

Analyzes domain events to detect state machines and their transitions.
Identifies entities that go through distinct states and the events that trigger transitions.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from app.analyzer.event_extractor import DomainEvent, EventType
from app.analyzer.llm_client import LLMClient


class TransitionType(str, Enum):
    """Types of state transitions"""
    USER_TRIGGERED = "user_triggered"      # User action causes transition
    SYSTEM_TRIGGERED = "system_triggered"  # System event causes transition
    AUTOMATIC = "automatic"                # Automatic/timed transition
    CONDITIONAL = "conditional"            # Condition-based transition


@dataclass
class StateTransition:
    """Represents a state transition"""
    from_state: str
    to_state: str
    trigger_event: str
    transition_type: TransitionType
    condition: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateMachine:
    """Represents a detected state machine"""
    entity: str                            # Entity that has states (e.g., "TetrisPiece", "Game")
    states: Set[str]                       # All possible states
    initial_state: Optional[str] = None    # Starting state
    final_states: Set[str] = field(default_factory=set)  # Terminal states
    transitions: List[StateTransition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateMachineDetector:
    """Detects state machines from domain events"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def detect_state_machines(self, events: List[DomainEvent]) -> List[StateMachine]:
        """
        Detect all state machines from domain events.

        Args:
            events: List of domain events

        Returns:
            List of detected state machines
        """
        if not events:
            return []

        # Group events by affected entity
        events_by_entity = self._group_by_entity(events)

        # Detect state machines for each entity
        state_machines = []
        for entity, entity_events in events_by_entity.items():
            # Only analyze entities with state changes
            has_state_changes = any(
                e.event_type == EventType.STATE_CHANGE
                for e in entity_events
            )
            if has_state_changes:
                machine = await self._detect_entity_state_machine(entity, entity_events)
                if machine:
                    state_machines.append(machine)

        return state_machines

    def _group_by_entity(self, events: List[DomainEvent]) -> Dict[str, List[DomainEvent]]:
        """Group events by affected entity"""
        grouped = {}
        for event in events:
            if event.affected_entity:
                entity = event.affected_entity
                if entity not in grouped:
                    grouped[entity] = []
                grouped[entity].append(event)
        return grouped

    async def _detect_entity_state_machine(
        self,
        entity: str,
        events: List[DomainEvent]
    ) -> Optional[StateMachine]:
        """Detect state machine for a specific entity"""

        # Build event summary
        event_summary = []
        for e in events:
            event_summary.append({
                "name": e.name,
                "type": e.event_type.value,
                "description": e.description,
                "actor": e.actor
            })

        prompt = f"""Analyze these events for the entity "{entity}" and identify if it follows a state machine pattern.

Events:
{event_summary}

If this entity has distinct states and transitions between them, provide:

1. All possible states the entity can be in
2. Initial state (if identifiable)
3. Final/terminal states (if any)
4. State transitions with:
   - From state
   - To state
   - Triggering event name
   - Transition type (user_triggered, system_triggered, automatic, conditional)
   - Condition (if applicable)

Format as JSON:
{{
  "has_state_machine": true/false,
  "states": ["state1", "state2", ...],
  "initial_state": "state1",
  "final_states": ["state3"],
  "transitions": [
    {{
      "from_state": "state1",
      "to_state": "state2",
      "trigger_event": "EventName",
      "transition_type": "user_triggered",
      "condition": "optional condition description"
    }}
  ]
}}

If no clear state machine pattern exists, set has_state_machine to false.
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

            if not data.get("has_state_machine", False):
                return None

            # Build StateMachine object
            transitions = []
            for t in data.get("transitions", []):
                transition = StateTransition(
                    from_state=t["from_state"],
                    to_state=t["to_state"],
                    trigger_event=t["trigger_event"],
                    transition_type=TransitionType(t["transition_type"]),
                    condition=t.get("condition")
                )
                transitions.append(transition)

            machine = StateMachine(
                entity=entity,
                states=set(data.get("states", [])),
                initial_state=data.get("initial_state"),
                final_states=set(data.get("final_states", [])),
                transitions=transitions,
                metadata={
                    "event_count": len(events),
                    "state_change_events": len([e for e in events if e.event_type == EventType.STATE_CHANGE])
                }
            )

            return machine

        except Exception as e:
            import traceback
            print(f"Error detecting state machine for {entity}: {e}")
            traceback.print_exc()
            return None

    def generate_mermaid_diagram(self, state_machine: StateMachine) -> str:
        """Generate a Mermaid state diagram"""
        lines = ["stateDiagram-v2"]

        # Add initial state
        if state_machine.initial_state:
            lines.append(f"    [*] --> {state_machine.initial_state}")

        # Add transitions
        for transition in state_machine.transitions:
            label = transition.trigger_event
            if transition.condition:
                label += f" [{transition.condition}]"
            lines.append(f"    {transition.from_state} --> {transition.to_state}: {label}")

        # Add final states
        for final_state in state_machine.final_states:
            lines.append(f"    {final_state} --> [*]")

        return "\n".join(lines)
