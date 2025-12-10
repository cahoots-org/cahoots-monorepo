"""Unified artifact editing endpoints.

Provides a single interface for editing any project artifact (epic, story, swimlane,
requirement, chapter, slice) with automatic cascade analysis and atomic updates.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import json

from app.storage import TaskStorage
from app.api.dependencies import get_task_storage, get_llm_client
from app.models import Task


router = APIRouter(prefix="/api/edit", tags=["edit"])


# Artifact types that can be edited
ARTIFACT_TYPES = [
    "epic", "story", "swimlane", "feature",  # Business artifacts
    "chapter", "slice", "gwt",                # Event model artifacts
    "requirement", "functional_requirement", "non_functional_requirement",  # Requirements
    "command", "event", "read_model", "automation"  # Technical artifacts
]


class ArtifactChange(BaseModel):
    """Represents a change to a single artifact."""
    artifact_type: str
    artifact_id: str
    field: str
    old_value: Any
    new_value: Any
    reason: Optional[str] = None


class AnalyzeEditRequest(BaseModel):
    """Request to analyze an artifact edit and its cascade effects."""
    artifact_type: str = Field(..., description="Type: epic, story, swimlane, requirement, chapter, slice, gwt, command, event, read_model")
    artifact_id: str = Field(..., description="Unique identifier of the artifact")
    changes: Dict[str, Any] = Field(..., description="Field -> new value mapping")


class AnalyzeEditResponse(BaseModel):
    """Response with direct change and cascade effects."""
    direct_change: ArtifactChange
    cascade_changes: List[ArtifactChange]
    warnings: List[str] = []
    summary: str


class ApplyEditRequest(BaseModel):
    """Request to apply direct change and selected cascade changes."""
    artifact_type: str
    artifact_id: str
    changes: Dict[str, Any]
    approved_cascades: List[ArtifactChange] = []


class ApplyEditResponse(BaseModel):
    """Response after applying changes."""
    success: bool
    applied_count: int
    updated_artifacts: List[str]


@router.get("/artifact-types")
async def get_artifact_types():
    """Get list of editable artifact types with metadata."""
    return {
        "types": [
            {"type": "epic", "label": "Epic", "icon": "🎯", "fields": ["name", "title", "description", "business_value"]},
            {"type": "story", "label": "User Story", "icon": "📖", "fields": ["title", "actor", "action", "benefit", "description", "acceptance_criteria"]},
            {"type": "swimlane", "label": "Swimlane", "icon": "🏢", "fields": ["name", "description", "commands", "read_models", "automations"]},
            {"type": "chapter", "label": "Chapter", "icon": "📚", "fields": ["name", "description", "business_focus"]},
            {"type": "slice", "label": "Slice", "icon": "🍕", "fields": ["command", "events", "read_model", "gwt_scenarios"]},
            {"type": "command", "label": "Command", "icon": "🔵", "fields": ["name", "description", "aggregate"]},
            {"type": "event", "label": "Event", "icon": "🟠", "fields": ["name", "description", "aggregate", "triggered_by"]},
            {"type": "read_model", "label": "Read Model", "icon": "🟢", "fields": ["name", "description", "data_source"]},
            {"type": "gwt", "label": "GWT Scenario", "icon": "✅", "fields": ["given", "when", "then"]},
            {"type": "requirement", "label": "Requirement", "icon": "📋", "fields": ["id", "description", "priority", "source"]},
        ]
    }


@router.post("/tasks/{task_id}/analyze", response_model=AnalyzeEditResponse)
async def analyze_edit(
    task_id: str,
    request: AnalyzeEditRequest,
    storage: TaskStorage = Depends(get_task_storage),
    llm_client = Depends(get_llm_client)
) -> AnalyzeEditResponse:
    """
    Analyze an artifact edit and determine cascade effects.

    Returns the direct change plus any cascading changes needed to maintain
    consistency across all project artifacts.
    """
    # Validate artifact type
    if request.artifact_type not in ARTIFACT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact type. Must be one of: {ARTIFACT_TYPES}"
        )

    # Get the task
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    # Find the current artifact state
    current_artifact = _find_artifact(task, request.artifact_type, request.artifact_id)
    if not current_artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{request.artifact_type} {request.artifact_id} not found"
        )

    # Build the direct change
    old_values = {}
    for field, new_value in request.changes.items():
        old_values[field] = current_artifact.get(field) if isinstance(current_artifact, dict) else getattr(current_artifact, field, None)

    # Create direct change record (use first field for simple display)
    first_field = list(request.changes.keys())[0]
    direct_change = ArtifactChange(
        artifact_type=request.artifact_type,
        artifact_id=request.artifact_id,
        field=first_field,
        old_value=old_values.get(first_field),
        new_value=request.changes.get(first_field)
    )

    # Analyze cascade effects using LLM
    cascade_changes, warnings, summary = await _analyze_cascade_effects(
        task, request.artifact_type, request.artifact_id,
        request.changes, old_values, llm_client
    )

    return AnalyzeEditResponse(
        direct_change=direct_change,
        cascade_changes=cascade_changes,
        warnings=warnings,
        summary=summary
    )


@router.post("/tasks/{task_id}/apply", response_model=ApplyEditResponse)
async def apply_edit(
    task_id: str,
    request: ApplyEditRequest,
    storage: TaskStorage = Depends(get_task_storage)
) -> ApplyEditResponse:
    """
    Apply an artifact edit and approved cascade changes atomically.

    All changes are applied together - if any fail, none are saved.
    """
    # Get the task
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )

    updated_artifacts = []

    try:
        # Apply the direct change
        _apply_artifact_change(task, request.artifact_type, request.artifact_id, request.changes)
        updated_artifacts.append(f"{request.artifact_type}:{request.artifact_id}")

        # Apply approved cascades
        for cascade in request.approved_cascades:
            _apply_artifact_change(task, cascade.artifact_type, cascade.artifact_id, {cascade.field: cascade.new_value})
            updated_artifacts.append(f"{cascade.artifact_type}:{cascade.artifact_id}")

        # Save the task
        await storage.save_task(task)

        print(f"[Edit] Applied {len(updated_artifacts)} changes to task {task_id}")

        return ApplyEditResponse(
            success=True,
            applied_count=len(updated_artifacts),
            updated_artifacts=updated_artifacts
        )

    except Exception as e:
        print(f"[Edit] Error applying changes: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply changes: {str(e)}"
        )


def _find_artifact(task: Task, artifact_type: str, artifact_id: str) -> Optional[Dict[str, Any]]:
    """Find an artifact within the task by type and ID."""
    metadata = task.metadata or {}
    context = task.context or {}

    if artifact_type == "epic":
        epics = context.get("epics", []) or metadata.get("epics", [])
        for epic in epics:
            if epic.get("id") == artifact_id or epic.get("title") == artifact_id:
                return epic

    elif artifact_type == "story":
        stories = context.get("user_stories", []) or metadata.get("user_stories", [])
        for story in stories:
            if story.get("id") == artifact_id or story.get("title") == artifact_id:
                return story

    elif artifact_type in ("swimlane", "feature"):
        swimlanes = metadata.get("swimlanes", [])
        for swimlane in swimlanes:
            if swimlane.get("name") == artifact_id:
                return swimlane

    elif artifact_type == "chapter":
        chapters = metadata.get("chapters", [])
        for chapter in chapters:
            if chapter.get("name") == artifact_id:
                return chapter

    elif artifact_type == "slice":
        chapters = metadata.get("chapters", [])
        for chapter in chapters:
            for slice in chapter.get("slices", []):
                slice_id = slice.get("command") or slice.get("read_model") or slice.get("automation_name")
                if slice_id == artifact_id:
                    return slice

    elif artifact_type == "gwt":
        # GWT scenarios are nested in slices or stories
        chapters = metadata.get("chapters", [])
        for chapter in chapters:
            for slice in chapter.get("slices", []):
                for i, gwt in enumerate(slice.get("gwt_scenarios", [])):
                    if f"{slice.get('command', 'gwt')}_{i}" == artifact_id:
                        return gwt

    elif artifact_type in ("requirement", "functional_requirement"):
        requirements = metadata.get("requirements", {})
        for req in requirements.get("functional_requirements", []):
            if req.get("id") == artifact_id:
                return req

    elif artifact_type == "non_functional_requirement":
        requirements = metadata.get("requirements", {})
        for req in requirements.get("non_functional_requirements", []):
            if req.get("id") == artifact_id:
                return req

    elif artifact_type == "command":
        commands = metadata.get("commands", [])
        for cmd in commands:
            if cmd.get("name") == artifact_id:
                return cmd

    elif artifact_type == "event":
        events = metadata.get("extracted_events", [])
        for evt in events:
            if evt.get("name") == artifact_id:
                return evt

    elif artifact_type == "read_model":
        read_models = metadata.get("read_models", [])
        for rm in read_models:
            if rm.get("name") == artifact_id:
                return rm

    elif artifact_type == "automation":
        # Automations might be in swimlanes or chapters
        swimlanes = metadata.get("swimlanes", [])
        for swimlane in swimlanes:
            for auto in swimlane.get("automations", []):
                if auto == artifact_id or (isinstance(auto, dict) and auto.get("name") == artifact_id):
                    return {"name": auto} if isinstance(auto, str) else auto

    return None


def _apply_artifact_change(task: Task, artifact_type: str, artifact_id: str, changes: Dict[str, Any]):
    """Apply changes to an artifact within the task."""
    if not task.metadata:
        task.metadata = {}
    if not task.context:
        task.context = {}

    if artifact_type == "epic":
        epics = task.context.get("epics", []) or task.metadata.get("epics", [])
        for epic in epics:
            if epic.get("id") == artifact_id or epic.get("title") == artifact_id:
                for field, value in changes.items():
                    epic[field] = value
                # Ensure epics are in context
                task.context["epics"] = epics
                return

    elif artifact_type == "story":
        stories = task.context.get("user_stories", []) or task.metadata.get("user_stories", [])
        for story in stories:
            if story.get("id") == artifact_id or story.get("title") == artifact_id:
                for field, value in changes.items():
                    story[field] = value
                task.context["user_stories"] = stories
                return

    elif artifact_type in ("swimlane", "feature"):
        swimlanes = task.metadata.get("swimlanes", [])
        for swimlane in swimlanes:
            if swimlane.get("name") == artifact_id:
                for field, value in changes.items():
                    swimlane[field] = value
                return

    elif artifact_type == "chapter":
        chapters = task.metadata.get("chapters", [])
        for chapter in chapters:
            if chapter.get("name") == artifact_id:
                for field, value in changes.items():
                    chapter[field] = value
                return

    elif artifact_type == "slice":
        chapters = task.metadata.get("chapters", [])
        for chapter in chapters:
            for slice in chapter.get("slices", []):
                slice_id = slice.get("command") or slice.get("read_model") or slice.get("automation_name")
                if slice_id == artifact_id:
                    for field, value in changes.items():
                        slice[field] = value
                    return

    elif artifact_type in ("requirement", "functional_requirement"):
        if "requirements" not in task.metadata:
            task.metadata["requirements"] = {"functional_requirements": [], "non_functional_requirements": []}
        for req in task.metadata["requirements"].get("functional_requirements", []):
            if req.get("id") == artifact_id:
                for field, value in changes.items():
                    req[field] = value
                return

    elif artifact_type == "non_functional_requirement":
        if "requirements" not in task.metadata:
            task.metadata["requirements"] = {"functional_requirements": [], "non_functional_requirements": []}
        for req in task.metadata["requirements"].get("non_functional_requirements", []):
            if req.get("id") == artifact_id:
                for field, value in changes.items():
                    req[field] = value
                return

    elif artifact_type == "command":
        commands = task.metadata.get("commands", [])
        for cmd in commands:
            if cmd.get("name") == artifact_id:
                for field, value in changes.items():
                    cmd[field] = value
                return

    elif artifact_type == "event":
        events = task.metadata.get("extracted_events", [])
        for evt in events:
            if evt.get("name") == artifact_id:
                for field, value in changes.items():
                    evt[field] = value
                return

    elif artifact_type == "read_model":
        read_models = task.metadata.get("read_models", [])
        for rm in read_models:
            if rm.get("name") == artifact_id:
                for field, value in changes.items():
                    rm[field] = value
                return

    print(f"[Edit] Warning: Could not find {artifact_type}:{artifact_id} to update")


async def _analyze_cascade_effects(
    task: Task,
    artifact_type: str,
    artifact_id: str,
    changes: Dict[str, Any],
    old_values: Dict[str, Any],
    llm_client
) -> tuple[List[ArtifactChange], List[str], str]:
    """Use LLM to analyze what other artifacts should change."""

    metadata = task.metadata or {}
    context = task.context or {}

    # Build context for LLM
    prompt = f"""You are an expert at maintaining consistency across software project artifacts.

