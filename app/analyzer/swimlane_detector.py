"""Swimlane and Chapter Detection for Event Models

Organizes event models by business capabilities (swimlanes) and workflows (chapters)
following Event Modeling best practices from the book.
"""

from typing import List, Dict, Any
import json


def _generate_fallback_structure(event_model: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a basic swimlanes/chapters structure when LLM fails.

    This creates a single "Main" swimlane and organizes slices into a single chapter.
    Also generates basic GWT scenarios based on command/read model structure.
    """
    commands = event_model.get('commands', [])
    events = event_model.get('events', [])
    read_models = event_model.get('read_models', [])

    # Create one swimlane with all elements
    event_model['swimlanes'] = [{
        "name": "Main",
        "description": "Primary system functionality",
        "events": [e.name if hasattr(e, 'name') else e.get('name', '') for e in events],
        "commands": [c.get('name', '') for c in commands if isinstance(c, dict)],
        "read_models": [rm.get('name', '') for rm in read_models if isinstance(rm, dict)],
        "automations": []
    }]

    # Create slices from commands with basic GWT scenarios
    slices = []
    for cmd in commands:
        if isinstance(cmd, dict) and cmd.get('name'):
            cmd_name = cmd['name']
            triggered_events = cmd.get('triggers_events', [])

            # Generate basic GWT scenarios from command structure
            gwt_scenarios = []

            # Happy path scenario
            events_str = ', '.join(triggered_events) if triggered_events else f'{cmd_name}Completed'
            gwt_scenarios.append({
                "given": "Valid request data is provided",
                "when": f"{cmd_name} command is executed",
                "then": f"{events_str} event(s) are emitted"
            })

            # Error scenario - check if command has required parameters
            params = cmd.get('parameters', [])
            required_params = [p.get('name') for p in params if isinstance(p, dict) and p.get('required')]
            if required_params:
                gwt_scenarios.append({
                    "given": f"Required parameter(s) {', '.join(required_params[:2])} are missing",
                    "when": f"{cmd_name} command is executed",
                    "then": "Validation error is returned"
                })
            else:
                gwt_scenarios.append({
                    "given": "Invalid or malformed data is provided",
                    "when": f"{cmd_name} command is executed",
                    "then": "Error response is returned"
                })

            slices.append({
                "type": "state_change",
                "command": cmd_name,
                "events": triggered_events,
                "gwt_scenarios": gwt_scenarios
            })

    # Add read model slices with basic GWT scenarios
    for rm in read_models:
        if isinstance(rm, dict) and rm.get('name'):
            rm_name = rm['name']
            source_events = rm.get('data_source', [])

            # Generate basic GWT scenarios for read models
            gwt_scenarios = []

            if source_events:
                gwt_scenarios.append({
                    "given": f"{source_events[0] if source_events else 'Source'} event has occurred",
                    "then": f"{rm_name} displays the updated data"
                })
            else:
                gwt_scenarios.append({
                    "given": "Data exists in the system",
                    "then": f"{rm_name} displays the current state"
                })

            gwt_scenarios.append({
                "given": "No matching data exists",
                "then": f"{rm_name} shows empty state or appropriate message"
            })

            slices.append({
                "type": "state_view",
                "read_model": rm_name,
                "source_events": source_events,
                "gwt_scenarios": gwt_scenarios
            })

    # Create one chapter with all slices
    event_model['chapters'] = [{
        "name": "Core Functionality",
        "description": "Main system workflows",
        "slices": slices
    }]

    print(f"[SwimlaneDetector] Generated fallback: 1 swimlane, 1 chapter with {len(slices)} slices (with GWT scenarios)")
    return event_model


def _extract_swimlanes_from_reasoning(content: str, event_model: Dict[str, Any]) -> Dict[str, Any]:
    """Extract swimlane assignments from model's reasoning output.

    Some models output their reasoning like:
    "1. RegisterUser - Identity"
    "2. CreateAppointment - Scheduling"

    This function parses that into proper swimlane structure.
    """
    import re

    # Look for patterns like "CommandName - Category" or "N. CommandName - Category"
    # Common patterns from reasoning models
    patterns = [
        r'(\w+)\s*[-–—]\s*(\w+(?:\s+\w+)?)',  # "CommandName - Category" or "CommandName - Two Words"
        r'\d+\.\s*(\w+)\s*[-–—]\s*(\w+(?:\s+\w+)?)',  # "1. CommandName - Category"
    ]

    assignments = {}  # command/event -> swimlane name

    for pattern in patterns:
        matches = re.findall(pattern, content)
        for name, swimlane in matches:
            # Normalize swimlane name
            swimlane = swimlane.strip().title()
            if swimlane not in ['We', 'The', 'This', 'That', 'Or', 'And', 'If']:  # Skip common words
                assignments[name] = swimlane

    if not assignments:
        return None

    # Group by swimlane
    swimlanes_dict = {}
    for name, swimlane in assignments.items():
        if swimlane not in swimlanes_dict:
            swimlanes_dict[swimlane] = {
                "name": swimlane,
                "description": f"{swimlane} business capability",
                "events": [],
                "commands": [],
                "read_models": [],
                "automations": []
            }

    # Categorize elements
    commands = {c.get('name'): c for c in event_model.get('commands', []) if isinstance(c, dict) and c.get('name')}
    events = {(e.name if hasattr(e, 'name') else e.get('name', '')): e for e in event_model.get('events', [])}
    read_models = {rm.get('name'): rm for rm in event_model.get('read_models', []) if isinstance(rm, dict) and rm.get('name')}

    for name, swimlane in assignments.items():
        if name in commands:
            swimlanes_dict[swimlane]["commands"].append(name)
        elif name in events:
            swimlanes_dict[swimlane]["events"].append(name)
        elif name in read_models:
            swimlanes_dict[swimlane]["read_models"].append(name)

    # Add any unassigned elements to "Other" swimlane
    assigned_commands = set(name for s in swimlanes_dict.values() for name in s["commands"])
    assigned_events = set(name for s in swimlanes_dict.values() for name in s["events"])
    assigned_read_models = set(name for s in swimlanes_dict.values() for name in s["read_models"])

    unassigned_commands = [c for c in commands.keys() if c not in assigned_commands]
    unassigned_events = [e for e in events.keys() if e not in assigned_events]
    unassigned_read_models = [rm for rm in read_models.keys() if rm not in assigned_read_models]

    if unassigned_commands or unassigned_events or unassigned_read_models:
        if "Other" not in swimlanes_dict:
            swimlanes_dict["Other"] = {
                "name": "Other",
                "description": "Other functionality",
                "events": [],
                "commands": [],
                "read_models": [],
                "automations": []
            }
        swimlanes_dict["Other"]["commands"].extend(unassigned_commands)
        swimlanes_dict["Other"]["events"].extend(unassigned_events)
        swimlanes_dict["Other"]["read_models"].extend(unassigned_read_models)

    swimlanes = list(swimlanes_dict.values())
    if swimlanes:
        return {"swimlanes": swimlanes}

    return None


def _compact_event_model(event_model: Dict[str, Any]) -> str:
    """Create a compact string representation of the event model for prompts."""
    lines = []

    # Events - just names and affected entity
    events = event_model.get('events', [])
    event_names = []
    for e in events:
        name = e.name if hasattr(e, 'name') else e.get('name', '')
        entity = e.affected_entity if hasattr(e, 'affected_entity') else e.get('affected_entity', '')
        if name:
            event_names.append(f"{name}({entity})" if entity else name)
    lines.append(f"EVENTS ({len(event_names)}): {', '.join(event_names)}")

    # Commands - name and triggered events
    commands = event_model.get('commands', [])
    cmd_info = []
    for c in commands:
        if isinstance(c, dict) and c.get('name'):
            triggers = c.get('triggers_events', [])
            cmd_info.append(f"{c['name']}→{','.join(triggers) if triggers else '?'}")
    lines.append(f"COMMANDS ({len(cmd_info)}): {', '.join(cmd_info)}")

    # Read models - just names
    read_models = event_model.get('read_models', [])
    rm_names = [rm.get('name', '') for rm in read_models if isinstance(rm, dict) and rm.get('name')]
    lines.append(f"READ_MODELS ({len(rm_names)}): {', '.join(rm_names)}")

    # Automations
    automations = event_model.get('automations', [])
    auto_names = [a.get('name', '') for a in automations if isinstance(a, dict) and a.get('name')]
    if auto_names:
        lines.append(f"AUTOMATIONS ({len(auto_names)}): {', '.join(auto_names)}")

    return '\n'.join(lines)


async def _detect_swimlanes_only(llm_client, root_task, event_model: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Phase 1: Detect swimlanes (grouping by business capability)."""

    compact_model = _compact_event_model(event_model)

    prompt = f"""Group these event model elements into swimlanes (business capabilities).

PROJECT: {root_task.description if root_task else "Unknown"}

{compact_model}

Return JSON with swimlanes that group related events, commands, and read_models by business domain.
Example: User, Cart, Order, Payment, Inventory, Notification, etc.

Format:
{{"swimlanes": [{{"name": "Name", "description": "What it does", "events": ["Event1"], "commands": ["Cmd1"], "read_models": ["RM1"], "automations": []}}]}}

Rules:
- 3-8 swimlanes typically
- Each element in exactly one swimlane
- Group by affected entity/domain
- Singular nouns for names

Return ONLY valid JSON."""

    try:
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.2
        )

        print(f"[SwimlaneDetector] Phase 1 response type: {type(response)}")
        if isinstance(response, dict):
            print(f"[SwimlaneDetector] Phase 1 response keys: {list(response.keys())}")

        # Handle different response formats
        content = None
        if isinstance(response, dict):
            if "choices" in response:
                print(f"[SwimlaneDetector] Phase 1 choices[0] keys: {list(response['choices'][0].keys())}")
                msg = response["choices"][0].get("message", {})
                print(f"[SwimlaneDetector] Phase 1 message keys: {list(msg.keys()) if isinstance(msg, dict) else 'not a dict'}")
                # Try content first, then reasoning (some models return reasoning instead)
                if isinstance(msg, dict):
                    content = msg.get("content") or msg.get("reasoning") or ""
                    if msg.get("reasoning") and not msg.get("content"):
                        print(f"[SwimlaneDetector] Phase 1 using 'reasoning' field instead of 'content'")
                else:
                    content = ""
            elif "message" in response:
                content = response["message"].get("content", "")
            elif "content" in response:
                content = response["content"]
            else:
                print(f"[SwimlaneDetector] Phase 1 unexpected response keys: {list(response.keys())}")
        elif isinstance(response, str):
            content = response

        if content:
            print(f"[SwimlaneDetector] Phase 1 content length: {len(content)}")

            # Some reasoning models embed JSON in their thought process
            # Look for JSON blocks in the content
            data = _parse_json_response(content)

            # If no direct JSON found, try to find JSON embedded in reasoning text
            if not data or 'swimlanes' not in data:
                # Look for ```json blocks or raw JSON objects
                import re
                json_patterns = [
                    r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
                    r'```\s*([\s\S]*?)\s*```',      # ``` ... ```
                    r'(\{"swimlanes"[\s\S]*?\]\s*\})',  # Direct swimlanes JSON
                ]
                for pattern in json_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        try:
                            parsed = json.loads(match)
                            if 'swimlanes' in parsed:
                                data = parsed
                                print(f"[SwimlaneDetector] Phase 1 found embedded JSON with swimlanes")
                                break
                        except json.JSONDecodeError:
                            continue
                    if data and 'swimlanes' in data:
                        break

            if data and 'swimlanes' in data:
                print(f"[SwimlaneDetector] Phase 1 parsed {len(data['swimlanes'])} swimlanes")
                return data['swimlanes']
            else:
                print(f"[SwimlaneDetector] Phase 1 failed to parse swimlanes from response")
                # Check if response looks like reasoning without final answer
                if content.startswith("We need") or content.startswith("Let me") or "I need to" in content[:200]:
                    print(f"[SwimlaneDetector] Phase 1 model returned reasoning - trying to extract assignments")
                    # Try to extract swimlane assignments from reasoning output
                    # Look for patterns like "CommandName - SwimlaneCategory" or numbered lists
                    data = _extract_swimlanes_from_reasoning(content, event_model)
                    if data and 'swimlanes' in data:
                        print(f"[SwimlaneDetector] Phase 1 extracted {len(data['swimlanes'])} swimlanes from reasoning")
                        return data['swimlanes']
                    print(f"[SwimlaneDetector] Phase 1 could not extract swimlanes from reasoning")
                else:
                    print(f"[SwimlaneDetector] Phase 1 content preview: {content[:500]}")
        else:
            print(f"[SwimlaneDetector] Phase 1 no content extracted from response")

    except Exception as e:
        import traceback
        print(f"[SwimlaneDetector] Phase 1 error: {e}")
        print(f"[SwimlaneDetector] Phase 1 traceback: {traceback.format_exc()}")

    return None


