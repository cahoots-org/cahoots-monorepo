"""Task storage operations using Redis."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from app.models import Task, TaskStatus, TaskTree, Epic, UserStory
from .redis_client import RedisClient


class TaskStorage:
    """Storage layer for task operations."""

    def __init__(self, redis_client: RedisClient):
        """Initialize task storage.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.task_prefix = "task:"
        self.tree_prefix = "tree:"
        self.user_tasks_prefix = "user_tasks:"
        self.status_index_prefix = "status:"
        self.epic_prefix = "epic:"
        self.story_prefix = "story:"
        self.root_epics_prefix = "root_epics:"
        self.epic_stories_prefix = "epic_stories:"

    def _task_key(self, task_id: str) -> str:
        """Generate Redis key for a task."""
        return f"{self.task_prefix}{task_id}"

    def _tree_key(self, root_id: str) -> str:
        """Generate Redis key for a task tree."""
        return f"{self.tree_prefix}{root_id}"

    def _user_tasks_key(self, user_id: str) -> str:
        """Generate Redis key for user's tasks."""
        return f"{self.user_tasks_prefix}{user_id}"

    def _status_index_key(self, status: TaskStatus) -> str:
        """Generate Redis key for status index."""
        return f"{self.status_index_prefix}{status.value}"

    async def save_task(self, task: Task, expire: Optional[int] = None, skip_indices: bool = False) -> bool:
        """Save a task to Redis.

        Args:
            task: Task to save
            expire: Optional expiration in seconds
            skip_indices: Skip updating indices (used internally to prevent recursion)

        Returns:
            True if successful
        """
        task.updated_at = datetime.now(timezone.utc)
        key = self._task_key(task.id)

        # Save the task data
        success = await self.redis.set(key, task.to_redis_dict(), expire)

        if success and not skip_indices:
            # Update indices
            await self._update_indices(task)

        return success

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        key = self._task_key(task_id)
        data = await self.redis.get(key)

        if data:
            return Task.from_redis_dict(data)
        return None

    async def get_tasks(self, task_ids: List[str]) -> List[Optional[Task]]:
        """Get multiple tasks by IDs.

        Args:
            task_ids: List of task IDs

        Returns:
            List of tasks (None for missing tasks)
        """
        if not task_ids:
            return []

        keys = [self._task_key(task_id) for task_id in task_ids]
        values = await self.redis.mget(keys)

        result = []
        for value in values:
            if value:
                result.append(Task.from_redis_dict(value))
            else:
                result.append(None)

        return result

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task's fields.

        Args:
            task_id: Task ID
            updates: Dictionary of field updates

        Returns:
            True if successful
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        # Apply updates
        for field, value in updates.items():
            if hasattr(task, field):
                setattr(task, field, value)

        # Save updated task
        return await self.save_task(task)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if task was deleted
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        key = self._task_key(task_id)

        # Remove from indices first
        await self._remove_from_indices(task)

        # Delete the task
        deleted = await self.redis.delete(key)
        return deleted > 0

    async def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status.

        Args:
            status: Task status

        Returns:
            List of tasks
        """
        key = self._status_index_key(status)
        task_ids = await self.redis.smembers(key)

        if not task_ids:
            return []

        tasks = await self.get_tasks(list(task_ids))
        return [task for task in tasks if task is not None]

    async def get_user_tasks(
        self,
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """Get tasks for a specific user.

        Args:
            user_id: User ID
            limit: Maximum number of tasks to return
            offset: Offset for pagination

        Returns:
            List of tasks
        """
        key = self._user_tasks_key(user_id)

        # If no limit, get all tasks
        if limit is None:
            task_ids = await self.redis.lrange(key, 0, -1)
        else:
            task_ids = await self.redis.lrange(key, offset, offset + limit - 1)

        if not task_ids:
            return []

        tasks = await self.get_tasks(task_ids)
        return [task for task in tasks if task is not None]

    async def get_children(self, parent_id: str) -> List[Task]:
        """Get all children of a task.

        Args:
            parent_id: Parent task ID

        Returns:
            List of child tasks
        """
        parent = await self.get_task(parent_id)
        if not parent or not parent.subtasks:
            return []

        tasks = await self.get_tasks(parent.subtasks)
        return [task for task in tasks if task is not None]

    async def count_all_descendants(self, task_id: str) -> int:
        """Count all descendants of a task recursively.

        Args:
            task_id: Task ID to count descendants for

        Returns:
            Total number of descendants (children, grandchildren, etc.)
        """
        task = await self.get_task(task_id)
        if not task or not task.subtasks:
            return 0

        # Count immediate children
        count = len(task.subtasks)

        # Recursively count descendants of each child
        for child_id in task.subtasks:
            count += await self.count_all_descendants(child_id)

        return count

    async def save_task_tree(self, tree: TaskTree, expire: Optional[int] = None) -> bool:
        """Save an entire task tree.

        Args:
            tree: TaskTree to save
            expire: Optional expiration in seconds

        Returns:
            True if successful
        """
        # Save all tasks in the tree
        for task in tree.tasks.values():
            success = await self.save_task(task, expire)
            if not success:
                return False

        # Save tree metadata
        tree_data = {
            "root_id": tree.root.id,
            "task_ids": list(tree.tasks.keys()),
            "depth_map": tree.depth_map,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        key = self._tree_key(tree.root.id)
        return await self.redis.set(key, tree_data, expire)

    async def get_task_tree(self, root_id: str) -> Optional[TaskTree]:
        """Get an entire task tree by root ID.

        Args:
            root_id: Root task ID

        Returns:
            TaskTree or None if not found
        """
        # Get tree metadata
        key = self._tree_key(root_id)
        tree_data = await self.redis.get(key)

        if not tree_data:
            # Try to reconstruct from root task
            root = await self.get_task(root_id)
            if not root:
                return None

            tree = TaskTree(root=root)
            await self._reconstruct_tree(tree, root_id)
            return tree

        # Load all tasks
        task_ids = tree_data.get("task_ids", [])
        tasks = await self.get_tasks(task_ids)

        # Build the tree
        root = None
        task_dict = {}

        for task in tasks:
            if task:
                task_dict[task.id] = task
                if task.id == root_id:
                    root = task

        if not root:
            return None

        tree = TaskTree(root=root, tasks=task_dict)
        tree.depth_map = tree_data.get("depth_map", {})

        return tree

    async def _reconstruct_tree(self, tree: TaskTree, task_id: str) -> None:
        """Recursively reconstruct a task tree.

        Args:
            tree: TaskTree to populate
            task_id: Current task ID
        """
        task = await self.get_task(task_id)
        if not task:
            return

        tree.add_task(task)

        # Recursively add children
        for child_id in task.subtasks:
            await self._reconstruct_tree(tree, child_id)

    async def _update_indices(self, task: Task) -> None:
        """Update Redis indices for a task.

        Args:
            task: Task to index
        """
        # Status index
        status_key = self._status_index_key(task.status)
        await self.redis.sadd(status_key, task.id)

        # User index - only add if not already present to avoid duplicates
        if task.user_id:
            user_key = self._user_tasks_key(task.user_id)
            # Only add if not already in the list (prevent duplicates)
            existing_ids = await self.redis.lrange(user_key, 0, -1)
            if task.id not in existing_ids:
                await self.redis.lpush(user_key, task.id)

        # Parent-child relationship
        if task.parent_id:
            parent = await self.get_task(task.parent_id)
            if parent and task.id not in parent.subtasks:
                parent.subtasks.append(task.id)
                # Use skip_indices to prevent infinite recursion
                await self.save_task(parent, skip_indices=True)

    async def _remove_from_indices(self, task: Task) -> None:
        """Remove a task from Redis indices.

        Args:
            task: Task to remove from indices
        """
        # Remove from status index
        for status in TaskStatus:
            status_key = self._status_index_key(status)
            await self.redis.srem(status_key, task.id)

        # Remove from parent's subtasks
        if task.parent_id:
            parent = await self.get_task(task.parent_id)
            if parent and task.id in parent.subtasks:
                parent.subtasks.remove(task.id)
                # Use skip_indices to prevent infinite recursion
                await self.save_task(parent, skip_indices=True)

    async def count_tasks_by_status(self) -> Dict[TaskStatus, int]:
        """Count tasks grouped by status.

        Returns:
            Dictionary mapping status to count
        """
        counts = {}
        for status in TaskStatus:
            key = self._status_index_key(status)
            count = await self.redis.scard(key)
            counts[status] = count
        return counts

    async def search_tasks(
        self,
        query: str,
        limit: int = 50
    ) -> List[Task]:
        """Search for tasks by description.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching tasks
        """
        # Simple implementation - get all task keys and filter
        # In production, this should use a proper search index
        pattern = f"{self.task_prefix}*"
        keys = await self.redis.keys(pattern)

        if not keys:
            return []

        # Get task IDs from keys
        task_ids = [key.replace(self.task_prefix, "") for key in keys[:limit * 2]]
        tasks = await self.get_tasks(task_ids)

        # Filter by query
        query_lower = query.lower()
        matching_tasks = []

        for task in tasks:
            if task and query_lower in task.description.lower():
                matching_tasks.append(task)
                if len(matching_tasks) >= limit:
                    break

        return matching_tasks

    # Epic and Story storage methods

    def _epic_key(self, epic_id: str) -> str:
        """Generate Redis key for an epic."""
        return f"{self.epic_prefix}{epic_id}"

    def _story_key(self, story_id: str) -> str:
        """Generate Redis key for a story."""
        return f"{self.story_prefix}{story_id}"

    async def save_epic(self, epic: Epic) -> bool:
        """Save an epic to Redis.

        Args:
            epic: Epic to save

        Returns:
            True if successful
        """
        try:
            # Save epic data
            key = self._epic_key(epic.id)
            await self.redis.set(key, epic.to_dict())

            # Add to root task's epic index
            if epic.root_task_id:
                root_epics_key = f"{self.root_epics_prefix}{epic.root_task_id}"
                await self.redis.sadd(root_epics_key, epic.id)

            return True
        except Exception as e:
            print(f"Error saving epic {epic.id}: {e}")
            return False

    async def get_epic(self, epic_id: str) -> Optional[Epic]:
        """Get an epic from Redis.

        Args:
            epic_id: Epic ID

        Returns:
            Epic if found, None otherwise
        """
        try:
            key = self._epic_key(epic_id)
            data = await self.redis.get(key)
            if data:
                return Epic.from_dict(data)
            return None
        except Exception as e:
            print(f"Error getting epic {epic_id}: {e}")
            return None

    async def save_story(self, story: UserStory) -> bool:
        """Save a user story to Redis.

        Args:
            story: Story to save

        Returns:
            True if successful
        """
        try:
            # Save story data
            key = self._story_key(story.id)
            await self.redis.set(key, story.to_dict())

            # Add to epic's story index
            if story.epic_id:
                epic_stories_key = f"{self.epic_stories_prefix}{story.epic_id}"
                await self.redis.sadd(epic_stories_key, story.id)

            return True
        except Exception as e:
            print(f"Error saving story {story.id}: {e}")
            return False

    async def get_story(self, story_id: str) -> Optional[UserStory]:
        """Get a user story from Redis.

        Args:
            story_id: Story ID

        Returns:
            Story if found, None otherwise
        """
        try:
            key = self._story_key(story_id)
            data = await self.redis.get(key)
            if data:
                return UserStory.from_dict(data)
            return None
        except Exception as e:
            print(f"Error getting story {story_id}: {e}")
            return None

    async def get_epics_for_root_task(self, root_task_id: str) -> List[Epic]:
        """Get all epics for a root task.

        Args:
            root_task_id: Root task ID

        Returns:
            List of epics
        """
        try:
            root_epics_key = f"{self.root_epics_prefix}{root_task_id}"
            epic_ids = await self.redis.smembers(root_epics_key)

            epics = []
            if epic_ids:
                for epic_id in epic_ids:
                    epic = await self.get_epic(epic_id)
                    if epic:
                        epics.append(epic)

            return epics
        except Exception as e:
            print(f"Error getting epics for root task {root_task_id}: {e}")
            return []

    async def get_stories_for_epic(self, epic_id: str) -> List[UserStory]:
        """Get all stories for an epic.

        Args:
            epic_id: Epic ID

        Returns:
            List of stories
        """
        try:
            epic_stories_key = f"{self.epic_stories_prefix}{epic_id}"
            story_ids = await self.redis.smembers(epic_stories_key)

            stories = []
            if story_ids:
                for story_id in story_ids:
                    story = await self.get_story(story_id)
                    if story:
                        stories.append(story)

            return stories
        except Exception as e:
            print(f"Error getting stories for epic {epic_id}: {e}")
            return []