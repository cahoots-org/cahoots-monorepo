"""
Task Dependency Graph

Builds and manages dependencies between tasks for proper execution order.
Tasks can depend on other tasks that must complete before they can start.

Unlike slice-based generation which derives dependencies from events,
task dependencies are explicit - specified during task decomposition.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from collections import defaultdict


@dataclass
class TaskNode:
    """A node in the task dependency graph."""
    task_id: str
    description: str
    implementation_details: Optional[str] = None
    story_points: Optional[int] = None

    # Story/epic context
    story_id: Optional[str] = None
    epic_id: Optional[str] = None

    # Dependencies (explicit)
    dependencies: List[str] = field(default_factory=list)  # task_ids this depends on
    dependents: List[str] = field(default_factory=list)    # task_ids that depend on this

    # Execution level (0 = no dependencies)
    level: int = 0

    # Keywords extracted for context matching
    keywords: List[str] = field(default_factory=list)


class TaskDependencyGraph:
    """
    Manages task dependencies and execution order.

    Builds a DAG from task dependencies and provides:
    - Topological sort for execution order
    - Level grouping for parallel execution
    - Keyword extraction for context matching
    """

    def __init__(self):
        self.nodes: Dict[str, TaskNode] = {}
        self.levels: List[List[str]] = []
        self.execution_order: List[str] = []

    @classmethod
    def from_tasks(cls, tasks: List[Dict]) -> "TaskDependencyGraph":
        """
        Build dependency graph from a list of tasks.

        Task structure:
        {
            "id": "task-uuid",
            "description": "Task description",
            "implementation_details": "How to implement",
            "story_points": 3,
            "depends_on": ["other-task-id"],
            "story_id": "story-uuid",
            "epic_id": "epic-uuid"
        }
        """
        graph = cls()

        # First pass: Create all nodes
        for task in tasks:
            node = graph._create_node(task)
            if node:
                graph.nodes[node.task_id] = node

        # Second pass: Build dependency relationships (reverse links)
        graph._build_dependents()

        # Third pass: Calculate levels and execution order
        graph._calculate_levels()
        graph._topological_sort()

        return graph

    def _create_node(self, task: Dict) -> Optional[TaskNode]:
        """Create a TaskNode from a task dictionary."""
        task_id = task.get("id") or task.get("task_id")
        if not task_id:
            return None

        description = task.get("description", "")
        implementation_details = task.get("implementation_details")

        # Extract keywords from description and implementation details
        keywords = self._extract_keywords(description, implementation_details)

        return TaskNode(
            task_id=task_id,
            description=description,
            implementation_details=implementation_details,
            story_points=task.get("story_points"),
            story_id=task.get("story_id"),
            epic_id=task.get("epic_id"),
            dependencies=task.get("depends_on", []),
            keywords=keywords
        )

    def _extract_keywords(self, description: str, implementation_details: Optional[str]) -> List[str]:
        """Extract keywords from task description and implementation details."""
        text = f"{description} {implementation_details or ''}"

        # Common technical keywords to look for
        tech_patterns = [
            "api", "endpoint", "route", "handler", "controller",
            "model", "schema", "database", "migration", "query",
            "service", "repository", "client", "provider",
            "component", "view", "page", "form", "modal",
            "test", "spec", "fixture", "mock",
            "auth", "authentication", "authorization", "jwt", "oauth",
            "event", "command", "aggregate", "projection",
            "websocket", "socket", "stream", "queue", "message",
            "cache", "redis", "storage", "file",
            "validation", "error", "exception", "logging"
        ]

        text_lower = text.lower()
        keywords = []

        for pattern in tech_patterns:
            if pattern in text_lower:
                keywords.append(pattern)

        # Also extract file paths mentioned (e.g., src/api/routes.py)
        import re
        file_patterns = re.findall(r'[\w/]+\.\w+', text)
        keywords.extend(file_patterns[:5])  # Limit to 5 file references

        return keywords

    def _build_dependents(self) -> None:
        """Build reverse dependency relationships (who depends on this)."""
        for task_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if dep_node and task_id not in dep_node.dependents:
                    dep_node.dependents.append(task_id)

    def _calculate_levels(self) -> None:
        """Calculate execution levels (0 = no dependencies)."""
        processed: Set[str] = set()
        current_level: List[str] = []

        # Find all tasks with no dependencies or only external dependencies
        for task_id, node in self.nodes.items():
            # Check if all dependencies are satisfied (either in graph or external)
            deps_in_graph = [d for d in node.dependencies if d in self.nodes]
            if not deps_in_graph:
                node.level = 0
                current_level.append(task_id)
                processed.add(task_id)

        self.levels = [current_level] if current_level else []

        # Process remaining levels
        max_iterations = len(self.nodes) + 1  # Prevent infinite loops
        iteration = 0

        while len(processed) < len(self.nodes) and iteration < max_iterations:
            iteration += 1
            next_level: List[str] = []
            level_num = len(self.levels)

            for task_id, node in self.nodes.items():
                if task_id in processed:
                    continue

                # Check if all dependencies in this graph are processed
                deps_in_graph = [d for d in node.dependencies if d in self.nodes]
                if all(dep in processed for dep in deps_in_graph):
                    node.level = level_num
                    next_level.append(task_id)
                    processed.add(task_id)

            if not next_level and len(processed) < len(self.nodes):
                # Circular dependency detected - add remaining at current level
                for task_id in self.nodes:
                    if task_id not in processed:
                        self.nodes[task_id].level = level_num
                        next_level.append(task_id)
                        processed.add(task_id)

            if next_level:
                self.levels.append(next_level)

    def _topological_sort(self) -> None:
        """Generate topological sort for execution order."""
        self.execution_order = []
        for level in self.levels:
            # Within each level, sort by story points (smaller first) for quick wins
            sorted_level = sorted(
                level,
                key=lambda tid: self.nodes[tid].story_points or 99
            )
            self.execution_order.extend(sorted_level)

    def get_tasks_at_level(self, level: int) -> List[TaskNode]:
        """Get all tasks at a given execution level."""
        if level >= len(self.levels):
            return []
        return [self.nodes[tid] for tid in self.levels[level]]

    def get_ready_tasks(self, completed: Set[str]) -> List[TaskNode]:
        """Get tasks that are ready to execute (all dependencies completed)."""
        ready = []
        for task_id, node in self.nodes.items():
            if task_id in completed:
                continue
            # Only check dependencies that are in this graph
            deps_in_graph = [d for d in node.dependencies if d in self.nodes]
            if all(dep in completed for dep in deps_in_graph):
                ready.append(node)
        return ready

    def get_blocked_tasks(self, failed: Set[str]) -> List[str]:
        """Get tasks that are blocked due to failed dependencies."""
        blocked = []

        def check_blocked(task_id: str, checked: Set[str]) -> bool:
            if task_id in checked:
                return task_id in blocked
            checked.add(task_id)

            node = self.nodes.get(task_id)
            if not node:
                return False

            # Check if any dependency (in graph) failed or is blocked
            for dep in node.dependencies:
                if dep in self.nodes:  # Only check deps in this graph
                    if dep in failed or check_blocked(dep, checked):
                        if task_id not in blocked:
                            blocked.append(task_id)
                        return True

            return False

        for task_id in self.nodes:
            check_blocked(task_id, set())

        return blocked

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """Get a task node by ID."""
        return self.nodes.get(task_id)

    def get_all_task_ids(self) -> List[str]:
        """Get all task IDs in execution order."""
        return self.execution_order.copy()

    def get_context_for_task(self, task_id: str, completed_tasks: Dict[str, Dict]) -> Dict:
        """
        Get relevant context for a task based on its keywords and dependencies.

        Args:
            task_id: The task to get context for
            completed_tasks: Dict of task_id -> {files, code, etc} from completed tasks

        Returns:
            Dict with relevant context (files, patterns, etc)
        """
        node = self.nodes.get(task_id)
        if not node:
            return {}

        context = {
            "description": node.description,
            "implementation_details": node.implementation_details,
            "related_files": [],
            "related_code": [],
        }

        # Get context from direct dependencies
        for dep_id in node.dependencies:
            if dep_id in completed_tasks:
                dep_result = completed_tasks[dep_id]
                if "files" in dep_result:
                    context["related_files"].extend(dep_result["files"])
                if "code" in dep_result:
                    context["related_code"].append(dep_result["code"])

        # Also find related tasks by keyword matching
        for other_id, other_result in completed_tasks.items():
            if other_id == task_id or other_id in node.dependencies:
                continue

            other_node = self.nodes.get(other_id)
            if other_node:
                # Check keyword overlap
                overlap = set(node.keywords) & set(other_node.keywords)
                if len(overlap) >= 2:  # At least 2 matching keywords
                    if "files" in other_result:
                        context["related_files"].extend(other_result["files"][:2])

        # Deduplicate
        context["related_files"] = list(set(context["related_files"]))[:10]

        return context

    def __len__(self) -> int:
        return len(self.nodes)

    def summary(self) -> Dict:
        """Get a summary of the graph for debugging/logging."""
        return {
            "total_tasks": len(self.nodes),
            "total_levels": len(self.levels),
            "tasks_per_level": [len(level) for level in self.levels],
            "execution_order": self.execution_order[:10],  # First 10
        }