async def _generate_chapters_with_gwt(llm_client, root_task, event_model: Dict[str, Any], swimlanes: List[Dict[str, Any]], user_stories: List[Dict] = None) -> List[Dict[str, Any]]:
    """Phase 2: Generate chapters with GWT scenarios, processing in batches if needed."""

    commands = event_model.get('commands', [])
    read_models = event_model.get('read_models', [])

    # For small event models, process all at once
    if len(commands) + len(read_models) <= 30:
        return await _generate_chapters_batch(llm_client, root_task, commands, read_models, user_stories=user_stories)

    # For large event models, process by swimlane
    all_chapters = []
    for swimlane in swimlanes:
        sw_commands = [c for c in commands if isinstance(c, dict) and c.get('name') in swimlane.get('commands', [])]
        sw_read_models = [rm for rm in read_models if isinstance(rm, dict) and rm.get('name') in swimlane.get('read_models', [])]

        if sw_commands or sw_read_models:
            chapters = await _generate_chapters_batch(
                llm_client, root_task, sw_commands, sw_read_models,
                chapter_prefix=swimlane.get('name', 'Main'),
                user_stories=user_stories
            )
            if chapters:
                all_chapters.extend(chapters)

    return all_chapters if all_chapters else None


async def _generate_chapters_batch(
    llm_client,
    root_task,
    commands: List[Dict],
    read_models: List[Dict],
    chapter_prefix: str = "",
    user_stories: List[Dict] = None
) -> List[Dict[str, Any]]:
    """Generate chapters with GWT for a batch of commands/read models."""

    # Create detailed command info with full parameters for rich GWT generation
    cmd_info = []
    for c in commands:
        if isinstance(c, dict) and c.get('name'):
            name = c['name']
            desc = c.get('description', '')
            triggers = c.get('triggers_events', [])
            params = c.get('parameters', [])
            param_details = []
            for p in params:
                if isinstance(p, dict):
                    p_name = p.get('name', '')
                    p_type = p.get('type', 'string')
                    p_required = '(required)' if p.get('required') else '(optional)'
                    param_details.append(f"{p_name}: {p_type} {p_required}")
            cmd_info.append(f"""- {name}:
    Description: {desc}
    Triggers: {', '.join(triggers) if triggers else 'events'}
    Parameters: {', '.join(param_details) if param_details else 'none'}""")

    rm_info = []
    for rm in read_models:
        if isinstance(rm, dict) and rm.get('name'):
            name = rm['name']
            desc = rm.get('description', '')
            fields = rm.get('fields', [])
            field_names = [f.get('name', '') for f in fields if isinstance(f, dict)][:5]
            rm_info.append(f"- {name}: {desc}. Fields: {', '.join(field_names) if field_names else 'various'}")

    # Include user stories if available for acceptance criteria context
    story_context = ""
    if user_stories:
        story_snippets = []
        for story in user_stories[:5]:  # Limit to avoid token overflow
            if isinstance(story, dict):
                actor = story.get('actor', 'User')
                action = story.get('action', '')
                criteria = story.get('acceptance_criteria', [])[:2]
                if action:
                    story_snippets.append(f"- As {actor}, {action}")
                    for c in criteria:
                        story_snippets.append(f"  • {c}")
        if story_snippets:
            story_context = f"""
USER STORIES & ACCEPTANCE CRITERIA (use these for scenario specifics):
{chr(10).join(story_snippets)}
"""

    prompt = f"""Generate BDD test scenarios (Given-When-Then) for these commands and read models.

PROJECT: {root_task.description if root_task else "Unknown"}
{story_context}
COMMANDS:
{chr(10).join(cmd_info) if cmd_info else "None"}

READ MODELS:
{chr(10).join(rm_info) if rm_info else "None"}

CRITICAL REQUIREMENTS FOR HIGH-QUALITY SCENARIOS:

1. **NAMED ACTORS with specific identifiers**:
   - BAD: "Given a user wants to..."
   - GOOD: "Given Client 'acme-corp' (clientId: 'client-123') owns project 'website-redesign'"

2. **CONCRETE ENTITY IDs and VALUES**:
   - BAD: "When the command is executed"
   - GOOD: "When AcceptBid is executed with bidId='bid-456', projectId='proj-789'"

3. **SPECIFIC EVENT PAYLOADS in Then clause**:
   - BAD: "Then events are emitted"
   - GOOD: "Then BidAccepted is emitted with contractId='contract-001', amount=$2000"

4. **MULTIPLE SCENARIO TYPES per command** (aim for 3-5 scenarios each):
   a. Happy path with full specifics
   b. Authorization failure (wrong user tries action)
   c. Business rule violation (e.g., insufficient funds, invalid state)
   d. Edge case (concurrent access, expiration, boundary values)

5. **READ MODEL SCENARIOS must show specific data**:
   - BAD: "Then the read model displays data"
   - GOOD: "Then EscrowBalance shows totalHeld=$5000, released=$1500, pending=$3500"

EXAMPLE SCENARIOS FOR REFERENCE:

For AcceptBid command:
{{
  "given": "Client 'acme-corp' (clientId: 'c-123') has project 'website-redesign' (projectId: 'p-456') with budget $5000. Freelancer 'jane-dev' (freelancerId: 'f-789') submitted bid 'bid-001' for $4500",
  "when": "Client executes AcceptBid with bidId='bid-001', clientId='c-123'",
  "then": "BidAccepted is emitted with contractId='contract-new', acceptedAmount=$4500. EscrowFundsHeld is emitted with amount=$4500, contractId='contract-new'. All other bids on project 'p-456' are marked rejected"
}}

For authorization failure:
{{
  "given": "Freelancer 'jane-dev' (freelancerId: 'f-789') submitted bid 'bid-001' on project owned by 'acme-corp'",
  "when": "Different client 'other-corp' (clientId: 'c-999') attempts AcceptBid with bidId='bid-001'",
  "then": "BidAcceptanceFailed is emitted with reason='UnauthorizedAccess'. No escrow funds are held. Bid remains in 'pending' status"
}}

For a read model:
{{
  "given": "EscrowFundsHeld event occurred with amount=$5000 for contract 'contract-123'. MilestoneReleased events occurred for $1500 total",
  "then": "EscrowBalanceDetails for contract 'contract-123' shows totalHeld=$5000, released=$1500, remaining=$3500, with breakdown by milestone"
}}

Return JSON with chapters containing slices:

{{"chapters": [
  {{"name": "Chapter Name", "description": "...", "slices": [
    {{"type": "state_change", "command": "CmdName", "events": ["Event1"], "gwt_scenarios": [
      {{"given": "detailed precondition with named actors and IDs", "when": "specific action with parameter values", "then": "specific outcome with event payloads"}}
    ]}},
    {{"type": "state_view", "read_model": "RMName", "source_events": ["Event1"], "gwt_scenarios": [
      {{"given": "specific events that occurred with values", "then": "exact data shown with field values"}}
    ]}}
  ]}}
]}}

Return ONLY valid JSON."""

    try:
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
            temperature=0.3
        )

        # Handle different response formats (including reasoning models)
        content = None
        if isinstance(response, dict):
            if "choices" in response:
                msg = response["choices"][0].get("message", {})
                if isinstance(msg, dict):
                    # Try content first, then reasoning (some models return reasoning instead)
                    content = msg.get("content") or msg.get("reasoning") or ""
                    if msg.get("reasoning") and not msg.get("content"):
                        print(f"[SwimlaneDetector] Phase 2 using 'reasoning' field instead of 'content'")
            elif "message" in response:
                content = response["message"].get("content", "")
            elif "content" in response:
                content = response["content"]

        if content:
            # Try to parse JSON from the content
            data = _parse_json_response(content)

            # If no direct JSON found, try to find JSON embedded in reasoning text
            if not data or 'chapters' not in data:
                import re
                json_patterns = [
                    r'```json\s*([\s\S]*?)\s*```',
                    r'```\s*([\s\S]*?)\s*```',
                    r'(\{"chapters"[\s\S]*?\]\s*\})',
                ]
                for pattern in json_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        try:
                            parsed = json.loads(match)
                            if 'chapters' in parsed:
                                data = parsed
                                print(f"[SwimlaneDetector] Phase 2 found embedded JSON with chapters")
                                break
                        except json.JSONDecodeError:
                            continue
                    if data and 'chapters' in data:
                        break

            if data and 'chapters' in data:
                chapters = data['chapters']
                # Add prefix to chapter names if provided
                if chapter_prefix:
                    for ch in chapters:
                        if ch.get('name') and not ch['name'].startswith(chapter_prefix):
                            ch['name'] = f"{chapter_prefix}: {ch['name']}"
                print(f"[SwimlaneDetector] Phase 2 generated {len(chapters)} chapters from LLM")
                return chapters
            else:
                print(f"[SwimlaneDetector] Phase 2 could not parse chapters from response")
                print(f"[SwimlaneDetector] Phase 2 content preview: {content[:500] if content else 'empty'}")
    except Exception as e:
        import traceback
        print(f"[SwimlaneDetector] Chapter generation error: {e}")
        print(f"[SwimlaneDetector] Chapter generation traceback: {traceback.format_exc()}")

    return None


