"""Unified Domain Analyzer

Single LLM call that extracts ALL domain analysis:
- Events
- State Machines
- Commands/Queries (CQRS)
- Database Schema

This replaces 4 separate LLM calls with 1 comprehensive analysis.
"""

from typing import List, Dict, Any
from app.models import Task
from app.analyzer.llm_client import LLMClient
from app.analyzer.event_extractor import DomainEvent, EventType
from app.analyzer.state_machine_detector import StateMachine, StateTransition, TransitionType
from app.analyzer.cqrs_detector import Command, Query, CQRSAnalysis
from app.analyzer.schema_generator import Entity, Field, SchemaAnalysis


class UnifiedDomainAnalyzer:
    """Single-pass domain analysis that extracts everything at once"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def analyze_domain(self, task_tree: List[Task]) -> Dict[str, Any]:
        """
        Perform complete domain analysis, batching if needed.

        Args:
            task_tree: Complete task tree (root + all descendants)

        Returns:
            Dictionary with events, state_machines, cqrs_analysis, and schema
        """
        # Collect all atomic tasks
        atomic_tasks = [t for t in task_tree if t.is_atomic and t.implementation_details]

        if not atomic_tasks:
            return {
                "events": [],
                "commands": [],
                "read_models": [],
                "user_interactions": [],
                "automations": []
            }

        # Build context
        root_task = next((t for t in task_tree if t.parent_id is None), None)

        # Batch tasks if we have too many (to avoid token limits)
        batch_size = 20  # Process 20 tasks at a time
        batches = []
        for i in range(0, len(atomic_tasks), batch_size):
            batch = atomic_tasks[i:i + batch_size]
            task_descriptions = []
            for task in batch:
                task_descriptions.append({
                    "description": task.description,
                    "implementation": task.implementation_details[:500] if task.implementation_details else ""
                })
            batches.append(task_descriptions)

        # Process each batch and combine results
        all_events = []
        all_commands = []
        all_read_models = []
        all_user_interactions = []
        all_automations = []

        for batch_idx, task_descriptions in enumerate(batches):
            print(f"[UnifiedDomainAnalyzer] Processing batch {batch_idx + 1}/{len(batches)} ({len(task_descriptions)} tasks)")

            batch_result = await self._analyze_batch(root_task, task_descriptions, len(atomic_tasks))

            all_events.extend(batch_result.get("events", []))
            all_commands.extend(batch_result.get("commands", []))
            all_read_models.extend(batch_result.get("read_models", []))
            all_user_interactions.extend(batch_result.get("user_interactions", []))
            all_automations.extend(batch_result.get("automations", []))

        # Deduplicate by name (events are DomainEvent objects, others are dicts)
        events = self._deduplicate_events(all_events)
        commands = self._deduplicate_by_name(all_commands)
        read_models = self._deduplicate_by_name(all_read_models)
        user_interactions = self._deduplicate_user_interactions(all_user_interactions)
        automations = self._deduplicate_by_name(all_automations)

        return {
            "events": events,
            "commands": commands,
            "read_models": read_models,
            "user_interactions": user_interactions,
            "automations": automations
        }

    async def _analyze_batch(self, root_task, task_descriptions: list, total_tasks: int) -> Dict[str, Any]:
        """Analyze a single batch of tasks."""

        prompt = f"""Analyze this software project for event modeling.

Project: {root_task.description if root_task else ""}

Note: This is analyzing {len(task_descriptions)} of {total_tasks} total tasks.

Atomic Tasks ({len(task_descriptions)}):
{task_descriptions}

Extract the following for event modeling:

1. EVENTS - Things that happen in the system:
   - name (PastTense: "UserRegistered", "OrderPlaced", "GameStarted", "PieceSpawned")
   - event_type (user_action, system_event, integration, state_change)
   - description
   - actor (User, System, ExternalService)
   - affected_entity (User, Order, etc.)

   IMPORTANT: Include both explicit events mentioned in tasks AND implicit lifecycle events:
   - Initialization/startup events (GameStarted, SessionInitialized, etc.)
   - Entity creation events (PieceSpawned, UserCreated, OrderInitiated, etc.)
   - Termination events (GameEnded, SessionClosed, etc.)
   - State transition events that enable the system to function

2. COMMANDS - User-initiated actions that trigger events:
   - name (imperative: "RegisterUser", "PlaceOrder")
   - description
   - input_data (required fields)
   - triggers_events (event names)

