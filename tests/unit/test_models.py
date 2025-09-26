"""Unit tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    Task, TaskStatus, TaskAnalysis, ApproachType,
    TaskDecomposition, TaskTree, TaskRequest,
    TechPreferences, RepositoryInfo,
    TaskResponse, TaskTreeNode, TaskStats
)


class TestTaskModel:
    """Test suite for Task model."""

    def test_task_creation_with_defaults(self):
        """Test creating a task with default values."""
        task = Task(description="Test task")

        assert task.description == "Test task"
        assert task.status == TaskStatus.SUBMITTED
        assert task.depth == 0
        assert task.parent_id is None
        assert task.is_atomic is False
        assert task.complexity_score == 0.0
        assert task.subtasks == []
        assert isinstance(task.id, str)
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

    def test_task_creation_with_all_fields(self):
        """Test creating a task with all fields specified."""
        task = Task(
            id="test-123",
            description="Complex task",
            status=TaskStatus.PROCESSING,
            depth=2,
            parent_id="parent-456",
            is_atomic=True,
            complexity_score=0.75,
            implementation_details="Use Python with FastAPI",
            story_points=5,
            subtasks=["child-1", "child-2"],
            metadata={"key": "value"},
            tech_preferences={"language": "python"},
            best_practices="Follow PEP8",
            user_id="user-789"
        )

        assert task.id == "test-123"
        assert task.status == TaskStatus.PROCESSING
        assert task.depth == 2
        assert task.parent_id == "parent-456"
        assert task.is_atomic is True
        assert task.complexity_score == 0.75
        assert task.story_points == 5
        assert len(task.subtasks) == 2

    def test_task_depth_validation(self):
        """Test depth validation."""
        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test", depth=-1)
        assert "Depth must be non-negative" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test", depth=11)
        assert "Maximum depth exceeded" in str(exc_info.value)

    def test_task_complexity_validation(self):
        """Test complexity score validation."""
        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test", complexity_score=1.5)
        assert "Complexity score must be between 0 and 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test", complexity_score=-0.1)
        assert "Complexity score must be between 0 and 1" in str(exc_info.value)

    def test_task_story_points_validation(self):
        """Test story points validation."""
        task = Task(description="Test", story_points=5)
        assert task.story_points == 5

        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test", story_points=0)
        assert "Story points must be between 1 and 21" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test", story_points=22)
        assert "Story points must be between 1 and 21" in str(exc_info.value)

    def test_task_redis_serialization(self):
        """Test converting task to/from Redis dictionary."""
        original = Task(
            description="Test task",
            status=TaskStatus.IN_PROGRESS,
            complexity_score=0.5,
            story_points=3,
            metadata={"test": "data"}
        )

        # Convert to Redis dict
        redis_dict = original.to_redis_dict()
        assert isinstance(redis_dict, dict)
        assert redis_dict["description"] == "Test task"
        assert redis_dict["status"] == "in_progress"
        assert isinstance(redis_dict["created_at"], str)

        # Convert back from Redis dict
        restored = Task.from_redis_dict(redis_dict)
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.complexity_score == original.complexity_score
        assert restored.story_points == original.story_points


class TestTaskAnalysisModel:
    """Test suite for TaskAnalysis model."""

    def test_task_analysis_creation(self):
        """Test creating a task analysis."""
        analysis = TaskAnalysis(
            complexity_score=0.7,
            is_atomic=False,
            is_specific=True,
            confidence=0.85,
            reasoning="This task requires multiple steps",
            suggested_approach=ApproachType.DECOMPOSE,
            estimated_story_points=8,
            similar_patterns=["CRUD", "authentication"]
        )

        assert analysis.complexity_score == 0.7
        assert analysis.is_atomic is False
        assert analysis.suggested_approach == ApproachType.DECOMPOSE
        assert len(analysis.similar_patterns) == 2

    def test_task_analysis_validation(self):
        """Test validation of analysis fields."""
        with pytest.raises(ValidationError) as exc_info:
            TaskAnalysis(
                complexity_score=1.5,  # Invalid: > 1
                is_atomic=True,
                is_specific=True,
                confidence=0.9,
                reasoning="Test",
                suggested_approach=ApproachType.IMPLEMENT
            )
        assert "less than or equal to 1" in str(exc_info.value).lower()


class TestTaskDecompositionModel:
    """Test suite for TaskDecomposition model."""

    def test_decomposition_creation(self):
        """Test creating a task decomposition."""
        decomposition = TaskDecomposition(
            subtasks=[
                {
                    "description": "Create database schema",
                    "is_atomic": True,
                    "implementation_details": "Use PostgreSQL",
                    "story_points": 3
                },
                {
                    "description": "Build API endpoints",
                    "is_atomic": False,
                    "story_points": 8
                }
            ],
            decomposition_reasoning="Split into data and API layers",
            estimated_total_points=11,
            suggested_order=[0, 1]
        )

        assert len(decomposition.subtasks) == 2
        assert decomposition.estimated_total_points == 11

        atomic_tasks = decomposition.get_atomic_tasks()
        assert len(atomic_tasks) == 1
        assert atomic_tasks[0]["description"] == "Create database schema"

        complex_tasks = decomposition.get_complex_tasks()
        assert len(complex_tasks) == 1
        assert complex_tasks[0]["description"] == "Build API endpoints"


class TestTaskTreeModel:
    """Test suite for TaskTree model."""

    def test_task_tree_operations(self):
        """Test TaskTree operations."""
        root = Task(id="root", description="Root task", depth=0)
        tree = TaskTree(root=root)
        tree.add_task(root)  # Add root to the tree

        # Add tasks
        child1 = Task(id="child1", description="Child 1", parent_id="root", depth=1)
        child2 = Task(id="child2", description="Child 2", parent_id="root", depth=1)
        grandchild = Task(id="grandchild", description="Grandchild", parent_id="child1", depth=2)

        tree.add_task(child1)
        tree.add_task(child2)
        tree.add_task(grandchild)

        # Update root's subtasks
        root.subtasks = ["child1", "child2"]
        tree.tasks["root"] = root

        # Update child1's subtasks
        child1.subtasks = ["grandchild"]
        tree.tasks["child1"] = child1

        # Test retrieval
        assert tree.get_task("child1") == child1
        assert tree.get_task("nonexistent") is None

        # Test get_children
        root_children = tree.get_children("root")
        assert len(root_children) == 2
        assert child1 in root_children
        assert child2 in root_children

        # Test get_all_descendants
        descendants = tree.get_all_descendants("root")
        assert len(descendants) == 3

        # Test get_leaf_tasks
        leaf_tasks = tree.get_leaf_tasks()
        assert len(leaf_tasks) == 2  # child2 and grandchild

        # Test depth_map
        assert "root" in tree.depth_map[0]
        assert "child1" in tree.depth_map[1]
        assert "grandchild" in tree.depth_map[2]

    def test_task_tree_completion_percentage(self):
        """Test calculating completion percentage."""
        root = Task(id="root", description="Root", status=TaskStatus.COMPLETED)
        tree = TaskTree(root=root, tasks={"root": root})

        # All completed
        assert tree.calculate_completion_percentage() == 100.0

        # Add incomplete tasks
        tree.add_task(Task(id="t1", description="Task 1", status=TaskStatus.IN_PROGRESS))
        tree.add_task(Task(id="t2", description="Task 2", status=TaskStatus.SUBMITTED))

        # 1 out of 3 completed
        percentage = tree.calculate_completion_percentage()
        assert 33 <= percentage <= 34


class TestRequestModels:
    """Test suite for request models."""

    def test_task_request_creation(self):
        """Test creating a task request."""
        request = TaskRequest(
            description="Build a web app",
            max_depth=3,
            complexity_threshold=0.5,
            use_cache=True
        )

        assert request.description == "Build a web app"
        assert request.max_depth == 3
        assert request.complexity_threshold == 0.5
        assert request.use_cache is True
        assert request.max_subtasks == 7  # default

    def test_task_request_validation(self):
        """Test request validation."""
        with pytest.raises(ValidationError) as exc_info:
            TaskRequest(description="")  # Empty description

        with pytest.raises(ValidationError) as exc_info:
            TaskRequest(description="   ")  # Whitespace only
        assert "cannot be empty" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            TaskRequest(description="Test", max_depth=15)  # Too deep

        with pytest.raises(ValidationError) as exc_info:
            TaskRequest(description="Test", complexity_threshold=1.5)  # Invalid threshold

    def test_tech_preferences(self):
        """Test TechPreferences model."""
        prefs = TechPreferences(
            application_type="web-application",
            tech_stack_id="react-node-postgres",
            preferred_languages=["python", "typescript"],
            frameworks={"backend": "FastAPI", "frontend": "React"}
        )

        assert prefs.application_type == "web-application"
        assert "python" in prefs.preferred_languages
        assert prefs.frameworks["backend"] == "FastAPI"

    def test_repository_info(self):
        """Test RepositoryInfo model."""
        repo = RepositoryInfo(
            type="github",
            url="https://github.com/user/repo",
            branch="develop",
            name="my-repo"
        )

        assert repo.type == "github"
        assert repo.url == "https://github.com/user/repo"
        assert repo.branch == "develop"

        # Test validation
        with pytest.raises(ValidationError) as exc_info:
            RepositoryInfo(type="invalid", url="http://example.com")
        assert "must be one of" in str(exc_info.value).lower()


class TestResponseModels:
    """Test suite for response models."""

    def test_task_response_from_task(self):
        """Test creating TaskResponse from Task."""
        task = Task(
            id="test-123",
            description="Test task",
            status=TaskStatus.IN_PROGRESS,
            complexity_score=0.5,
            story_points=3,
            subtasks=["child1", "child2"]
        )

        response = TaskResponse.from_task(task)

        assert response.task_id == "test-123"
        assert response.description == "Test task"
        assert response.status == TaskStatus.IN_PROGRESS
        assert response.children_count == 2
        assert response.complexity_score == 0.5
        assert response.story_points == 3

    def test_task_tree_node(self):
        """Test TaskTreeNode model."""
        task = Task(
            id="test-123",
            description="Test task",
            is_atomic=True,
            depth=1,
            complexity_score=0.3
        )

        node = TaskTreeNode.from_task(task)

        assert node.task_id == "test-123"
        assert node.description == "Test task"
        assert node.is_atomic is True
        assert node.depth == 1
        assert node.complexity_score == 0.3
        assert node.children == []

        # Test with children
        child_task = Task(id="child", description="Child task")
        child_node = TaskTreeNode.from_task(child_task)
        parent_node = TaskTreeNode.from_task(task, children=[child_node])

        assert len(parent_node.children) == 1
        assert parent_node.children[0].task_id == "child"

    def test_task_stats(self):
        """Test TaskStats model."""
        stats = TaskStats(
            total=100,
            completed=45,
            in_progress=20,
            rejected=5,
            pending=30,
            atomic=60,
            average_complexity=0.55,
            average_depth=2.3
        )

        assert stats.total == 100
        assert stats.completed == 45
        assert stats.atomic == 60
        assert stats.average_complexity == 0.55