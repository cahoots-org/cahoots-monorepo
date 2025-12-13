"""Universal Export Router for Cahoots.

Provides flexible export of project artifacts in multiple formats.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
import json
import csv
import io
import yaml
import zipfile

from app.api.dependencies import get_task_storage, require_feature
from app.api.routes.auth import get_current_user
from app.storage import TaskStorage

# Feature gate for export functionality
require_export = require_feature("export")

router = APIRouter(prefix="/api/tasks/{task_id}/export", tags=["export"])


# ============ TYPE DEFINITIONS ============

ARTIFACT_TYPES = Literal[
    "epics",
    "stories",
    "tasks",
    "commands",
    "events",
    "read_models",
    "functional_requirements",
    "non_functional_requirements",
    "acceptance_criteria",
    "gwt_scenarios",
    "executive_summary",
    "proposal",
]

FORMAT_TYPES = Literal["json", "csv", "markdown", "yaml", "llm_prompt"]

DOWNLOAD_STRUCTURE = Literal["single", "zip"]

PROMPT_TEMPLATES = Literal[
    "design_review",
    "implementation_guide",
    "test_generation",
    "documentation",
    "custom",
]


# ============ REQUEST/RESPONSE MODELS ============

class ExportRequest(BaseModel):
    """Request to export project artifacts."""
    artifacts: List[ARTIFACT_TYPES] = Field(
        ...,
        min_length=1,
        description="List of artifact types to export"
    )
    format: FORMAT_TYPES = Field(
        default="json",
        description="Export format"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include additional metadata fields"
    )
    include_ids: bool = Field(
        default=True,
        description="Include internal IDs"
    )
    flatten_hierarchy: bool = Field(
        default=False,
        description="Flatten nested structures (useful for CSV)"
    )
    download_structure: Optional[DOWNLOAD_STRUCTURE] = Field(
        default="single",
        description="Download as single document or ZIP archive with separate files"
    )
    # LLM Prompt specific fields
    prompt_template: Optional[PROMPT_TEMPLATES] = Field(
        default=None,
        description="Prompt template to use (for llm_prompt format)"
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Custom instructions for LLM prompt"
    )


# ============ PROMPT TEMPLATES ============

PROMPT_TEMPLATE_CONTENTS = {
    "design_review": """# Design Review Request

Please review the following project artifacts and provide feedback on:
- Architecture and design decisions
- Potential issues or risks
- Suggestions for improvement
- Missing considerations

## Project Context
{project_description}

## Artifacts
{artifacts_content}

Please provide a structured review with specific recommendations.""",

    "implementation_guide": """# Implementation Guide Request

Based on the following project artifacts, please create a detailed implementation guide that includes:
- Step-by-step implementation order
- Key technical decisions to make
- Potential challenges and solutions
- Best practices to follow

## Project Context
{project_description}

## Artifacts
{artifacts_content}

Please structure the guide so a developer can follow it sequentially.""",

    "test_generation": """# Test Case Generation Request

Based on the following project artifacts, please generate comprehensive test cases including:
- Unit tests for each component
- Integration tests for workflows
- Edge cases and error scenarios
- Test data suggestions

## Project Context
{project_description}

## Artifacts
{artifacts_content}

Please provide test cases in a format that can be easily implemented.""",

    "documentation": """# Documentation Generation Request

Based on the following project artifacts, please create documentation including:
- Technical overview
- API documentation
- User guide sections
- Architecture diagrams (described in text)

## Project Context
{project_description}

## Artifacts
{artifacts_content}

Please structure the documentation for both technical and non-technical readers.""",

    "custom": """{custom_instructions}

## Project Context
{project_description}