def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling various formats."""
    import re

    if not content:
        return None

    # Try direct parse
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # Try code block extraction
    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object with brace matching
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
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            pass
                        break

    return None


async def detect_swimlanes_and_chapters(llm_client, root_task, event_model: Dict[str, Any], user_stories: List[Dict] = None) -> Dict[str, Any]:
    """
    Detect swimlanes (business capabilities) and chapters (workflows) for the event model.

    Uses a two-phase approach:
    1. Detect swimlanes (grouping by business capability)
    2. Generate chapters with GWT scenarios (potentially in batches for large models)

    Args:
        llm_client: LLM client for analysis
        root_task: Root task for context
        event_model: Event model with events, commands, read_models, etc.
        user_stories: Optional list of user stories with acceptance criteria for richer GWT scenarios

    Returns:
        Enhanced event model with swimlanes and chapters
    """
    num_events = len(event_model.get('events', []))
    num_commands = len(event_model.get('commands', []))
    num_read_models = len(event_model.get('read_models', []))

    print(f"[SwimlaneDetector] Processing: {num_events} events, {num_commands} commands, {num_read_models} read models")

    # Try to get user stories from root_task.context if not provided directly
    if not user_stories and root_task and hasattr(root_task, 'context') and root_task.context:
        user_stories = root_task.context.get('user_stories', [])
        if user_stories:
            print(f"[SwimlaneDetector] Extracted {len(user_stories)} user stories from root_task.context")

    if user_stories:
        print(f"[SwimlaneDetector] Using {len(user_stories)} user stories for scenario context")

    # Phase 1: Detect swimlanes
    print("[SwimlaneDetector] Phase 1: Detecting swimlanes...")
    swimlanes = await _detect_swimlanes_only(llm_client, root_task, event_model)

    if not swimlanes:
        print("[SwimlaneDetector] Phase 1 failed, using fallback")
        return _generate_fallback_structure(event_model)

    print(f"[SwimlaneDetector] Phase 1 complete: {len(swimlanes)} swimlanes detected")
    event_model['swimlanes'] = swimlanes

    # Phase 2: Generate chapters with GWT
    print("[SwimlaneDetector] Phase 2: Generating chapters with GWT scenarios...")
    chapters = await _generate_chapters_with_gwt(llm_client, root_task, event_model, swimlanes, user_stories=user_stories)

    if not chapters:
        print("[SwimlaneDetector] Phase 2 failed, generating basic chapters from swimlanes")
        # Generate basic chapters from swimlanes with GWT
        chapters = _generate_chapters_from_swimlanes(event_model, swimlanes)

    print(f"[SwimlaneDetector] Phase 2 complete: {len(chapters)} chapters generated")
    event_model['chapters'] = chapters

    # Count GWT scenarios
    total_gwt = sum(
        len(slice.get('gwt_scenarios', []))
        for ch in chapters
        for slice in ch.get('slices', [])
    )
    print(f"[SwimlaneDetector] Total GWT scenarios: {total_gwt}")

    return event_model


def _generate_chapters_from_swimlanes(event_model: Dict[str, Any], swimlanes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate chapters with GWT from swimlanes when LLM phase 2 fails."""
    commands = {c.get('name'): c for c in event_model.get('commands', []) if isinstance(c, dict) and c.get('name')}
    read_models = {rm.get('name'): rm for rm in event_model.get('read_models', []) if isinstance(rm, dict) and rm.get('name')}

    chapters = []

    for swimlane in swimlanes:
        slices = []

        # Add command slices
        for cmd_name in swimlane.get('commands', []):
            cmd = commands.get(cmd_name, {})
            triggered_events = cmd.get('triggers_events', [])
            params = cmd.get('parameters', [])
            required_params = [p.get('name') for p in params if isinstance(p, dict) and p.get('required')]

            gwt_scenarios = [
                {
                    "given": "Valid request data is provided",
                    "when": f"{cmd_name} command is executed",
                    "then": f"{', '.join(triggered_events) if triggered_events else cmd_name + 'Completed'} event(s) are emitted"
                }
            ]

            if required_params:
                gwt_scenarios.append({
                    "given": f"Required parameter(s) {', '.join(required_params[:2])} are missing",
                    "when": f"{cmd_name} command is executed",
                    "then": "Validation error is returned"
                })
            else:
                gwt_scenarios.append({
                    "given": "Invalid or malformed data is provided",
                    "when": f"{cmd_name} command is executed",
                    "then": "Error response is returned"
                })

            slices.append({
                "type": "state_change",
                "command": cmd_name,
                "events": triggered_events,
                "gwt_scenarios": gwt_scenarios
            })

        # Add read model slices
        for rm_name in swimlane.get('read_models', []):
            rm = read_models.get(rm_name, {})
            source_events = rm.get('data_source', [])

            gwt_scenarios = [
                {
                    "given": f"Relevant events have occurred",
                    "then": f"{rm_name} displays the current data"
                },
                {
                    "given": "No matching data exists",
                    "then": f"{rm_name} shows empty state"
                }
            ]

            slices.append({
                "type": "state_view",
                "read_model": rm_name,
                "source_events": source_events,
                "gwt_scenarios": gwt_scenarios
            })

        if slices:
            chapters.append({
                "name": f"{swimlane.get('name', 'Main')} Workflows",
                "description": swimlane.get('description', ''),
                "slices": slices
            })

    return chapters
