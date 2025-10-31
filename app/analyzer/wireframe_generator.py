"""Wireframe and Data Flow Generator for Event Models

Generates UI wireframes and tracks complete data flow through the system
following Event Modeling best practices.
"""

from typing import List, Dict, Any
import json


async def generate_wireframes_and_dataflow(llm_client, root_task, event_model: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate wireframes and complete data flow tracking for the event model.

    Wireframes show UI components that:
    - Provide data to commands (inputs, forms)
    - Display data from read models (lists, tables, text)
    - Trigger commands (buttons, actions)

    Data flow tracks:
    - UI fields → Command parameters
    - Command parameters → Event attributes
    - Event attributes → Read Model fields
    - Read Model fields → UI components

    Args:
        llm_client: LLM client for generation
        root_task: Root task for context
        event_model: Event model with commands, events, read_models, chapters

    Returns:
        Enhanced event model with wireframes and data_flow
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

    chapters = event_model.get('chapters', [])
    commands = event_model.get('commands', [])
    read_models = event_model.get('read_models', [])

    prompt = f"""You are generating wireframes and data flow for an Event Model.

PROJECT: {root_task.description if root_task else ""}

CURRENT EVENT MODEL:
Events: {json.dumps(serializable_events, indent=2)}
Commands: {json.dumps(commands, indent=2)}
Read Models: {json.dumps(read_models, indent=2)}
Chapters: {json.dumps(chapters, indent=2)}

EVENT MODELING WIREFRAME PRINCIPLES:

1. **Wireframes are LOW-FIDELITY**:
   - Simple boxes and labels
   - Focus on DATA, not aesthetics
   - Show what data is collected/displayed, not how it looks

2. **Component Types**:
   - **input**: Text fields, dropdowns, date pickers (user provides data)
   - **button**: Actions that trigger commands
   - **text**: Display a single value from read model
   - **list**: Display multiple items from read model
   - **table**: Display structured data from read model
   - **form**: Group of inputs that collectively trigger a command

3. **Component Structure**:
   - **field**: The data field name (maps to command parameter or read model field)
   - **label**: Human-readable label
   - **triggers**: (for buttons) Which command it triggers
   - **displays**: (for display components) Which read model fields it shows

YOUR TASK:

For each chapter/slice, generate wireframes showing the UI screens.

1. **State Change Slices** (Command → Event):
   - Create wireframe showing how user provides data to the command
   - Include input components for each command parameter
   - Include button component that triggers the command

2. **State View Slices** (Event → Read Model):
   - Create wireframe showing how read model data is displayed
   - Include display components for each read model field
   - **CRITICAL**: Set the "read_models" field to list which read models this wireframe displays

3. **Data Flow Tracking**:
   - Map UI input fields → Command parameters
   - Map Command parameters → Event attributes
   - Map Event attributes → Read Model fields
   - Map Read Model fields → UI display components

EXAMPLE for a shopping cart "Add Item" slice:

{{
  "wireframes": [
    {{
      "name": "Add Item Screen",
      "slice": "AddItem",
      "type": "state_change",
      "components": [
        {{
          "type": "input",
          "field": "productId",
          "label": "Product ID"
        }},
        {{
          "type": "input",
          "field": "quantity",
          "label": "Quantity"
        }},
        {{
          "type": "button",
          "label": "Add to Cart",
          "triggers": "AddItem"
        }}
      ]
    }},
    {{
      "name": "Cart Items View",
      "slice": "CartItems",
      "type": "state_view",
      "read_models": ["CartItems"],
      "components": [
        {{
          "type": "list",
          "label": "Items in Cart",
          "displays": ["items"]
        }},
        {{
          "type": "text",
          "field": "totalPrice",
          "label": "Total Price"
        }}
      ]
    }}
  ],
  "data_flow": [
    {{
      "from": "UI:AddItemScreen.productId",
      "to": "Command:AddItem.productId",
      "description": "User provides product ID"
    }},
    {{
      "from": "Command:AddItem.productId",
      "to": "Event:ItemAdded.productId",
      "description": "Command passes product ID to event"
    }},
    {{
      "from": "Event:ItemAdded.productId",
      "to": "ReadModel:CartItems.items.productId",
      "description": "Event populates read model"
    }},
    {{
      "from": "ReadModel:CartItems.items",
      "to": "UI:CartItemsView.items",
      "description": "Read model data displayed in UI"
    }}
  ]
}}

CRITICAL RULES:

1. **Every command parameter must have a UI source**:
   - Either an input field in the wireframe
   - Or derived from a read model displayed on the screen
   - Or a system-generated value (mark as "System" source)

2. **Every read model field must have an event source**:
   - Trace back to which event(s) provide this data
   - Mark derived/calculated fields

3. **Complete the loop**:
   - UI → Command → Event → Read Model → UI
   - Track data through the ENTIRE system

4. **One wireframe per slice**:
   - State change slices get input wireframes
   - State view slices get display wireframes
   - Automation slices may not need wireframes

5. **Use simple component types**:
   - Don't overthink the UI design
   - Focus on what data is collected/displayed

6. **CRITICAL - Link wireframes to read models**:
   - Every state_view wireframe MUST have a "read_models" array listing which read models it displays
   - Match the "displays" fields in components to actual read model names
   - Example: If wireframe displays "items" and "totalPrice", and those come from "CartItems" read model, set "read_models": ["CartItems"]
   - State change wireframes may have read_models if they display data alongside input forms
   - If no read model is displayed, set "read_models": null or []

Return JSON in this exact format:
{{
  "wireframes": [...],
  "data_flow": [...]
}}

IMPORTANT: Generate wireframes for ALL slices in the chapters. Be comprehensive.

Return ONLY valid JSON, no explanation."""

    try:
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=32000,
            temperature=0.3
        )

        # Extract JSON
        import re

        # Extract content from OpenAI-format response
        if isinstance(response, dict) and "choices" in response:
            content = response["choices"][0]["message"]["content"]
        else:
            print(f"[WireframeGenerator] Unexpected response format: {type(response)}")
            return event_model

        print(f"[WireframeGenerator] Content preview: {content[:200] if content else 'Empty'}")

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

        if data and 'wireframes' in data:
            event_model['wireframes'] = data.get('wireframes', [])
            event_model['data_flow'] = data.get('data_flow', [])
            print(f"[WireframeGenerator] Generated {len(event_model.get('wireframes', []))} wireframes and {len(event_model.get('data_flow', []))} data flow mappings")
            return event_model
        else:
            print("[WireframeGenerator] Failed to generate wireframes, skipping")
            return event_model

    except Exception as e:
        print(f"[WireframeGenerator] Error generating wireframes: {e}")
        return event_model
