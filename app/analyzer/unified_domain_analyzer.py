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

            # Try up to 10 times with validation feedback
            batch_result = None
            validation_feedback = None
            max_retries = 10

            for retry in range(max_retries):
                batch_result = await self._analyze_batch(root_task, task_descriptions, len(atomic_tasks), validation_feedback)

                # Validate the batch result
                from app.analyzer.event_model_validator import EventModelValidator
                validator = EventModelValidator()
                is_valid, validation_issues = validator.validate(batch_result)

                # If valid, accept it
                if is_valid:
                    print(f"[UnifiedDomainAnalyzer] Batch validation passed")
                    break

                # If not valid, try to fix errors with separate LLM call
                errors = [issue for issue in validation_issues if issue.severity == 'error']

                if errors and retry < max_retries - 1:
                    print(f"[UnifiedDomainAnalyzer] Batch validation failed with {len(errors)} errors (attempt {retry + 1}/{max_retries})")
                    print(f"[UnifiedDomainAnalyzer] Attempting to fix errors with separate LLM call...")

                    batch_result = await self._fix_validation_errors(batch_result, validation_issues)

                    # Re-validate after fixes
                    is_valid, validation_issues = validator.validate(batch_result)
                    if is_valid:
                        print(f"[UnifiedDomainAnalyzer] Fixes successful, validation passed")
                        break
                    else:
                        print(f"[UnifiedDomainAnalyzer] Fixes incomplete, {len([i for i in validation_issues if i.severity == 'error'])} errors remain")
                elif retry == max_retries - 1:
                    print(f"[UnifiedDomainAnalyzer] Batch validation failed after {max_retries} attempts, proceeding anyway")
                    break

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

        combined_result = {
            "events": events,
            "commands": commands,
            "read_models": read_models,
            "user_interactions": user_interactions,
            "automations": automations
        }

        # If we had multiple batches, make a final consolidation pass to ensure completeness
        if len(batches) > 1:
            print(f"[UnifiedDomainAnalyzer] Making final consolidation pass to ensure completeness")
            combined_result = await self._consolidate_event_model(root_task, combined_result, atomic_tasks)

        # Final validation with fix attempts
        from app.analyzer.event_model_validator import EventModelValidator
        validator = EventModelValidator()

        for retry in range(10):
            is_valid, validation_issues = validator.validate(combined_result)

            if is_valid:
                print(f"[UnifiedDomainAnalyzer] Final validation passed")
                break

            errors = [issue for issue in validation_issues if issue.severity == 'error']

            if errors and retry < 9:
                print(f"[UnifiedDomainAnalyzer] Final validation failed with {len(errors)} errors (attempt {retry + 1}/10)")
                combined_result = await self._fix_validation_errors(combined_result, validation_issues)
            else:
                print(f"[UnifiedDomainAnalyzer] Proceeding with {len(errors)} validation errors")
                break

        # Add swimlanes and chapters for Event Modeling structure
        print(f"[UnifiedDomainAnalyzer] Detecting swimlanes and chapters...")
        combined_result = await self._detect_swimlanes_and_chapters(root_task, combined_result)

        return combined_result

    async def _analyze_batch(self, root_task, task_descriptions: list, total_tasks: int, validation_feedback: str = None) -> Dict[str, Any]:
        """Analyze a single batch of tasks.

        Args:
            root_task: Root task for context
            task_descriptions: List of atomic tasks to analyze
            total_tasks: Total number of tasks
            validation_feedback: Optional feedback from previous validation attempt
        """

        prompt = f"""Analyze this software project using Event Modeling methodology.

Project: {root_task.description if root_task else ""}

Note: Analyzing {len(task_descriptions)} of {total_tasks} total tasks.

Atomic Tasks:
{task_descriptions}

IMPORTANT - Event Modeling Principles:
1. Events are FACTS (past tense) - what happened in the system
2. Commands are INTENTIONS (imperative) - what users/systems want to do
3. Read Models are QUERIES - data views (only create when displaying/querying data)
4. Automations are BACKGROUND PROCESSES - triggered automatically
5. Focus on BEHAVIOR not implementation

Extract the following components:

1. EVENTS - Facts that happened (past tense):
   - name: PastTense format ("UserRegistered", "ItemAdded", "OrderPlaced")
   - event_type: user_action, system_event, integration, or state_change
   - description: What happened
   - actor: Who/what triggered it (User, System, ExternalService, etc.)
   - affected_entity: What was affected (User, Order, Cart, etc.)

   Include lifecycle events:
   - Creation: "CartCreated", "SessionStarted", "UserRegistered"
   - Changes: "ItemAdded", "PriceChanged", "StatusUpdated"
   - Completion: "OrderSubmitted", "SessionEnded", "GameFinished"

2. COMMANDS - User/system intentions (imperative):
   - name: Imperative format ("AddItem", "RegisterUser", "SubmitOrder")
   - description: What the command does
   - input_data: Required input fields (list of field names)
   - triggers_events: Events produced (list of event names)

   Each command represents a State Change slice (Command → Event(s))

3. READ MODELS - Data views (only when querying/displaying):
   - name: What data is shown ("CartItems", "UserProfile", "OrderHistory")
   - description: Purpose of this view
   - data_fields: Fields displayed (list)

   CRITICAL: Only create read models when:
   - Displaying data to users
   - Querying current state for validation
   - Feeding data to automations
   - NOT for every command/event

   Each read model represents a State View slice (Events → Read Model)

4. USER INTERACTIONS - How users trigger commands:
   - action: User action ("Click submit", "Enter email", "Select item")
   - triggers_command: Command name
   - viewed_read_model: Read model shown (if any)

5. AUTOMATIONS - Background processes (Event → Process → Event):
   - name: What the automation does
   - trigger_event: Event that triggers it
   - result_events: Events it produces

   Each automation represents an Automation slice (Event → Read Model → Processor → Command → Event)

REQUIRED OUTPUT FORMAT - You MUST include ALL 5 sections:

Return JSON with exactly these keys (all are required, use empty arrays if none found):
{{
  "events": [...],
  "commands": [...],
  "read_models": [...],
  "user_interactions": [...],
  "automations": [...]
}}

Example for a shopping cart:
{{
  "events": [
    {{"name": "ItemAdded", "event_type": "user_action", "description": "Item added to cart", "actor": "User", "affected_entity": "Cart"}},
    {{"name": "CartCreated", "event_type": "system_event", "description": "Shopping cart created", "actor": "System", "affected_entity": "Cart"}}
  ],
  "commands": [
    {{"name": "AddItem", "description": "Add item to shopping cart", "input_data": ["productId", "quantity"], "triggers_events": ["CartCreated", "ItemAdded"]}},
    {{"name": "RemoveItem", "description": "Remove item from cart", "input_data": ["itemId"], "triggers_events": ["ItemRemoved"]}}
  ],
  "read_models": [
    {{"name": "CartItems", "description": "Display items in cart", "data_fields": ["items", "totalPrice", "quantity"]}}
  ],
  "user_interactions": [
    {{"action": "Click 'Add to Cart' button", "triggers_command": "AddItem", "viewed_read_model": "ProductDetails"}},
    {{"action": "Click 'Remove' button", "triggers_command": "RemoveItem", "viewed_read_model": "CartItems"}}
  ],
  "automations": [
    {{"name": "Publish cart to order system", "trigger_event": "CartSubmitted", "result_events": ["ExternalCartPublished"]}}
  ]
}}

CRITICAL: For the tasks provided, identify actual commands users/system execute. Every user action needs a command.
For Tetris example:
- Commands: StartGame, MoveLeft, MoveRight, RotatePiece, DropPiece, PauseGame
- Events: GameStarted, PieceMoved, PieceRotated, PieceDropped, LineCleared, GameOver
- Read Models: GameBoard, Score, NextPiece
- User Interactions: Press arrow key left → MoveLeft, Press space → DropPiece
- Automations: LineCleared → CheckGameOver → GameOver

Guidelines:
- Be comprehensive: include ALL commands for user actions
- Past tense for events, imperative for commands
- Only create read models when displaying/querying data
- Every user action should have a corresponding command

CRITICAL: Your response must be ONLY valid JSON. No explanations, no markdown, no code blocks, no extra text.
Just the raw JSON object starting with {{ and ending with }}.
"""

        # Add validation feedback if provided
        if validation_feedback:
            prompt += f"""

⚠️ CRITICAL - YOUR PREVIOUS RESPONSE HAD VALIDATION ERRORS ⚠️

The following errors MUST be fixed in your next response:

{validation_feedback}

MANDATORY FIXES:
1. If a command references an event that doesn't exist, you MUST either:
   - Add that event to the events list, OR
   - Change the command to reference an existing event
2. Event names in "triggers_events" must EXACTLY match event names in the "events" list
3. All events must be past tense (e.g., "GamePaused", not "PauseGame")
4. All commands must be imperative (e.g., "PauseGame", not "GamePaused")

DO NOT submit a response that fails these validations. Fix the issues now.
"""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32000  # Llama 3.3 70B supports up to 128K context
            )

            # Extract and parse response
            import json
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]

                # Try to extract JSON using a robust approach
                import re
                data = None

                # Strategy 1: Try direct JSON parse (if LLM followed instructions)
                try:
                    data = json.loads(content.strip())
                    print(f"[UnifiedDomainAnalyzer] Successfully parsed JSON directly")
                except json.JSONDecodeError:
                    pass

                # Strategy 2: Look for JSON in code blocks (```json ... ```)
                if data is None:
                    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
                    if code_block_match:
                        try:
                            data = json.loads(code_block_match.group(1))
                            print(f"[UnifiedDomainAnalyzer] Successfully extracted JSON from code block")
                        except json.JSONDecodeError:
                            pass

                # Strategy 3: Find the first complete JSON object
                if data is None:
                    # Try to find a JSON object with balanced braces
                    start_idx = content.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        in_string = False
                        escape = False

                        for i in range(start_idx, len(content)):
                            char = content[i]

                            if escape:
                                escape = False
                                continue

                            if char == '\\':
                                escape = True
                                continue

                            if char == '"' and not escape:
                                in_string = not in_string
                                continue

                            if not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_str = content[start_idx:i+1]
                                        try:
                                            data = json.loads(json_str)
                                            print(f"[UnifiedDomainAnalyzer] Successfully extracted JSON using brace matching")
                                            break
                                        except json.JSONDecodeError:
                                            pass

                # If all strategies failed
                if data is None:
                    print(f"[UnifiedDomainAnalyzer] Failed to parse JSON, returning empty analysis")
                    print(f"[UnifiedDomainAnalyzer] Response preview: {content[:500]}")
                    data = {"events": [], "commands": [], "read_models": [], "user_interactions": [], "automations": []}
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

            print(f"[UnifiedDomainAnalyzer] LLM returned: {len(events)} events, {len(commands)} commands, {len(read_models)} read models")
            if len(commands) == 0:
                print(f"[UnifiedDomainAnalyzer] WARNING: No commands extracted! Check LLM response.")
                print(f"[UnifiedDomainAnalyzer] Raw data keys: {list(data.keys())}")

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

    async def _fix_validation_errors(self, analysis: Dict[str, Any], validation_issues: List) -> Dict[str, Any]:
        """Make a separate LLM call to fix validation errors."""
        import json

        # Build error descriptions with specific fix options
        errors = [issue for issue in validation_issues if issue.severity == 'error']

        error_descriptions = []
        for issue in errors:
            error_descriptions.append(f"\nERROR: {issue.message}")

            # Provide specific fix options based on error type
            if 'missing_event' in issue.details:
                missing_event = issue.details['missing_event']
                command = issue.details.get('command', '')
                error_descriptions.append(f"Fix by choosing ONE option:")
                error_descriptions.append(f'1. Add event to events list: {{"name": "{missing_event}", "event_type": "system_event", "description": "...", "actor": "System", "affected_entity": "Game"}}')
                error_descriptions.append(f'2. Change command "{command}" to reference an existing event instead')

            elif 'missing_command' in issue.details:
                missing_command = issue.details['missing_command']
                error_descriptions.append(f"Fix by adding command: {missing_command}")

            elif 'missing_read_model' in issue.details:
                missing_read_model = issue.details['missing_read_model']
                interaction = issue.details.get('interaction', '')
                available_read_models = issue.details.get('available_read_models', [])
                error_descriptions.append(f"Fix user interaction '{interaction}' by choosing ONE option:")
                error_descriptions.append(f'1. Add read model to read_models list: {{"name": "{missing_read_model}", "description": "...", "data_fields": ["..."]}}')
                if available_read_models:
                    error_descriptions.append(f'2. Change viewed_read_model to use an existing read model: {available_read_models[:3]}')
                error_descriptions.append(f'3. Set viewed_read_model to null if no read model is needed for this interaction')

            elif issue.category == 'orphaned':
                event_name = issue.details.get('event', '')
                error_descriptions.append(f"Fix event '{event_name}' by choosing ONE option:")
                error_descriptions.append(f'1. Add a command that triggers it: {{"name": "SomeCommand", "triggers_events": ["{event_name}"]}}')
                error_descriptions.append(f'2. Add an automation that produces it: {{"name": "...", "trigger_event": "...", "result_events": ["{event_name}"]}}')
                error_descriptions.append(f'3. Change event_type to "integration" if it\'s an external event')
                error_descriptions.append(f'4. Remove the event if it\'s not needed')

        errors_text = "\n".join(error_descriptions)

        # Convert analysis to JSON-serializable format
        serializable_analysis = {
            "events": [
                {
                    "name": e.name if hasattr(e, 'name') else e.get('name'),
                    "event_type": e.event_type.value if hasattr(e, 'event_type') else e.get('event_type'),
                    "description": e.description if hasattr(e, 'description') else e.get('description'),
                    "actor": e.actor if hasattr(e, 'actor') else e.get('actor'),
                    "affected_entity": e.affected_entity if hasattr(e, 'affected_entity') else e.get('affected_entity')
                }
                for e in analysis.get('events', [])
            ],
            "commands": analysis.get('commands', []),
            "read_models": analysis.get('read_models', []),
            "user_interactions": analysis.get('user_interactions', []),
            "automations": analysis.get('automations', [])
        }

        prompt = f"""You are fixing validation errors in an event model.

CURRENT EVENT MODEL (with errors):
{json.dumps(serializable_analysis, indent=2)}

VALIDATION ERRORS THAT MUST BE FIXED:
{errors_text}

YOUR TASK:
Return the COMPLETE corrected event model as JSON with ALL sections (events, commands, read_models, user_interactions, automations).
Make the minimum changes necessary to fix the errors.
Preserve all existing correct data.

Return ONLY the JSON, no explanation."""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=64000  # Llama 3.3 70B supports up to 128K context
            )

            # Extract and parse response
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                finish_reason = response["choices"][0].get("finish_reason", "unknown")

                if finish_reason == "length":
                    print("[UnifiedDomainAnalyzer] WARNING: Fix response was truncated due to max_tokens limit")
                    print("[UnifiedDomainAnalyzer] Consider increasing max_tokens or simplifying the event model")

                # Extract JSON using same robust method as _analyze_batch
                import re
                data = None

                # Strategy 1: Try direct JSON parse
                try:
                    data = json.loads(content.strip())
                    print("[UnifiedDomainAnalyzer] Successfully parsed fix JSON directly")
                except json.JSONDecodeError:
                    pass

                # Strategy 2: Look for JSON in code blocks
                if data is None:
                    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
                    if code_block_match:
                        try:
                            data = json.loads(code_block_match.group(1))
                            print("[UnifiedDomainAnalyzer] Successfully extracted fix JSON from code block")
                        except json.JSONDecodeError:
                            pass

                # Strategy 3: Find the first complete JSON object with brace matching
                if data is None:
                    start_idx = content.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        in_string = False
                        escape = False

                        for i in range(start_idx, len(content)):
                            char = content[i]

                            if escape:
                                escape = False
                                continue

                            if char == '\\':
                                escape = True
                                continue

                            if char == '"' and not escape:
                                in_string = not in_string
                                continue

                            if not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_str = content[start_idx:i+1]
                                        try:
                                            data = json.loads(json_str)
                                            print("[UnifiedDomainAnalyzer] Successfully extracted fix JSON using brace matching")
                                            break
                                        except json.JSONDecodeError as e:
                                            print(f"[UnifiedDomainAnalyzer] Failed to parse fix response: {e}")
                                            # Print the problematic area
                                            if hasattr(e, 'pos'):
                                                start = max(0, e.pos - 200)
                                                end = min(len(json_str), e.pos + 200)
                                                print(f"[UnifiedDomainAnalyzer] JSON context around error: ...{json_str[start:end]}...")

                if data is None:
                    print("[UnifiedDomainAnalyzer] No valid JSON found in fix response, keeping original")
                    return analysis

                fixed_data = data
            else:
                print("[UnifiedDomainAnalyzer] Unexpected fix response format, keeping original")
                return analysis

            # Parse events (they need to be DomainEvent objects)
            fixed_data["events"] = self._parse_events(fixed_data.get("events", []))

            print(f"[UnifiedDomainAnalyzer] Applied fixes: {len(fixed_data.get('events', []))} events, {len(fixed_data.get('commands', []))} commands")
            return fixed_data

        except Exception as e:
            print(f"[UnifiedDomainAnalyzer] Error fixing validation errors: {e}")
            return analysis

    async def _consolidate_event_model(self, root_task, combined_model: Dict[str, Any], atomic_tasks: List) -> Dict[str, Any]:
        """
        Make a final LLM call to consolidate and complete the event model from multiple batches.
        This ensures the model is comprehensive and coherent.
        """
        try:
            # Convert events to serializable format
            serializable_events = [
                {
                    "name": e.name if hasattr(e, 'name') else e.get('name'),
                    "event_type": e.event_type.value if hasattr(e, 'event_type') else e.get('event_type'),
                    "description": e.description if hasattr(e, 'description') else e.get('description'),
                    "actor": e.actor if hasattr(e, 'actor') else e.get('actor'),
                    "affected_entity": e.affected_entity if hasattr(e, 'affected_entity') else e.get('affected_entity')
                }
                for e in combined_model.get('events', [])
            ]

            current_model_summary = f"""
Current Event Model (from {len(atomic_tasks)} tasks):
- Events: {len(combined_model.get('events', []))} - {[e['name'] for e in serializable_events[:10]]}{'...' if len(serializable_events) > 10 else ''}
- Commands: {len(combined_model.get('commands', []))} - {[c['name'] for c in combined_model.get('commands', [])[:10]]}{'...' if len(combined_model.get('commands', [])) > 10 else ''}
- Read Models: {len(combined_model.get('read_models', []))} - {[r['name'] for r in combined_model.get('read_models', [])[:10]]}{'...' if len(combined_model.get('read_models', [])) > 10 else ''}
- Automations: {len(combined_model.get('automations', []))}
"""

            # Sample of tasks for context (first 10 and last 10)
            task_samples = atomic_tasks[:10] + (atomic_tasks[-10:] if len(atomic_tasks) > 10 else [])
            task_descriptions = "\n".join([f"- {t.description}" for t in task_samples])

            prompt = f"""You are completing and consolidating an Event Model for a software project.

PROJECT: {root_task.description if root_task else ""}

CURRENT MODEL STATUS:
{current_model_summary}

SAMPLE TASKS (showing {len(task_samples)} of {len(atomic_tasks)} total tasks):
{task_descriptions}

YOUR TASK:
Review the current event model and ensure it is COMPLETE and COMPREHENSIVE for all {len(atomic_tasks)} tasks.

The model was generated in batches, so it may be missing:
1. Important events that weren't captured from all task batches
2. Commands needed for complete functionality
3. Read models for displaying system state
4. Automations for background processes
5. User interactions linking UI to commands

INSTRUCTIONS:
1. Keep all existing events, commands, read models that are correct
2. ADD any missing components needed for a complete system
3. Ensure ALL commands reference existing events in triggers_events
4. Ensure ALL automations reference existing events
5. Ensure read models cover key system state queries
6. Use proper naming: Events (past tense), Commands (imperative)

Return the COMPLETE event model as JSON with all 5 required sections.

IMPORTANT: Only include events that are ACTUALLY triggered by commands or automations, or are external (integration type).

Return ONLY valid JSON, no explanation:
{{
  "events": [...],
  "commands": [...],
  "read_models": [...],
  "user_interactions": [...],
  "automations": [...]
}}"""

            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32000,  # Llama 3.3 70B supports up to 128K context
                temperature=0.3
            )

            # Parse response
            import re
            import json

            content = response.get("content", "")
            if isinstance(content, list):
                content = content[0].get("text", "") if content else ""

            # Extract JSON using same robust method as _analyze_batch
            data = None

            # Strategy 1: Try direct JSON parse
            try:
                data = json.loads(content.strip())
                print(f"[UnifiedDomainAnalyzer] Successfully parsed consolidated JSON directly")
            except json.JSONDecodeError:
                pass

            # Strategy 2: Look for JSON in code blocks
            if data is None:
                code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
                if code_block_match:
                    try:
                        data = json.loads(code_block_match.group(1))
                        print(f"[UnifiedDomainAnalyzer] Successfully extracted consolidated JSON from code block")
                    except json.JSONDecodeError:
                        pass

            # Strategy 3: Find the first complete JSON object with brace matching
            if data is None:
                start_idx = content.find('{')
                if start_idx != -1:
                    brace_count = 0
                    in_string = False
                    escape = False

                    for i in range(start_idx, len(content)):
                        char = content[i]

                        if escape:
                            escape = False
                            continue

                        if char == '\\':
                            escape = True
                            continue

                        if char == '"' and not escape:
                            in_string = not in_string
                            continue

                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = content[start_idx:i+1]
                                    try:
                                        data = json.loads(json_str)
                                        print(f"[UnifiedDomainAnalyzer] Successfully extracted consolidated JSON using brace matching")
                                        break
                                    except json.JSONDecodeError:
                                        pass

            if data:
                # Parse events to DomainEvent objects
                data["events"] = self._parse_events(data.get("events", []))
                print(f"[UnifiedDomainAnalyzer] Consolidated model: {len(data.get('events', []))} events, {len(data.get('commands', []))} commands")
                return data
            else:
                print("[UnifiedDomainAnalyzer] Failed to parse consolidation response, keeping original")
                return combined_model

        except Exception as e:
            print(f"[UnifiedDomainAnalyzer] Error consolidating event model: {e}")
            return combined_model

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

    async def _detect_swimlanes_and_chapters(self, root_task, event_model: Dict[str, Any]) -> Dict[str, Any]:
        """Detect swimlanes and chapters using the swimlane_detector module."""
        from app.analyzer.swimlane_detector import detect_swimlanes_and_chapters
        return await detect_swimlanes_and_chapters(self.llm, root_task, event_model)

