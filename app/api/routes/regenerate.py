"""API endpoint to regenerate event model markdown for existing tasks"""

from fastapi import APIRouter, HTTPException, Depends
from app.storage.task_storage import TaskStorage
from app.api.dependencies import get_task_storage
from app.analyzer.event_model_markdown_generator import EventModelMarkdownGenerator
from app.analyzer.event_extractor import DomainEvent, EventType

router = APIRouter()


@router.post("/tasks/{task_id}/regenerate-event-model")
async def regenerate_event_model(
    task_id: str,
    storage: TaskStorage = Depends(get_task_storage)
):
    """Regenerate event model markdown for a task that already has event data"""

    # Get task
    task = await storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if task has event model data
    if not task.metadata:
        raise HTTPException(status_code=400, detail="Task has no metadata")

    has_events = 'extracted_events' in task.metadata
    has_commands = 'commands' in task.metadata
    has_read_models = 'read_models' in task.metadata

    if not (has_events or has_commands or has_read_models):
        raise HTTPException(status_code=400, detail="Task has no event model data")

    # Convert stored events back to DomainEvent objects
    events = []
    for event_data in task.metadata.get('extracted_events', []):
        event = DomainEvent(
            name=event_data['name'],
            event_type=EventType(event_data['event_type']),
            description=event_data['description'],
            source_task_id=event_data.get('source_task_id', ''),
            actor=event_data.get('actor'),
            affected_entity=event_data.get('affected_entity'),
            triggers=event_data.get('triggers', []),
            metadata=event_data.get('metadata', {})
        )
        events.append(event)

    analysis = {
        'events': events,
        'commands': task.metadata.get('commands', []),
        'read_models': task.metadata.get('read_models', []),
        'user_interactions': task.metadata.get('user_interactions', []),
        'automations': task.metadata.get('automations', [])
    }

    # Generate markdown
    generator = EventModelMarkdownGenerator()
    markdown = generator.generate(analysis, task.description)

    # Update task with markdown
    task.metadata['event_model_markdown'] = markdown
    await storage.save_task(task)

    return {
        "message": "Event model markdown regenerated successfully",
        "task_id": task_id,
        "markdown_length": len(markdown),
        "events_count": len(events),
        "commands_count": len(analysis['commands']),
        "read_models_count": len(analysis['read_models'])
    }