A user has edited a {artifact_type} with ID "{artifact_id}".

CHANGES MADE:
{json.dumps({field: {"old": old_values.get(field), "new": new_val} for field, new_val in changes.items()}, indent=2)}

CURRENT PROJECT STATE:

Epics: {json.dumps(context.get("epics", [])[:5], indent=2)}

User Stories: {json.dumps(context.get("user_stories", [])[:10], indent=2)}

Swimlanes/Features: {json.dumps(metadata.get("swimlanes", []), indent=2)}

Commands: {json.dumps(metadata.get("commands", [])[:15], indent=2)}

Events: {json.dumps(metadata.get("extracted_events", [])[:15], indent=2)}

Read Models: {json.dumps(metadata.get("read_models", [])[:10], indent=2)}

Requirements: {json.dumps(metadata.get("requirements", {}), indent=2)}

Chapters/Slices: {json.dumps(metadata.get("chapters", [])[:5], indent=2)}

ANALYZE CASCADE EFFECTS:

Carefully examine EVERY artifact in the project state above. Look for:
1. Direct references to the changed values (e.g., same numbers, terms, names)
2. Semantic relationships where the change implies updates elsewhere
3. Artifacts that implement or relate to the changed artifact

RELATIONSHIP RULES:
- Requirements with specific values (dimensions, limits, percentages) often cascade to:
  - Commands that enforce those limits
  - Events that carry those values as payload
  - Read models that display those values
  - Other requirements in the same category
  - User stories that describe the feature
