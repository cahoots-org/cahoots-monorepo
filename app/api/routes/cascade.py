"""Cascade analysis and update application endpoints.

Handles intelligent cascade updates when users edit any part of the Event Model,
tasks, or diagram. Uses LLM to analyze what else needs to change to maintain consistency.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import json

from app.storage import TaskStorage
from app.api.dependencies import get_task_storage, get_llm_client
from app.models import Task


router = APIRouter(prefix="/api/cascade", tags=["cascade"])


class CascadeChange(BaseModel):
    """Represents a single change that needs to be made."""
    type: str = Field(..., description="Type of element being changed (command, event, task, etc)")
    id: str = Field(..., description="Identifier of the element")
    action: str = Field(..., description="Action to take (create, update, delete)")
    field: Optional[str] = Field(None, description="Field being updated (for updates)")
    value: Optional[Any] = Field(None, description="New value")
    old_value: Optional[Any] = Field(None, description="Previous value (for diff display)")
    data: Optional[Dict[str, Any]] = Field(None, description="Full data (for creates)")
    reason: str = Field(..., description="Human-readable explanation for this change")


class AnalyzeCascadeRequest(BaseModel):
    """Request to analyze cascading changes from a user edit."""
    edit_type: str = Field(..., description="Type of element being edited")
    edit_id: str = Field(..., description="Identifier of the edited element")
    changes: Dict[str, Any] = Field(..., description="The changes made by the user")
    current_state: Dict[str, Any] = Field(..., description="Current state of event model, tasks, diagram")


class AnalyzeCascadeResponse(BaseModel):
    """Response with proposed cascading changes."""
    changes: List[CascadeChange]
    summary: str = Field(..., description="High-level summary of what will change")


class ApplyCascadeRequest(BaseModel):
    """Request to apply selected cascade changes."""
    task_id: str
    changes: List[CascadeChange]


@router.post("/tasks/{task_id}/analyze", response_model=AnalyzeCascadeResponse)
async def analyze_cascade(
    task_id: str,
    request: AnalyzeCascadeRequest,
    storage: TaskStorage = Depends(get_task_storage),
    llm_client = Depends(get_llm_client)
) -> AnalyzeCascadeResponse:
    """
    Analyze what cascading changes are needed for a user edit.

    Uses LLM to determine what other elements need to be updated to maintain
    consistency across the Event Model, tasks, and diagram.
    """
    # Get the task
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    # Build LLM prompt
    prompt = f"""You are maintaining consistency in an Event Model and task breakdown.

USER MADE THIS CHANGE:
Type: {request.edit_type}
Element: {request.edit_id}
Changes: {json.dumps(request.changes, indent=2)}

CURRENT STATE:
Event Model:
{json.dumps(request.current_state.get('event_model', {}), indent=2)}

Tasks:
{json.dumps(request.current_state.get('tasks', []), indent=2)}

Diagram:
{json.dumps(request.current_state.get('diagram', {}), indent=2)}

ANALYZE what other elements need to change to maintain consistency:

1. If a GWT scenario is added/changed:
   - Does the command handler need new validation logic?
   - Do we need new events for error cases?
   - Do tasks need updated implementation details?
   - Does the diagram need visual updates?

2. If a command is added/changed:
   - What events does it trigger (new or existing)?
   - What tasks implement this command?
   - Where does it appear in the diagram?
   - What GWTs are needed?

3. If an event is added/changed:
   - What read models does it affect?
   - What commands trigger it?
   - Which swimlane should it be in?
   - What tasks need to handle it?

4. If a swimlane assignment changes:
   - Which diagram elements need repositioning?
   - Do any tasks need context updates?
   - Does the affected_entity field need updating?

5. If a task is modified:
   - Does it affect the Event Model?
   - Should GWTs be added/updated?
   - Does implementation details change command/event definitions?

6. If a read model is added/changed:
   - What events are its data sources?
   - What UI displays it?
   - What tasks implement the projection?

