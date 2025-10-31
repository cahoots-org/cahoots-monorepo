"""Slice Associator Service

Associates implementation tasks with Event Modeling slices (chapters).
This enables batching tasks by slice for code generation.
"""

from typing import Dict, Any, List, Optional
from app.models import Task
from app.analyzer.llm_client import LLMClient


class SliceAssociator:
    """Associates tasks with slices from the event model."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def associate_tasks_with_slices(
        self,
        tasks: List[Task],
        event_model: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Associate tasks with slices using LLM-based matching.

        Args:
            tasks: List of tasks to associate
            event_model: Event model with chapters and slices

        Returns:
            Dictionary mapping slice_key -> [task_ids]
            slice_key format: "{chapter_name}::{slice_type}::{slice_identifier}"
        """
        chapters = event_model.get("chapters", [])
        if not chapters:
            print("[SliceAssociator] No chapters found in event model")
            return {}

        # Build slice catalog
        slices = []
        for chapter in chapters:
            chapter_name = chapter.get("name", "")
            for slice_data in chapter.get("slices", []):
                slice_type = slice_data.get("type", "")

                # Create slice identifier
                if slice_type == "state_change":
                    identifier = slice_data.get("command", "")
                elif slice_type == "state_view":
                    identifier = slice_data.get("read_model", "")
                elif slice_type == "automation":
                    identifier = slice_data.get("automation_name", "")
                else:
                    identifier = ""

                if identifier:
                    slices.append({
                        "chapter": chapter_name,
                        "type": slice_type,
                        "identifier": identifier,
                        "slice_key": f"{chapter_name}::{slice_type}::{identifier}",
                        "data": slice_data
                    })

        print(f"[SliceAssociator] Found {len(slices)} slices across {len(chapters)} chapters")

        # Use LLM to batch-associate all tasks at once
        task_slice_map = await self._llm_batch_associate(tasks, slices)

        print(f"[SliceAssociator] Associated {sum(len(task_ids) for task_ids in task_slice_map.values())} tasks with {len(task_slice_map)} slices")

        return task_slice_map

    async def _llm_batch_associate(
        self,
        tasks: List[Task],
        slices: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Use LLM to associate all tasks with slices in a single call.

        This is much more accurate than keyword matching.
        """
        import json

        # Format tasks for LLM
        task_list = []
        for i, task in enumerate(tasks):
            if task.is_atomic and task.implementation_details:
                task_list.append({
                    "index": i,
                    "id": task.id,
                    "description": task.description,
                    "implementation": task.implementation_details[:200]  # Truncate for token efficiency
                })

        # Format slices for LLM
        slice_list = []
        for slice_info in slices:
            slice_data = slice_info["data"]
            slice_desc = {
                "slice_key": slice_info["slice_key"],
                "type": slice_info["type"],
                "identifier": slice_info["identifier"]
            }

            if slice_info["type"] == "state_change":
                slice_desc["command"] = slice_data.get("command")
                slice_desc["events"] = slice_data.get("events", [])
            elif slice_info["type"] == "state_view":
                slice_desc["read_model"] = slice_data.get("read_model")
                slice_desc["source_events"] = slice_data.get("source_events", [])

            slice_list.append(slice_desc)

        prompt = f"""Associate implementation tasks with Event Modeling slices.

SLICES:
{json.dumps(slice_list, indent=2)}

TASKS:
{json.dumps(task_list, indent=2)}

For each task, determine which slice it belongs to based on what it implements:

- **state_change** slices (Command → Events): Tasks that implement commands, handle command parameters, trigger events, validate inputs, etc.
- **state_view** slices (Events → Read Model): Tasks that implement read models, query data, display UI components, aggregate event data, etc.
- **automation** slices: Tasks that implement background processes, scheduled jobs, event handlers, etc.

Examples:
- "Create TODO item model" → Likely belongs to CreateTodoItem (state_change) - models are used by commands
- "Implement TODO creation endpoint" → CreateTodoItem (state_change) - endpoints handle commands
- "Build TODO list display" → TodoItemList (state_view) - displays read model data
- "Connect list to API" → TodoItemList (state_view) - fetches read model data

Return JSON mapping task IDs to slice_keys:
{{
  "task_id_1": "Chapter::type::identifier",
  "task_id_2": "Chapter::type::identifier",
  ...
}}

If a task doesn't clearly belong to any slice, omit it.

Return ONLY valid JSON, no explanation."""

        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.1
            )

            # Parse response
            if isinstance(response, dict) and "choices" in response:
                content = response["choices"][0]["message"]["content"]
            else:
                content = response

            # Extract JSON
            data = self.llm._parse_json(content)

            # Build reverse map: slice_key -> [task_ids]
            task_slice_map = {}
            for task_id, slice_key in data.items():
                if slice_key not in task_slice_map:
                    task_slice_map[slice_key] = []
                task_slice_map[slice_key].append(task_id)

            return task_slice_map

        except Exception as e:
            print(f"[SliceAssociator] LLM association failed: {e}, falling back to keyword matching")
            # Fallback to keyword matching
            task_slice_map = {}
            for task in tasks:
                if task.is_atomic and task.implementation_details:
                    best_slice = self._match_task_to_slice_keywords(task, slices)
                    if best_slice:
                        slice_key = best_slice["slice_key"]
                        if slice_key not in task_slice_map:
                            task_slice_map[slice_key] = []
                        task_slice_map[slice_key].append(task.id)
            return task_slice_map

    def _match_task_to_slice_keywords(
        self,
        task: Task,
        slices: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Match task to slice using keyword matching.

        This is a fast, deterministic approach that works well for most cases.
        """
        task_text = f"{task.description} {task.implementation_details or ''}".lower()

        best_slice = None
        best_score = 0

        for slice_info in slices:
            score = 0
            slice_data = slice_info["data"]

            # Match on command name (state_change slices)
            if slice_info["type"] == "state_change":
                command = slice_data.get("command", "")
                if command.lower() in task_text:
                    score += 10

                # Match on events
                for event in slice_data.get("events", []):
                    if event.lower() in task_text:
                        score += 5

            # Match on read model name (state_view slices)
            elif slice_info["type"] == "state_view":
                read_model = slice_data.get("read_model", "")
                if read_model.lower() in task_text:
                    score += 10

                # Match on source events
                for event in slice_data.get("source_events", []):
                    if event.lower() in task_text:
                        score += 3

            # Match on automation name
            elif slice_info["type"] == "automation":
                automation_name = slice_data.get("automation_name", "")
                if automation_name.lower() in task_text:
                    score += 10

            # Chapter name matching (weaker signal)
            chapter = slice_info["chapter"]
            if chapter.lower() in task_text:
                score += 2

            if score > best_score:
                best_score = score
                best_slice = slice_info

        # Require minimum score threshold
        if best_score < 3:
            return None

        return best_slice

    async def update_task_metadata_with_slice(
        self,
        task: Task,
        slice_info: Dict[str, Any]
    ) -> None:
        """
        Update task metadata with slice information.

        Args:
            task: Task to update
            slice_info: Slice information from association
        """
        if not isinstance(task.metadata, dict):
            task.metadata = {}

        task.metadata["slice"] = {
            "chapter": slice_info["chapter"],
            "slice_type": slice_info["type"],
            "identifier": slice_info["identifier"],
            "slice_key": slice_info["slice_key"]
        }

    async def associate_and_update_tasks(
        self,
        tasks: List[Task],
        event_model: Dict[str, Any],
        storage
    ) -> Dict[str, List[str]]:
        """
        Associate tasks with slices and update task metadata.

        This is the main entry point for integrating slice association.

        Args:
            tasks: Tasks to associate
            event_model: Event model with chapters/slices
            storage: Task storage for saving updates

        Returns:
            Dictionary mapping slice_key -> [task_ids]
        """
        # Get associations
        task_slice_map = await self.associate_tasks_with_slices(tasks, event_model)

        # Build reverse map: task_id -> slice_info
        task_to_slice = {}
        chapters = event_model.get("chapters", [])

        for chapter in chapters:
            chapter_name = chapter.get("name", "")
            for slice_data in chapter.get("slices", []):
                slice_type = slice_data.get("type", "")

                if slice_type == "state_change":
                    identifier = slice_data.get("command", "")
                elif slice_type == "state_view":
                    identifier = slice_data.get("read_model", "")
                elif slice_type == "automation":
                    identifier = slice_data.get("automation_name", "")
                else:
                    continue

                if not identifier:
                    continue

                slice_key = f"{chapter_name}::{slice_type}::{identifier}"
                slice_info = {
                    "chapter": chapter_name,
                    "type": slice_type,
                    "identifier": identifier,
                    "slice_key": slice_key,
                    "data": slice_data
                }

                # Map all tasks in this slice
                for task_id in task_slice_map.get(slice_key, []):
                    task_to_slice[task_id] = slice_info

        # Update task metadata
        updated_count = 0
        for task in tasks:
            if task.id in task_to_slice:
                await self.update_task_metadata_with_slice(task, task_to_slice[task.id])
                await storage.save_task(task)
                updated_count += 1

        print(f"[SliceAssociator] Updated {updated_count} tasks with slice metadata")

        return task_slice_map