- Epic changes cascade to: related stories
- Story changes cascade to: GWT scenarios, acceptance criteria, commands
- Command changes cascade to: events they trigger, read models they affect
- Event changes cascade to: read models that consume them, automations triggered by them
- Swimlane changes cascade to: all commands/events/read_models within them

IMPORTANT: When a requirement mentions specific values (like "10 columns by 20 rows" changing to "15 columns"),
you MUST check if other artifacts reference those same values and suggest updates.

Return ONLY valid JSON in this format:
{{
  "cascade_changes": [
    {{
      "artifact_type": "command",
      "artifact_id": "InitializeBoard",
      "field": "description",
      "old_value": "Create 10x20 board",
      "new_value": "Create 15x20 board",
      "reason": "Board dimensions changed in requirement FR-001"
    }}
  ],
  "warnings": ["Warning if manual review recommended"],
  "summary": "Brief summary of all cascade effects"
}}

Guidelines:
- Search for matching values, not just names
- If a requirement changes a number, find other artifacts with that same number
- Suggest concrete new_value text, don't leave placeholders
- If truly no cascades needed, explain why in summary

Return ONLY valid JSON."""

    try:
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.2
        )

        # Extract content
        content = None
        if isinstance(response, dict):
            if "choices" in response:
                msg = response["choices"][0].get("message", {})
                content = msg.get("content") or msg.get("reasoning", "")
            elif "content" in response:
                content = response["content"]

        if not content:
            return [], [], "No cascade analysis available"

        # Parse JSON
        result = _parse_json_response(content)

        if not result:
            return [], [], "Could not parse cascade analysis"

        # Convert to ArtifactChange objects
        cascade_changes = []
        for change in result.get("cascade_changes", []):
            cascade_changes.append(ArtifactChange(
                artifact_type=change["artifact_type"],
                artifact_id=change["artifact_id"],
                field=change["field"],
                old_value=change.get("old_value"),
                new_value=change["new_value"],
                reason=change.get("reason")
            ))

        warnings = result.get("warnings", [])
        summary = result.get("summary", f"Found {len(cascade_changes)} potential cascade changes")

        print(f"[Edit] Cascade analysis found {len(cascade_changes)} changes, {len(warnings)} warnings")

        return cascade_changes, warnings, summary

    except Exception as e:
        print(f"[Edit] Error in cascade analysis: {e}")
        import traceback
        traceback.print_exc()
        return [], [f"Cascade analysis failed: {str(e)}"], "Manual review recommended"


def _parse_json_response(content: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from LLM response."""
    import re

    if not content:
        return None

    # Try direct parse
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from code block
    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object
    start_idx = content.find('{')
    if start_idx != -1:
        brace_count = 0
        for i in range(start_idx, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    try:
                        return json.loads(content[start_idx:i+1])
                    except json.JSONDecodeError:
                        pass
                    break

    return None