## Artifacts
{artifacts_content}""",
}


# ============ ENDPOINTS ============

@router.post("")
async def export_artifacts(
    task_id: str,
    request: ExportRequest,
    storage: TaskStorage = Depends(get_task_storage),
    current_user: dict = Depends(require_export),
):
    """
    Export selected artifacts in the specified format.

    Returns a downloadable file (single document or ZIP archive).
    """
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Project not found")

    if task.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Collect requested artifacts
    tree = await storage.get_task_tree(task_id)
    data = _collect_artifacts(task, tree, request.artifacts, request)

    # Check if ZIP archive requested
    if request.download_structure == "zip" and request.format != "llm_prompt":
        return _generate_zip_archive(data, task, task_id, request)

    # Generate output in requested format (single document)
    if request.format == "json":
        content = json.dumps(data, indent=2, default=str)
        media_type = "application/json"
        filename = f"{task_id}-export.json"

    elif request.format == "csv":
        content = _generate_csv(data, request.flatten_hierarchy)
        media_type = "text/csv"
        filename = f"{task_id}-export.csv"

    elif request.format == "markdown":
        content = _generate_markdown(data, task)
        media_type = "text/markdown"
        filename = f"{task_id}-export.md"

    elif request.format == "yaml":
        content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        media_type = "application/x-yaml"
        filename = f"{task_id}-export.yaml"

    elif request.format == "llm_prompt":
        content = _generate_llm_prompt(
            data,
            task,
            request.prompt_template or "design_review",
            request.custom_instructions
        )
        media_type = "text/plain"
        filename = f"{task_id}-prompt.txt"

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")

    # Return as downloadable file
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
    )


@router.get("/artifact-types")
async def list_artifact_types():
    """List available artifact types, formats, templates, and presets for export."""
    return {
        "artifact_types": [
            {"id": "epics", "name": "Epics", "category": "Project Structure"},
            {"id": "stories", "name": "User Stories", "category": "Project Structure"},
            {"id": "tasks", "name": "Implementation Tasks", "category": "Project Structure"},
            {"id": "commands", "name": "Commands", "category": "Event Model"},
            {"id": "events", "name": "Events", "category": "Event Model"},
            {"id": "read_models", "name": "Read Models", "category": "Event Model"},
            {"id": "functional_requirements", "name": "Functional Requirements", "category": "Requirements"},
            {"id": "non_functional_requirements", "name": "Non-Functional Requirements", "category": "Requirements"},
            {"id": "acceptance_criteria", "name": "Acceptance Criteria", "category": "Test Artifacts"},
            {"id": "gwt_scenarios", "name": "GWT Scenarios", "category": "Test Artifacts"},
            {"id": "executive_summary", "name": "Executive Summary", "category": "Documentation"},
            {"id": "proposal", "name": "Full Proposal", "category": "Documentation"},
        ],
        "formats": [
            {"id": "json", "name": "JSON", "description": "Structured data format"},
            {"id": "csv", "name": "CSV", "description": "Spreadsheet-compatible format"},
            {"id": "markdown", "name": "Markdown", "description": "Formatted document"},
            {"id": "yaml", "name": "YAML", "description": "Human-readable data format"},
            {"id": "llm_prompt", "name": "LLM Prompt", "description": "Formatted for AI assistants"},
        ],
        "prompt_templates": [
            {"id": "design_review", "name": "Design Review", "description": "Review architecture and design decisions"},
            {"id": "implementation_guide", "name": "Implementation Guide", "description": "Step-by-step implementation instructions"},
            {"id": "test_generation", "name": "Test Generation", "description": "Generate test cases from requirements"},
            {"id": "documentation", "name": "Documentation", "description": "Create technical documentation"},
            {"id": "custom", "name": "Custom", "description": "Write your own prompt"},
        ],
        "presets": [
            {
                "id": "all",
                "name": "All Artifacts",
                "artifacts": ["epics", "stories", "tasks", "commands", "events",
                             "read_models", "functional_requirements",
                             "non_functional_requirements", "acceptance_criteria",
                             "gwt_scenarios"],
            },
            {
                "id": "pm",
                "name": "PM Package",
                "artifacts": ["epics", "stories", "tasks", "functional_requirements",
                             "non_functional_requirements"],
            },
            {
                "id": "dev",
                "name": "Dev Package",
                "artifacts": ["epics", "stories", "tasks", "commands", "events",
                             "read_models", "gwt_scenarios"],
            },
            {
                "id": "consultant",
                "name": "Consultant Package",
                "artifacts": ["epics", "stories", "functional_requirements",
                             "non_functional_requirements", "executive_summary", "proposal"],
            },
        ],
    }


# ============ ARTIFACT COLLECTION ============

def _collect_artifacts(
    task,
    tree,
    artifact_types: List[str],
    options: ExportRequest,
) -> Dict[str, Any]:
    """Collect requested artifacts from task."""
    data = {}

    context = task.context or {}
    metadata = task.metadata or {}

    # Project info (always included)
    data["project"] = {
        "id": task.id,
        "description": task.description,
        "created_at": str(task.created_at) if hasattr(task, 'created_at') and task.created_at else None,
    }

    # Epics
    if "epics" in artifact_types:
        epics = context.get("epics", [])
        data["epics"] = _process_items(epics, options)

    # Stories
    if "stories" in artifact_types:
        stories = context.get("user_stories", [])
        data["stories"] = _process_items(stories, options)

    # Tasks
    if "tasks" in artifact_types:
        tasks = _extract_tasks_from_tree(tree)
        data["tasks"] = _process_items(tasks, options)

    # Commands
    if "commands" in artifact_types:
        commands = metadata.get("commands", [])
        data["commands"] = _normalize_items(commands)

    # Events
    if "events" in artifact_types:
        events = metadata.get("extracted_events", [])
        data["events"] = _normalize_items(events)

    # Read Models
    if "read_models" in artifact_types:
        read_models = metadata.get("read_models", [])
        data["read_models"] = _normalize_items(read_models)

    # Functional Requirements
    if "functional_requirements" in artifact_types:
        reqs = metadata.get("requirements", {})
        data["functional_requirements"] = reqs.get("functional_requirements", [])

    # Non-Functional Requirements
    if "non_functional_requirements" in artifact_types:
        reqs = metadata.get("requirements", {})
        data["non_functional_requirements"] = reqs.get("non_functional_requirements", [])

    # Acceptance Criteria
    if "acceptance_criteria" in artifact_types:
        criteria = []
        for story in context.get("user_stories", []):
            for ac in story.get("acceptance_criteria", []):
                criteria.append({
                    "story_id": story.get("id"),
                    "story_title": story.get("title", ""),
                    **(ac if isinstance(ac, dict) else {"description": ac}),
                })
        data["acceptance_criteria"] = criteria

    # GWT Scenarios
    if "gwt_scenarios" in artifact_types:
        scenarios = []
        for story in context.get("user_stories", []):
            for gwt in story.get("gwt_scenarios", []):
                scenarios.append({
                    "story_id": story.get("id"),
                    "story_title": story.get("title", ""),
                    "given": gwt.get("given", ""),
                    "when": gwt.get("when", ""),
                    "then": gwt.get("then", ""),
                })
        data["gwt_scenarios"] = scenarios

    # Executive Summary (generated)
    if "executive_summary" in artifact_types:
        data["executive_summary"] = _generate_executive_summary(task, tree)

    # Proposal (generated)
    if "proposal" in artifact_types:
        data["proposal"] = _generate_proposal(task, tree)

    return data


def _extract_tasks_from_tree(tree) -> List[Dict]:
    """Extract atomic tasks from task tree."""
    tasks = []

    def collect(node):
        if not node:
            return
        if node.get("is_atomic"):
            tasks.append({
                "id": node.get("id"),
                "description": node.get("description"),
                "story_points": node.get("story_points"),
                "implementation_details": node.get("implementation_details"),
                "epic_id": node.get("epic_id"),
                "story_id": node.get("story_id"),
                "depends_on": node.get("depends_on", []),
            })
        for child in node.get("children", []):
            collect(child)

    if tree:
        if isinstance(tree, dict):
            collect(tree)
        elif hasattr(tree, '__dict__'):
            collect(tree.__dict__)

    return tasks


def _process_items(items: List, options: ExportRequest) -> List[Dict]:
    """Process items based on export options."""
    result = []

    for item in items:
        if isinstance(item, str):
            result.append({"name": item})
        elif isinstance(item, dict):
            processed = dict(item)

            # Remove IDs if not requested
            if not options.include_ids:
                processed.pop("id", None)
                processed.pop("_id", None)

            # Remove metadata if not requested
            if not options.include_metadata:
                processed.pop("created_at", None)
                processed.pop("updated_at", None)
                processed.pop("metadata", None)

            result.append(processed)

    return result


def _normalize_items(items: List) -> List[Dict]:
    """Normalize items to consistent dict format."""
    result = []
    for item in items:
        if isinstance(item, str):
            result.append({"name": item, "description": ""})
        elif isinstance(item, dict):
            result.append(item)
    return result


# ============ EXECUTIVE SUMMARY & PROPOSAL GENERATION ============

def _calculate_scope_metrics(task, tree) -> Dict[str, Any]:
    """Calculate scope metrics for executive summary."""
    context = task.context or {}
    metadata = task.metadata or {}

    epics = context.get("epics", [])
    stories = context.get("user_stories", [])
    events = metadata.get("extracted_events", [])
    commands = metadata.get("commands", [])

    # Count tasks
    total_tasks = 0
    def count_tasks(node):
        nonlocal total_tasks
        if not node:
            return
        total_tasks += 1
        if isinstance(node, dict):
            for child in node.get("children", []):
                count_tasks(child)

    if tree:
        if isinstance(tree, dict):
            count_tasks(tree)
        elif hasattr(tree, '__dict__'):
            count_tasks(tree.__dict__)

    # Complexity rating
    feature_count = len(epics) + len(stories)
    if feature_count > 30:
        complexity_rating = "Large"
    elif feature_count > 15:
        complexity_rating = "Medium"
    else:
        complexity_rating = "Small"

    return {
        "epic_count": len(epics),
        "story_count": len(stories),
        "total_tasks": total_tasks,
        "complexity_rating": complexity_rating,
        "event_count": len(events),
        "command_count": len(commands),
    }


def _aggregate_by_business_domain(task) -> List[Dict]:
    """Aggregate artifacts by business domain for consultant-friendly output."""
    context = task.context or {}
    metadata = task.metadata or {}

    epics = context.get("epics", [])
    stories = context.get("user_stories", [])
    commands = metadata.get("commands", [])
    events = metadata.get("extracted_events", [])
    read_models = metadata.get("read_models", [])

    # Group by epic as domain
    domains = []
    for epic in epics:
        epic_id = epic.get("id", "")
        epic_stories = [s for s in stories if s.get("epic_id") == epic_id]

        # Extract actions (commands), views (read models), events for this domain
        domain_commands = []
        domain_events = []
        domain_views = []

        for story in epic_stories:
            story_id = story.get("id", "")
            # Simple heuristic: associate commands/events with stories by name matching
            for cmd in commands:
                cmd_name = cmd.get("name", "") if isinstance(cmd, dict) else cmd
                domain_commands.append(cmd_name)
            for evt in events:
                evt_name = evt.get("name", "") if isinstance(evt, dict) else evt
                domain_events.append(evt_name)

        for rm in read_models:
            rm_name = rm.get("name", "") if isinstance(rm, dict) else rm
            domain_views.append(rm_name)

        domains.append({
            "name": epic.get("title", "Unnamed Domain"),
            "description": epic.get("description", ""),
            "story_count": len(epic_stories),
            "actions": list(set(domain_commands))[:5],  # Dedupe, limit
            "views": list(set(domain_views))[:5],
            "automations": [],
        })

    return domains


def _generate_executive_summary(task, tree) -> str:
    """Generate executive summary text."""
    metrics = _calculate_scope_metrics(task, tree)
    domains = _aggregate_by_business_domain(task)

    domain_names = [d["name"] for d in domains][:5]
    total_capabilities = sum(
        len(d.get("actions", [])) + len(d.get("views", [])) + len(d.get("automations", []))
        for d in domains
    )

    summary = f"This project delivers a comprehensive solution spanning {len(domains)} core business areas"

    if domain_names:
        summary += f" including {', '.join(domain_names[:3])}"
        if len(domain_names) > 3:
            summary += f", and {len(domain_names) - 3} more"

    summary += f". The system provides {total_capabilities} distinct capabilities"

    if metrics["story_count"] > 0:
        summary += f" across {metrics['story_count']} user stories"

    summary += "."

    # Add complexity note
    summary += f"\n\nProject Complexity: {metrics['complexity_rating']}"
    summary += f"\n- {metrics['epic_count']} Features (Epics)"
    summary += f"\n- {metrics['story_count']} User Stories"
    summary += f"\n- {metrics['total_tasks']} Implementation Tasks"
    summary += f"\n- {metrics['command_count']} User Actions"

    return summary


def _generate_proposal(task, tree) -> str:
    """Generate full proposal markdown."""
    domains = _aggregate_by_business_domain(task)
    context = task.context or {}
    metadata = task.metadata or {}

    epics = context.get("epics", [])
    stories = context.get("user_stories", [])
    requirements = metadata.get("requirements", {})
    exec_summary = _generate_executive_summary(task, tree)

    lines = ["# Project Proposal", ""]

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(task.description or "No description provided.")
    lines.append("")
    lines.append(exec_summary)
    lines.append("")

    # Business Capabilities
    if domains:
        lines.append("## Business Capabilities")
        lines.append("")
        for domain in domains:
            lines.append(f"### {domain['name']}")
            if domain.get("description"):
                lines.append(f"{domain['description']}")
            lines.append("")
            if domain.get("actions"):
                lines.append("**User Actions:**")
                for action in domain["actions"]:
                    lines.append(f"- {action}")
                lines.append("")
            if domain.get("views"):
                lines.append("**Information Views:**")
                for view in domain["views"]:
                    lines.append(f"- {view}")
                lines.append("")

    # User Stories
    if stories:
        lines.append("## User Stories")
        lines.append("")
        for story in stories:
            title = story.get("title") or story.get("name") or "Untitled"
            lines.append(f"### {title}")
            if story.get("actor") and story.get("action"):
                lines.append(f"As a **{story['actor']}**, I want to **{story['action']}**")
                if story.get("benefit"):
                    lines.append(f"so that **{story['benefit']}**")
            lines.append("")

            # Acceptance criteria
            acs = story.get("acceptance_criteria", [])
            if acs:
                lines.append("**Acceptance Criteria:**")
                for ac in acs:
                    ac_text = ac.get("description", ac) if isinstance(ac, dict) else ac
                    lines.append(f"- {ac_text}")
                lines.append("")

    # Requirements
    func_reqs = requirements.get("functional_requirements", [])
    nfunc_reqs = requirements.get("non_functional_requirements", [])

    if func_reqs or nfunc_reqs:
        lines.append("## Requirements")
        lines.append("")

        if func_reqs:
            lines.append("### Functional Requirements")
            lines.append("")
            for req in func_reqs:
                req_id = req.get("id", "REQ")
                category = req.get("category", "General")
                requirement = req.get("requirement", "")
                lines.append(f"- **{req_id}** [{category}]: {requirement}")
            lines.append("")

        if nfunc_reqs:
            lines.append("### Non-Functional Requirements")
            lines.append("")
            for req in nfunc_reqs:
                req_id = req.get("id", "NFR")
                category = req.get("category", "General")
                requirement = req.get("requirement", "")
                lines.append(f"- **{req_id}** [{category}]: {requirement}")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("*Generated by Cahoots*")

    return "\n".join(lines)


# ============ FORMAT GENERATORS ============

def _generate_csv(data: Dict, flatten: bool = False) -> str:
    """Generate CSV output from data."""
    output = io.StringIO()

    rows = []
    for artifact_type, items in data.items():
        if artifact_type == "project":
            continue
        if not isinstance(items, list):
            continue

        for item in items:
            if isinstance(item, dict):
                row = {"_type": artifact_type, **item}

                if flatten:
                    flat_row = {}
                    for key, value in row.items():
                        if isinstance(value, (list, dict)):
                            flat_row[key] = json.dumps(value)
                        else:
                            flat_row[key] = value
                    row = flat_row

                rows.append(row)

    if not rows:
        return ""

    all_keys = set()
    for row in rows:
        all_keys.update(row.keys())

    writer = csv.DictWriter(output, fieldnames=sorted(all_keys))
    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue()


def _generate_markdown(data: Dict, task) -> str:
    """Generate Markdown document from data."""
    lines = []

    desc = task.description[:50] if task.description else "Export"
    lines.append(f"# Project Export: {desc}...")
    lines.append("")

    # Project info
    project = data.get("project", {})
    lines.append("## Project Information")
    lines.append(f"- **ID**: {project.get('id', 'N/A')}")
    lines.append(f"- **Description**: {project.get('description', 'N/A')}")
    lines.append("")

    # Epics
    if "epics" in data and data["epics"]:
        lines.append("## Epics")
        lines.append("")
        for epic in data["epics"]:
            lines.append(f"### {epic.get('title', epic.get('name', 'Untitled'))}")
            if epic.get("description"):
                lines.append(f"{epic['description']}")
            lines.append("")

    # Stories
    if "stories" in data and data["stories"]:
        lines.append("## User Stories")
        lines.append("")
        for story in data["stories"]:
            title = story.get("title") or story.get("name") or "Untitled"
            lines.append(f"### {title}")
            if story.get("actor") and story.get("action"):
                lines.append(f"As a **{story['actor']}**, I want to **{story['action']}**")
                if story.get("benefit"):
                    lines.append(f"so that **{story['benefit']}**")
            lines.append("")

    # Tasks
    if "tasks" in data and data["tasks"]:
        lines.append("## Implementation Tasks")
        lines.append("")
        for t in data["tasks"]:
            sp = f" ({t.get('story_points')} SP)" if t.get("story_points") else ""
            lines.append(f"- [ ] {t.get('description', 'Untitled')}{sp}")
        lines.append("")

    # Event Model
    if any(k in data for k in ["commands", "events", "read_models"]):
        lines.append("## Event Model")
        lines.append("")

        if "commands" in data and data["commands"]:
            lines.append("### Commands")
            for cmd in data["commands"]:
                name = cmd.get("name", "Untitled") if isinstance(cmd, dict) else cmd
                lines.append(f"- {name}")
            lines.append("")

        if "events" in data and data["events"]:
            lines.append("### Events")
            for evt in data["events"]:
                name = evt.get("name", "Untitled") if isinstance(evt, dict) else evt
                lines.append(f"- {name}")
            lines.append("")

        if "read_models" in data and data["read_models"]:
            lines.append("### Read Models")
            for rm in data["read_models"]:
                name = rm.get("name", "Untitled") if isinstance(rm, dict) else rm
                lines.append(f"- {name}")
            lines.append("")

    # Requirements
    if "functional_requirements" in data and data["functional_requirements"]:
        lines.append("## Functional Requirements")
        lines.append("")
        for req in data["functional_requirements"]:
            lines.append(f"- **{req.get('id', 'REQ')}** ({req.get('category', 'General')}): {req.get('requirement', '')}")
        lines.append("")

    if "non_functional_requirements" in data and data["non_functional_requirements"]:
        lines.append("## Non-Functional Requirements")
        lines.append("")
        for req in data["non_functional_requirements"]:
            lines.append(f"- **{req.get('id', 'NFR')}** ({req.get('category', 'General')}): {req.get('requirement', '')}")
        lines.append("")

    # Executive Summary
    if "executive_summary" in data:
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(data["executive_summary"])
        lines.append("")

    # Proposal
    if "proposal" in data:
        lines.append("---")
        lines.append("")
        lines.append(data["proposal"])

    lines.append("")
    lines.append("---")
    lines.append("*Exported from Cahoots*")

    return "\n".join(lines)


def _generate_zip_archive(
    data: Dict[str, Any],
    task,
    task_id: str,
    request: ExportRequest,
) -> Response:
    """Generate a ZIP archive with each artifact type in a separate file."""
    zip_buffer = io.BytesIO()

    # Map artifact keys to human-readable filenames
    artifact_filenames = {
        "project": "project-info",
        "epics": "epics",
        "stories": "user-stories",
        "tasks": "implementation-tasks",
        "commands": "event-model-commands",
        "events": "event-model-events",
        "read_models": "event-model-read-models",
        "functional_requirements": "functional-requirements",
        "non_functional_requirements": "non-functional-requirements",
        "acceptance_criteria": "acceptance-criteria",
        "gwt_scenarios": "gwt-scenarios",
        "executive_summary": "executive-summary",
        "proposal": "full-proposal",
    }

    # File extensions by format
    format_extensions = {
        "json": "json",
        "csv": "csv",
        "markdown": "md",
        "yaml": "yaml",
    }

    extension = format_extensions.get(request.format, "txt")

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for artifact_key, artifact_data in data.items():
            # Skip empty artifacts
            if artifact_data is None:
                continue
            if isinstance(artifact_data, list) and len(artifact_data) == 0:
                continue
            if isinstance(artifact_data, str) and len(artifact_data.strip()) == 0:
                continue

            # Get filename
            base_name = artifact_filenames.get(artifact_key, artifact_key)
            filename = f"{base_name}.{extension}"

            # Generate content based on format
            if request.format == "json":
                content = json.dumps(artifact_data, indent=2, default=str)

            elif request.format == "csv":
                # CSV only works well for list data
                if isinstance(artifact_data, list):
                    content = _generate_single_artifact_csv(artifact_data, request.flatten_hierarchy)
                elif isinstance(artifact_data, dict):
                    content = _generate_single_artifact_csv([artifact_data], request.flatten_hierarchy)
                else:
                    content = str(artifact_data)

            elif request.format == "markdown":
                content = _generate_single_artifact_markdown(artifact_key, artifact_data, task)

            elif request.format == "yaml":
                content = yaml.dump(artifact_data, default_flow_style=False, allow_unicode=True)

            else:
                content = str(artifact_data)

            # Add to ZIP
            zip_file.writestr(filename, content)

    # Return ZIP file
    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{task_id}-export.zip"',
        }
    )


def _generate_single_artifact_csv(items: List, flatten: bool = False) -> str:
    """Generate CSV for a single artifact type."""
    output = io.StringIO()

    if not items:
        return ""

    rows = []
    for item in items:
        if isinstance(item, dict):
            if flatten:
                flat_row = {}
                for key, value in item.items():
                    if isinstance(value, (list, dict)):
                        flat_row[key] = json.dumps(value)
                    else:
                        flat_row[key] = value
                rows.append(flat_row)
            else:
                rows.append(item)
        else:
            rows.append({"value": item})

    if not rows:
        return ""

    all_keys = set()
    for row in rows:
        all_keys.update(row.keys())

    writer = csv.DictWriter(output, fieldnames=sorted(all_keys))
    writer.writeheader()
    for row in rows:
        # Ensure all values are string-safe
        safe_row = {}
        for k, v in row.items():
            if isinstance(v, (list, dict)):
                safe_row[k] = json.dumps(v)
            else:
                safe_row[k] = v
        writer.writerow(safe_row)

    return output.getvalue()


def _generate_single_artifact_markdown(
    artifact_key: str,
    artifact_data: Any,
    task,
) -> str:
    """Generate Markdown for a single artifact type."""
    lines = []

    # Title mapping
    titles = {
        "project": "Project Information",
        "epics": "Epics",
        "stories": "User Stories",
        "tasks": "Implementation Tasks",
        "commands": "Commands (Event Model)",
        "events": "Events (Event Model)",
        "read_models": "Read Models (Event Model)",
        "functional_requirements": "Functional Requirements",
        "non_functional_requirements": "Non-Functional Requirements",
        "acceptance_criteria": "Acceptance Criteria",
        "gwt_scenarios": "GWT Scenarios",
        "executive_summary": "Executive Summary",
        "proposal": "Full Proposal",
    }

    title = titles.get(artifact_key, artifact_key.replace("_", " ").title())
    lines.append(f"# {title}")
    lines.append("")

    # Handle executive summary and proposal as strings
    if artifact_key in ["executive_summary", "proposal"]:
        lines.append(artifact_data if isinstance(artifact_data, str) else str(artifact_data))
        return "\n".join(lines)

    # Handle project info
    if artifact_key == "project" and isinstance(artifact_data, dict):
        lines.append(f"- **ID**: {artifact_data.get('id', 'N/A')}")
        lines.append(f"- **Description**: {artifact_data.get('description', 'N/A')}")
        lines.append("")
        return "\n".join(lines)

    # Handle list data
    if isinstance(artifact_data, list):
        for item in artifact_data:
            if artifact_key == "epics":
                lines.append(f"## {item.get('title', item.get('name', 'Untitled'))}")
                if item.get("description"):
                    lines.append(f"{item['description']}")
                lines.append("")

            elif artifact_key == "stories":
                title_val = item.get("title") or item.get("name") or "Untitled"
                lines.append(f"## {title_val}")
                if item.get("actor") and item.get("action"):
                    lines.append(f"As a **{item['actor']}**, I want to **{item['action']}**")
                    if item.get("benefit"):
                        lines.append(f"so that **{item['benefit']}**")
                lines.append("")

            elif artifact_key == "tasks":
                sp = f" ({item.get('story_points')} SP)" if item.get("story_points") else ""
                lines.append(f"- [ ] {item.get('description', 'Untitled')}{sp}")

            elif artifact_key in ["commands", "events", "read_models"]:
                name = item.get("name", "Untitled") if isinstance(item, dict) else item
                desc = item.get("description", "") if isinstance(item, dict) else ""
                if desc:
                    lines.append(f"- **{name}**: {desc}")
                else:
                    lines.append(f"- {name}")

            elif artifact_key in ["functional_requirements", "non_functional_requirements"]:
                req_id = item.get("id", "REQ")
                category = item.get("category", "General")
                requirement = item.get("requirement", "")
                lines.append(f"- **{req_id}** [{category}]: {requirement}")

            elif artifact_key == "acceptance_criteria":
                story_title = item.get("story_title", "")
                desc = item.get("description", item) if isinstance(item, dict) else item
                prefix = f"[{story_title}] " if story_title else ""
                lines.append(f"- {prefix}{desc}")

            elif artifact_key == "gwt_scenarios":
                story_title = item.get("story_title", "")
                if story_title:
                    lines.append(f"### {story_title}")
                lines.append(f"- **Given**: {item.get('given', '')}")
                lines.append(f"- **When**: {item.get('when', '')}")
                lines.append(f"- **Then**: {item.get('then', '')}")
                lines.append("")

            else:
                # Generic list item
                if isinstance(item, dict):
                    lines.append(f"- {json.dumps(item)}")
                else:
                    lines.append(f"- {item}")

        lines.append("")

    lines.append("")
    lines.append("---")
    lines.append("*Exported from Cahoots*")

    return "\n".join(lines)


def _generate_llm_prompt(
    data: Dict[str, Any],
    task,
    template_id: str,
    custom_instructions: Optional[str] = None,
) -> str:
    """Generate LLM prompt from data using selected template."""
    template = PROMPT_TEMPLATE_CONTENTS.get(template_id, PROMPT_TEMPLATE_CONTENTS["design_review"])

    # Format artifacts as readable content
    artifacts_lines = []

    if "epics" in data and data["epics"]:
        artifacts_lines.append("### Epics")
        for epic in data["epics"]:
            artifacts_lines.append(f"- **{epic.get('title', 'Untitled')}**: {epic.get('description', '')}")
        artifacts_lines.append("")

    if "stories" in data and data["stories"]:
        artifacts_lines.append("### User Stories")
        for story in data["stories"]:
            title = story.get("title") or story.get("name") or "Untitled"
            if story.get("actor") and story.get("action"):
                artifacts_lines.append(f"- **{title}**: As a {story['actor']}, I want to {story['action']}")
            else:
                artifacts_lines.append(f"- **{title}**")
        artifacts_lines.append("")

    if "tasks" in data and data["tasks"]:
        artifacts_lines.append("### Implementation Tasks")
        for t in data["tasks"]:
            sp = f" ({t.get('story_points')} SP)" if t.get("story_points") else ""
            artifacts_lines.append(f"- {t.get('description', 'Untitled')}{sp}")
            if t.get("implementation_details"):
                details = t['implementation_details'][:200]
                artifacts_lines.append(f"  Implementation: {details}...")
        artifacts_lines.append("")

    if "commands" in data and data["commands"]:
        artifacts_lines.append("### Commands (Event Model)")
        for cmd in data["commands"]:
            name = cmd.get("name", "Untitled") if isinstance(cmd, dict) else cmd
            artifacts_lines.append(f"- {name}")
        artifacts_lines.append("")

    if "events" in data and data["events"]:
        artifacts_lines.append("### Events (Event Model)")
        for evt in data["events"]:
            name = evt.get("name", "Untitled") if isinstance(evt, dict) else evt
            artifacts_lines.append(f"- {name}")
        artifacts_lines.append("")

    if "read_models" in data and data["read_models"]:
        artifacts_lines.append("### Read Models (Event Model)")
        for rm in data["read_models"]:
            name = rm.get("name", "Untitled") if isinstance(rm, dict) else rm
            artifacts_lines.append(f"- {name}")
        artifacts_lines.append("")

    if "functional_requirements" in data and data["functional_requirements"]:
        artifacts_lines.append("### Functional Requirements")
        for req in data["functional_requirements"]:
            artifacts_lines.append(f"- [{req.get('category', 'General')}] {req.get('requirement', '')}")
        artifacts_lines.append("")

    if "non_functional_requirements" in data and data["non_functional_requirements"]:
        artifacts_lines.append("### Non-Functional Requirements")
        for req in data["non_functional_requirements"]:
            artifacts_lines.append(f"- [{req.get('category', 'General')}] {req.get('requirement', '')}")
        artifacts_lines.append("")

    if "acceptance_criteria" in data and data["acceptance_criteria"]:
        artifacts_lines.append("### Acceptance Criteria")
        for ac in data["acceptance_criteria"]:
            desc = ac.get("description", ac) if isinstance(ac, dict) else ac
            artifacts_lines.append(f"- {desc}")
        artifacts_lines.append("")

    if "gwt_scenarios" in data and data["gwt_scenarios"]:
        artifacts_lines.append("### GWT Scenarios")
        for gwt in data["gwt_scenarios"]:
            artifacts_lines.append(f"- Given: {gwt.get('given', '')}")
            artifacts_lines.append(f"  When: {gwt.get('when', '')}")
            artifacts_lines.append(f"  Then: {gwt.get('then', '')}")
        artifacts_lines.append("")

    artifacts_content = "\n".join(artifacts_lines)

    # Fill in template
    prompt = template.format(
        project_description=task.description or "No description provided",
        artifacts_content=artifacts_content,
        custom_instructions=custom_instructions or "",
    )

    return prompt
