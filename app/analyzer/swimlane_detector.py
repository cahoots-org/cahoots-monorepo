"""Swimlane and Chapter Detection for Event Models

Organizes event models by business capabilities (swimlanes) and workflows (chapters)
following Event Modeling best practices from the book.
"""

from typing import List, Dict, Any
import json


async def detect_swimlanes_and_chapters(llm_client, root_task, event_model: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect swimlanes (business capabilities) and chapters (workflows) for the event model.

    Swimlanes group events by business capability/domain boundary.
    Chapters group slices into logical workflows that tell stories.

    Args:
        llm_client: LLM client for analysis
        root_task: Root task for context
        event_model: Event model with events, commands, read_models, etc.

    Returns:
        Enhanced event model with swimlanes and chapters
    """
    # Convert events to serializable format
    serializable_events = [
        {
            "name": e.name if hasattr(e, 'name') else e.get('name'),
            "event_type": e.event_type.value if hasattr(e, 'event_type') else e.get('event_type'),
            "description": e.description if hasattr(e, 'description') else e.get('description'),
            "actor": e.actor if hasattr(e, 'actor') else e.get('actor'),
            "affected_entity": e.affected_entity if hasattr(e, 'affected_entity') else e.get('affected_entity')
        }
        for e in event_model.get('events', [])
    ]

    prompt = f"""You are organizing an Event Model for Event Modeling best practices.

PROJECT: {root_task.description if root_task else ""}

CURRENT EVENT MODEL:
Events: {json.dumps(serializable_events, indent=2)}
Commands: {json.dumps(event_model.get('commands', []), indent=2)}
Read Models: {json.dumps(event_model.get('read_models', []), indent=2)}
Automations: {json.dumps(event_model.get('automations', []), indent=2)}

EVENT MODELING BOOK PRINCIPLES:

1. SWIMLANES (Business Capabilities / Services):
   - Swimlanes define STREAM BOUNDARIES
   - Events in one swimlane should form a COHERENT NARRATIVE when read in isolation
   - Each swimlane represents a business capability (e.g., "Cart", "Inventory", "Payment", "User")
   - Test: Hide all swimlanes but one - events should tell a compelling story to business people
   - Examples: "Product", "Order", "Shipping", "Authentication", "Notification"

2. CHAPTERS (Workflows / Contexts):
   - Chapters group slices into logical workflows
   - Each chapter represents a business process or context
   - Chapters can have sub-chapters for more granular organization
   - Examples: "Shopping" chapter with sub-chapters: "Items", "Checkout", "Payment"

3. STORYTELLING:
   - Events should be readable left-to-right like a narrative
   - Events in sequence tell the story of system capabilities
   - Focus on BEHAVIOR and DATA FLOW, not implementation

YOUR TASK:
Analyze the event model and identify:

1. **Swimlanes**: Group events, commands, and read models by business capability
   - Look at affected_entity field in events
   - Look at command names and what they operate on
   - Identify clear domain boundaries (e.g., User, Cart, Product, Order)
   - Typical system has 3-8 swimlanes

2. **Chapters**: Group related slices into workflows
   - Identify major business processes (e.g., "User Registration", "Shopping", "Checkout")
   - Each chapter should tell a coherent story
   - IMPORTANT: Each slice should appear in ONLY ONE chapter (no duplicates across chapters)
   - State view slices MUST include the source events that populate the read model

Return JSON in this exact format (NOTE: This is a FORMAT EXAMPLE ONLY - derive actual business rules from the project requirements, NOT from these placeholder examples):
{{
  "swimlanes": [
    {{
      "name": "Cart",
      "description": "Shopping cart management",
      "events": ["CartCreated", "ItemAdded", "ItemRemoved"],
      "commands": ["CreateCart", "AddItem", "RemoveItem"],
      "read_models": ["CartItems", "CartSummary"],
      "automations": []
    }},
    {{
      "name": "Product",
      "description": "Product catalog and pricing",
      "events": ["ProductPriceChanged", "ProductAdded"],
      "commands": ["UpdatePrice", "AddProduct"],
      "read_models": ["ProductCatalog"],
      "automations": ["PriceChangeNotification"]
    }}
  ],
  "chapters": [
    {{
      "name": "Example Chapter Name",
      "description": "Description of the business process",
      "slices": [
        {{
          "type": "state_change",
          "command": "ExampleCommand",
          "events": ["ExampleEvent"],
          "gwt_scenarios": [
            {{"given": "Valid preconditions are met", "when": "ExampleCommand is executed", "then": "ExampleEvent is triggered"}},
            {{"given": "Validation fails", "when": "ExampleCommand is executed", "then": "Error: Validation error message"}}
          ]
        }},
        {{
          "type": "state_view",
          "read_model": "ExampleReadModel",
          "source_events": ["ExampleEvent"],
          "gwt_scenarios": [
            {{"given": "ExampleEvent occurred with data", "then": "ExampleReadModel shows the data"}}
          ]
        }},
        {{
          "type": "automation",
          "automation_name": "ExampleAutomation",
          "trigger_event": "ExampleEvent",
          "result_events": ["ResultEvent"],
          "gwt_scenarios": [
            {{"given": "ExampleEvent occurred", "then": "ResultEvent is triggered"}}
          ]
        }}
      ]
    }}
  ]
}}

CRITICAL RULES:
1. Each slice (command or read_model) should appear in EXACTLY ONE chapter
2. If a command appears in multiple workflows, choose the chapter where it's most central
3. State view slices MUST include "source_events" array listing all events that populate the read model
4. Automation slices should use {{"type": "automation", "name": "AutomationName", "trigger_events": [...], "result_events": [...]}}
5. EVERY slice MUST include "gwt_scenarios" array with Given/When/Then scenarios:
   - State change slices: Use "given", "when", "then" (all three fields)
   - State view slices: Use "given", "then" (no "when" field)
   - Include at least 2 scenarios per slice (happy path + error/edge case)
   - Use concrete examples with real data values
   - IMPORTANT: Derive GWT scenarios from the actual PROJECT REQUIREMENTS and domain logic - DO NOT copy the placeholder examples above
   - Only include validation rules that are explicitly stated or clearly implied by the project description
   - Do NOT invent arbitrary constraints (like item limits, quantity restrictions, etc.) that aren't in the requirements

Guidelines:
- Swimlane names should be singular nouns (Cart, not Carts)
- Chapter names should describe the workflow/process
- Every event/command/read_model should belong to exactly ONE swimlane
- Events in a swimlane should form a coherent narrative
- Focus on business capabilities, not technical implementation

Return ONLY valid JSON, no explanation."""

    try:
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=16000,
            temperature=0.3
        )

        # Extract JSON
        import re

        # Extract content from OpenAI-format response
        if isinstance(response, dict) and "choices" in response:
            content = response["choices"][0]["message"]["content"]
        else:
            print(f"[SwimlaneDetector] Unexpected response format: {type(response)}")
            return event_model

        print(f"[SwimlaneDetector] Content preview: {content[:200] if content else 'Empty'}")

        data = None

        # Try direct parse
        try:
            data = json.loads(content.strip())
        except json.JSONDecodeError:
            pass

        # Try code block extraction
        if data is None:
            code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
            if code_block_match:
                try:
                    data = json.loads(code_block_match.group(1))
                except json.JSONDecodeError:
                    pass

        # Try brace matching
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
                                    break
                                except json.JSONDecodeError:
                                    pass

        if data and 'swimlanes' in data:
            event_model['swimlanes'] = data.get('swimlanes', [])
            event_model['chapters'] = data.get('chapters', [])
            print(f"[SwimlaneDetector] Detected {len(event_model.get('swimlanes', []))} swimlanes and {len(event_model.get('chapters', []))} chapters")
            return event_model
        else:
            print("[SwimlaneDetector] Failed to detect swimlanes, skipping")
            return event_model

    except Exception as e:
        print(f"[SwimlaneDetector] Error detecting swimlanes: {e}")
        return event_model