3. READ MODELS - Data views users need to see:
   - name (what they're viewing: "UserProfile", "OrderHistory")
   - description
   - data_fields (what data is shown)

4. USER INTERACTIONS - How users interact with the system:
   - action (what they do: "Click submit button", "Enter email")
   - triggers_command (which command it triggers)
   - viewed_read_model (which read model they're viewing when they perform this action, e.g., "RegistrationForm", "LoginPage")

5. AUTOMATIONS - System-triggered processes:
   - name (what happens: "Send welcome email", "Process payment")
   - trigger_event (what event triggers it)
   - result_events (what events it produces)

Format as JSON:
{{
  "events": [
    {{"name": "UserRegistered", "event_type": "user_action", "description": "User completes registration", "actor": "User", "affected_entity": "User"}}
  ],
  "commands": [
    {{"name": "RegisterUser", "description": "Create new user account", "input_data": ["email", "password"], "triggers_events": ["UserRegistered"]}}
  ],
  "read_models": [
    {{"name": "UserProfile", "description": "User's profile information", "data_fields": ["name", "email", "avatar"]}}
  ],
  "user_interactions": [
    {{"action": "Submit registration form", "triggers_command": "RegisterUser", "viewed_read_model": "RegistrationForm"}}
  ],
  "automations": [
    {{"name": "Send welcome email", "trigger_event": "UserRegistered", "result_events": ["WelcomeEmailSent"]}}
  ]
}}

Be comprehensive but concise.
"""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8000  # Increase to handle larger responses
            )

            # Extract and parse response
            import json
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                try:
                    data = self.llm._parse_json(content)
                except json.JSONDecodeError as e:
                    # Try to extract just the JSON object/array from the content
                    print(f"[UnifiedDomainAnalyzer] JSON parse error: {e}")
                    print(f"[UnifiedDomainAnalyzer] Attempting to extract JSON from response...")

                    # Try to find a JSON object or array
                    import re
                    # Look for JSON object
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                        except:
                            # If still fails, return empty analysis
                            print(f"[UnifiedDomainAnalyzer] Failed to parse JSON, returning empty analysis")
                            data = {"events": [], "state_machines": [], "commands": [], "queries": [], "schema": {}}
                    else:
                        data = {"events": [], "state_machines": [], "commands": [], "queries": [], "schema": {}}
            elif isinstance(response, dict):
                data = response
            else:
                data = json.loads(response.strip())

            # Parse results
            events = self._parse_events(data.get("events", []))
            commands = data.get("commands", [])
            read_models = data.get("read_models", [])
            user_interactions = data.get("user_interactions", [])
            automations = data.get("automations", [])

            return {
                "events": events,
                "commands": commands,
                "read_models": read_models,
                "user_interactions": user_interactions,
                "automations": automations
            }

        except Exception as e:
            import traceback
            print(f"Error in unified domain analysis: {e}")
            traceback.print_exc()
            return {
                "events": [],
                "commands": [],
                "read_models": [],
                "user_interactions": [],
                "automations": []
            }

    def _parse_events(self, events_data: List[Dict]) -> List[DomainEvent]:
        """Parse events from response"""
        events = []
        for event_data in events_data:
            try:
                # Source task ID will be unknown for batched analysis
                source_task_id = "batch_analysis"

                event = DomainEvent(
                    name=event_data["name"],
                    event_type=EventType(event_data["event_type"]),
                    description=event_data["description"],
                    source_task_id=source_task_id,
                    actor=event_data.get("actor"),
                    affected_entity=event_data.get("affected_entity"),
                    triggers=[],
                    metadata={}
                )
                events.append(event)
            except Exception as e:
                print(f"Error parsing event: {e}")
                continue
        return events

    def _deduplicate_events(self, events: List[DomainEvent]) -> List[DomainEvent]:
        """Deduplicate DomainEvent objects by name, keeping first occurrence."""
        seen = set()
        result = []
        for event in events:
            if event.name and event.name not in seen:
                seen.add(event.name)
                result.append(event)
        return result

    def _deduplicate_by_name(self, items: List[Dict]) -> List[Dict]:
        """Deduplicate dict items by name, keeping first occurrence."""
        seen = set()
        result = []
        for item in items:
            name = item.get("name")
            if name and name not in seen:
                seen.add(name)
                result.append(item)
        return result

    def _deduplicate_user_interactions(self, interactions: List[Dict]) -> List[Dict]:
        """Deduplicate user interactions by (action, triggers_command) tuple."""
        seen = set()
        result = []
        for interaction in interactions:
            action = interaction.get("action")
            triggers_command = interaction.get("triggers_command")
            key = (action, triggers_command)
            if key and key not in seen:
                seen.add(key)
                result.append(interaction)
        return result