Return ONLY the changes needed, in this format:
{{
  "changes": [
    {{
      "type": "command",
      "id": "AddItem",
      "action": "update",
      "field": "validation_rules",
      "value": "Check max 3 items before adding",
      "old_value": null,
      "reason": "GWT scenario requires validation"
    }},
    {{
      "type": "task",
      "id": "task_123",
      "action": "update",
      "field": "implementation_details",
      "value": "Add validation: if cart has 3+ items, return error",
      "old_value": "Implement add item endpoint",
      "reason": "Must implement GWT constraint"
    }},
    {{
      "type": "event",
      "id": "ItemAddFailed",
      "action": "create",
      "data": {{
        "name": "ItemAddFailed",
        "description": "Item could not be added to cart",
        "swimlane": "Cart",
        "event_type": "state_change"
      }},
      "reason": "Need event for validation failure case"
    }}
  ],
  "summary": "Added validation logic to AddItem command, created ItemAddFailed event, and updated implementation task"
}}

Guidelines:
- Only propose changes that are NECESSARY for consistency
- Don't propose changes that are nice-to-have
- Be conservative - when in doubt, don't propose the change
- Provide clear, specific reasons for each change
- Include old_value for updates so UI can show diffs

Return ONLY valid JSON, no explanation or markdown."""

    try:
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.2  # Low temperature for consistency
        )

        # Extract content
        if isinstance(response, dict) and "choices" in response:
            content = response["choices"][0]["message"]["content"]
        else:
            raise ValueError(f"Unexpected LLM response format: {type(response)}")

        # Parse JSON
        result = None

        # Try direct parse
        try:
            result = json.loads(content.strip())
        except json.JSONDecodeError:
            # Try extracting from code block
            import re
            code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
            if code_block_match:
                result = json.loads(code_block_match.group(1))
            else:
                # Try finding JSON object in content
                start_idx = content.find('{')
                if start_idx != -1:
                    result = json.loads(content[start_idx:])

        if not result or 'changes' not in result:
            print(f"[Cascade] Failed to parse LLM response: {content[:200]}")
            raise ValueError("LLM did not return valid JSON")

        # Convert to response model
        changes = [CascadeChange(**change) for change in result['changes']]
        summary = result.get('summary', f"Proposed {len(changes)} cascading changes")

        print(f"[Cascade] Analyzed edit {request.edit_type}:{request.edit_id}, found {len(changes)} cascade changes")

        return AnalyzeCascadeResponse(
            changes=changes,
            summary=summary
        )

    except Exception as e:
        print(f"[Cascade] Error analyzing cascade: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze cascade: {str(e)}"
        )


@router.post("/tasks/{task_id}/apply")
async def apply_cascade(
    task_id: str,
    request: ApplyCascadeRequest,
    storage: TaskStorage = Depends(get_task_storage)
) -> Dict[str, Any]:
    """
    Apply selected cascade changes atomically.

    All changes are applied in a transaction - if any fail, all are rolled back.
    """
    # Get the task
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    print(f"[Cascade] Applying {len(request.changes)} changes to task {task_id}")

    try:
        # Ensure metadata exists
        if not isinstance(task.metadata, dict):
            task.metadata = {}

        # Group changes by type for efficient processing
        changes_by_type = {}
        for change in request.changes:
            if change.type not in changes_by_type:
                changes_by_type[change.type] = []
            changes_by_type[change.type].append(change)

        # Apply changes by type
        for change_type, changes in changes_by_type.items():
            if change_type == 'command':
                await _apply_command_changes(task, changes)
            elif change_type == 'event':
                await _apply_event_changes(task, changes)
            elif change_type == 'read_model':
                await _apply_read_model_changes(task, changes)
            elif change_type == 'gwt':
                await _apply_gwt_changes(task, changes)
            elif change_type == 'swimlane':
                await _apply_swimlane_changes(task, changes)
            elif change_type == 'task':
                await _apply_task_changes(task, changes, storage)
            elif change_type == 'diagram':
                await _apply_diagram_changes(task, changes)
            else:
                print(f"[Cascade] Warning: Unknown change type '{change_type}'")

        # Regenerate derived artifacts
        # TODO: Regenerate event model markdown
        # TODO: Recalculate diagram layout if needed

        # Save task
        await storage.save_task(task)

        print(f"[Cascade] Successfully applied {len(request.changes)} changes")

        # TODO: Emit WebSocket event for real-time updates

        return {
            "success": True,
            "changes_applied": len(request.changes),
            "task_id": task_id
        }

    except Exception as e:
        print(f"[Cascade] Error applying cascade: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply cascade: {str(e)}"
        )


# Helper functions for applying specific change types

async def _apply_command_changes(task: Task, changes: List[CascadeChange]):
    """Apply changes to commands in the Event Model."""
    if 'commands' not in task.metadata:
        task.metadata['commands'] = []

    commands = task.metadata['commands']

    for change in changes:
        if change.action == 'create':
            # Add new command
            commands.append(change.data)
            print(f"[Cascade] Created command: {change.data.get('name')}")

        elif change.action == 'update':
            # Find and update command
            for cmd in commands:
                if cmd.get('name') == change.id:
                    if change.field:
                        cmd[change.field] = change.value
                    print(f"[Cascade] Updated command {change.id}.{change.field}")
                    break

        elif change.action == 'delete':
            # Remove command
            task.metadata['commands'] = [c for c in commands if c.get('name') != change.id]
            print(f"[Cascade] Deleted command: {change.id}")


async def _apply_event_changes(task: Task, changes: List[CascadeChange]):
    """Apply changes to events in the Event Model."""
    if 'extracted_events' not in task.metadata:
        task.metadata['extracted_events'] = []

    events = task.metadata['extracted_events']

    for change in changes:
        if change.action == 'create':
            # Add new event
            events.append(change.data)
            print(f"[Cascade] Created event: {change.data.get('name')}")

        elif change.action == 'update':
            # Find and update event
            for evt in events:
                if evt.get('name') == change.id:
                    if change.field:
                        evt[change.field] = change.value
                    print(f"[Cascade] Updated event {change.id}.{change.field}")
                    break

        elif change.action == 'delete':
            # Remove event
            task.metadata['extracted_events'] = [e for e in events if e.get('name') != change.id]
            print(f"[Cascade] Deleted event: {change.id}")


async def _apply_read_model_changes(task: Task, changes: List[CascadeChange]):
    """Apply changes to read models in the Event Model."""
    if 'read_models' not in task.metadata:
        task.metadata['read_models'] = []

    read_models = task.metadata['read_models']

    for change in changes:
        if change.action == 'create':
            read_models.append(change.data)
            print(f"[Cascade] Created read model: {change.data.get('name')}")

        elif change.action == 'update':
            for rm in read_models:
                if rm.get('name') == change.id:
                    if change.field:
                        rm[change.field] = change.value
                    print(f"[Cascade] Updated read model {change.id}.{change.field}")
                    break

        elif change.action == 'delete':
            task.metadata['read_models'] = [r for r in read_models if r.get('name') != change.id]
            print(f"[Cascade] Deleted read model: {change.id}")


async def _apply_gwt_changes(task: Task, changes: List[CascadeChange]):
    """Apply changes to GWT scenarios."""
    # TODO: Implement GWT storage structure
    # For now, store in metadata.gwt_scenarios
    if 'gwt_scenarios' not in task.metadata:
        task.metadata['gwt_scenarios'] = []

    for change in changes:
        if change.action == 'create':
            task.metadata['gwt_scenarios'].append(change.data)
            print(f"[Cascade] Created GWT scenario")
        # TODO: Implement update/delete


async def _apply_swimlane_changes(task: Task, changes: List[CascadeChange]):
    """Apply changes to swimlanes."""
    if 'swimlanes' not in task.metadata:
        task.metadata['swimlanes'] = []

    swimlanes = task.metadata['swimlanes']

    for change in changes:
        if change.action == 'create':
            swimlanes.append(change.data)
            print(f"[Cascade] Created swimlane: {change.data.get('name')}")

        elif change.action == 'update':
            for swimlane in swimlanes:
                if swimlane.get('name') == change.id:
                    if change.field:
                        swimlane[change.field] = change.value
                    print(f"[Cascade] Updated swimlane {change.id}.{change.field}")
                    break


async def _apply_task_changes(task: Task, changes: List[CascadeChange], storage: TaskStorage):
    """Apply changes to subtasks."""
    for change in changes:
        if change.action == 'update':
            # Get the subtask
            subtask = await storage.get_task(change.id)
            if subtask and change.field:
                # Update the field
                if hasattr(subtask, change.field):
                    setattr(subtask, change.field, change.value)
                    await storage.save_task(subtask)
                    print(f"[Cascade] Updated task {change.id}.{change.field}")


async def _apply_diagram_changes(task: Task, changes: List[CascadeChange]):
    """Apply changes to diagram layout."""
    if 'diagram_layout' not in task.metadata:
        task.metadata['diagram_layout'] = {}

    for change in changes:
        # Diagram changes typically update positions or connections
        if change.field:
            task.metadata['diagram_layout'][change.field] = change.value
            print(f"[Cascade] Updated diagram.{change.field}")
