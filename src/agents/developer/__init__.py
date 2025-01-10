"""Developer agent that implements code based on tasks."""
from typing import List, Dict, Any, Optional
import re

from ..base_agent import BaseAgent
from ...models.task import Task
from ...services.github_service import GitHubService
from ...utils.base_logger import BaseLogger
from ...utils.event_system import EventSystem
from .task_manager import TaskManager
from .code_generator import CodeGenerator
from .code_validator import CodeValidator
from .feedback_manager import FeedbackManager
from .file_manager import FileManager
from .pr_manager import PRManager

class Developer(BaseAgent):
    """Developer agent that implements code based on tasks."""
    
    def __init__(self, developer_id: str, start_listening: bool = True, focus: str = "backend", event_system: Optional[EventSystem] = None, github_service: Optional[GitHubService] = None, github_config: Optional[Any] = None):
        """Initialize the developer agent.
        
        Args:
            developer_id: The unique identifier for this developer
            start_listening: Whether to start listening for events immediately
            focus: The developer's focus area ("frontend" or "backend")
            event_system: Optional event system instance. If not provided, will get from singleton.
            github_service: Optional GitHub service instance for testing
            github_config: Optional GitHub config for testing
        """
        # Initialize base class with start_listening=False to prevent double initialization
        super().__init__("gpt-4-1106-preview", start_listening=False, event_system=event_system)
        
        self.github = github_service or GitHubService(github_config)
        self.developer_id = developer_id
        self.logger = BaseLogger(self.__class__.__name__)
        self.focus = focus
        self.feedback_history = []
        
        if not self.developer_id:
            raise RuntimeError("developer_id is required")
            
        # Initialize managers with shared task manager
        self.code_generator = CodeGenerator(self)
        self.code_validator = CodeValidator(self)
        self.feedback_manager = FeedbackManager(self)
        self.file_manager = FileManager(self)
        self.pr_manager = PRManager(self)
        
        # Ensure all managers use the same task manager instance
        for manager in [
            self.code_generator,
            self.code_validator,
            self.feedback_manager,
            self.file_manager,
            self.pr_manager
        ]:
            if hasattr(manager, "_task_manager"):
                manager._task_manager = self._task_manager
        
        # Start listening after full initialization if requested
        if start_listening:
            self._task_manager.create_task(self.setup_and_start())
            
    async def setup_and_start(self) -> None:
        """Set up event subscriptions and start listening."""
        await self.setup_events()
        await self.start()

    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        # Ensure event system is connected and base handlers are registered
        await super().setup_events()
        
        # Register developer-specific handlers
        await self.event_handler.register_handler("task_assigned", self._handle_message)
        await self.event_handler.register_handler("story_assigned", self._handle_message)
        await self.event_handler.register_handler("review_requested", self._handle_message)
        
    async def stop_listening(self) -> None:
        """Stop listening for events and cleanup all tasks."""
        self.logger.info("Stopping developer agent")
        
        # Stop event listener first
        await super().stop_listening()
        
        # Then cleanup manager tasks
        for manager in [
            self.code_generator,
            self.code_validator,
            self.feedback_manager,
            self.file_manager,
            self.pr_manager
        ]:
            if hasattr(manager, "cleanup"):
                try:
                    await manager.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up manager {manager.__class__.__name__}: {str(e)}")
        
        self.logger.info("Developer agent stopped")
        
    def needs_ux_design(self, tasks: List[Task]) -> bool:
        """Check if any tasks require UX design.
        
        Args:
            tasks: List of tasks to check
            
        Returns:
            bool: True if any task needs UX design, False otherwise
        """
        ux_keywords = {
            'ui', 'ux', 'user interface', 'user experience', 'design', 'layout',
            'wireframe', 'mockup', 'prototype', 'frontend', 'front-end', 'front end',
            'usability', 'accessibility', 'a11y', 'responsive', 'mobile', 'desktop',
            'interaction', 'animation', 'transition', 'style', 'css', 'sass', 'less',
            'theme', 'component', 'widget', 'modal', 'dialog', 'form', 'input',
            'button', 'menu', 'navigation', 'nav', 'header', 'footer', 'sidebar'
        }
        
        for task in tasks:
            # Check title and description
            text = f"{task.title.lower()} {task.description.lower()}"
            
            # Check for UX keywords
            if any(keyword in text for keyword in ux_keywords):
                return True
                
            # Check metadata
            if task.metadata:
                # Check required skills
                if 'required_skills' in task.metadata:
                    skills = [s.lower() for s in task.metadata['required_skills']]
                    if any(skill in ux_keywords for skill in skills):
                        return True
                
                # Check task type
                if 'type' in task.metadata:
                    task_type = task.metadata['type'].lower()
                    if task_type in {'ui', 'ux', 'design', 'frontend'}:
                        return True
                        
                # Check task tags
                if 'tags' in task.metadata:
                    tags = [t.lower() for t in task.metadata['tags']]
                    if any(tag in ux_keywords for tag in tags):
                        return True
                        
                # Check task category
                if 'category' in task.metadata:
                    category = task.metadata['category'].lower()
                    if category in {'ui', 'ux', 'design', 'frontend'}:
                        return True
        
        return False
        
    def _get_relevant_feedback(self, context: str) -> List[Dict[str, Any]]:
        """Get relevant feedback for the given context.
        
        Args:
            context: The context to get feedback for
            
        Returns:
            List[Dict[str, Any]]: List of relevant feedback items
        """
        # Get feedback from manager and ensure it's a list
        feedback = self.feedback_manager.get_relevant_feedback(context)
        if not isinstance(feedback, list):
            return []
        return feedback
        
    def _integrate_feedback(self, feedback: List[Dict[str, Any]]) -> None:
        """Integrate feedback into the implementation process.
        
        Args:
            feedback: List of feedback items to integrate
        """
        self.feedback_history.append(feedback)
        self.feedback_manager.integrate_feedback(feedback)
        
    def _determine_file_path(self, task: Task) -> str:
        """Determine the appropriate file path for a task implementation.
        
        Args:
            task: The task to determine the file path for
            
        Returns:
            str: The determined file path
        """
        return self.file_manager.determine_file_path(task)
        
    async def _handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a specific message type.
        
        Args:
            message: The message to handle
            
        Returns:
            Dict[str, Any]: The response to the message
        """
        handlers = {
            "task_assigned": self.handle_task_assigned,
            "story_assigned": self.handle_story_assigned,
            "review_requested": self.handle_review_request
        }
        
        handler = handlers.get(message["type"])
        if not handler:
            raise ValueError(f"Unknown message type: {message['type']}")
            
        return await handler(message)

    async def __aenter__(self) -> "Developer":
        """Async context manager entry."""
        await super().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await super().__aexit__(exc_type, exc_val, exc_tb)
        
    async def implement_tasks(self, tasks: List[Task]) -> Dict[str, Any]:
        """Implement a list of tasks in order.
        
        Args:
            tasks: List of tasks to implement
            
        Returns:
            Dict[str, Any]: Implementation results including code and metadata
        """
        self.logger.info(f"Implementing {len(tasks)} tasks")
        implementations = {}
        failed_tasks = []
        
        for task in tasks:
            try:
                self.logger.info(f"Implementing task: {task.title}")
                implementation = await self.code_generator.generate_implementation(task)
                
                validation_result = await self.code_validator.validate_implementation(
                    implementation["code"],
                    task
                )
                
                if validation_result["valid"]:
                    implementations[task.id] = {
                        "code": implementation["code"],
                        "file_path": implementation["file_path"],
                        "task": task.dict(),
                        "validation": validation_result
                    }
                else:
                    raise ValueError(f"Implementation validation failed: {validation_result['errors']}")
                    
            except Exception as e:
                self.logger.error(f"Failed to implement task {task.id}: {str(e)}")
                failed_tasks.append({
                    "task_id": task.id,
                    "error": str(e)
                })
                
        return {
            "implementations": implementations,
            "failed_tasks": failed_tasks
        }
        
    async def break_down_story(self, story: Dict[str, Any]) -> List[Task]:
        """Break down a user story into smaller technical tasks.
        
        Args:
            story: Dictionary containing story details
            
        Returns:
            List[Task]: List of tasks to implement the story
        """
        return await self.task_manager.break_down_story(story)
        
    async def create_pr(self, implementation_result: Dict[str, Any]) -> str:
        """Create a pull request with the implemented changes.
        
        Args:
            implementation_result: Results from implement_tasks
            
        Returns:
            str: URL of the created pull request
            
        Raises:
            ValueError: If any implementation has validation errors
        """
        # Check for validation errors
        for impl in implementation_result["implementations"].values():
            if not impl["validation"]["valid"]:
                raise ValueError(f"Implementation validation failed: {impl['validation']['errors']}")
                
        # Get first task ID for branch name
        first_task_id = next(iter(implementation_result["implementations"]))
        branch_name = f"feature/implementation-{first_task_id}"
        
        # Create branch
        await self.github.create_branch(branch_name)
        
        # Prepare changes
        changes = []
        for task_id, details in implementation_result["implementations"].items():
            changes.append({
                "file_path": details["file_path"],
                "content": details["code"]
            })
            
        # Commit changes
        await self.github.commit_changes(
            changes,
            f"Implement tasks: {', '.join(details['task']['title'] for details in implementation_result['implementations'].values())}"
        )
        
        # Prepare PR description with validation results
        pr_description = "## Implementation Details\n\n"
        for task_id, details in implementation_result["implementations"].items():
            pr_description += f"### {details['task']['title']}\n"
            pr_description += f"{details['task']['description']}\n\n"
            pr_description += "```python\n"
            pr_description += details['code']
            pr_description += "\n```\n\n"
            
        # Add validation results
        pr_description += "## Validation Results\n\n"
        pr_description += "✅ All implementations passed validation checks\n\n"
        
        # Create PR using GitHub API
        pr_url = await self.github.create_pr(
            title=f"Implementation of {len(implementation_result['implementations'])} tasks",
            body=pr_description,
            base="main",
            head=branch_name
        )
        
        return pr_url
        
    async def handle_task_assigned(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task assignment message.
        
        Args:
            message: Task assignment message
            
        Returns:
            Dict[str, Any]: Response indicating success/failure
        """
        try:
            task = Task(**message["task"])
            implementation = await self.implement_tasks([task])
            
            if implementation["failed_tasks"]:
                return {
                    "status": "error",
                    "message": f"Failed to implement task: {implementation['failed_tasks'][0]['error']}"
                }
                
            return {
                "status": "success",
                "implementation": implementation["implementations"][task.id]
            }
        except Exception as e:
            self.logger.error(f"Failed to handle task assignment: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def handle_story_assigned(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle story assignment message.
        
        Args:
            message: Story assignment message
            
        Returns:
            Dict[str, Any]: Response indicating success/failure
        """
        story = None
        try:
            if not isinstance(message, dict) or "story" not in message:
                return {
                    "status": "error",
                    "message": "Invalid message format: missing story data"
                }
                
            story = message["story"]
            if not isinstance(story, dict):
                return {
                    "status": "error",
                    "message": "Invalid story format: expected dictionary"
                }
            
            # Check for required fields
            required_fields = ["story_id", "title", "description", "repo_url"]
            missing_fields = [field for field in required_fields if field not in story]
            if missing_fields:
                return {
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }
            
            # Check if story is assigned to this developer
            if story.get("assigned_to") != self.developer_id:
                return {
                    "status": "error",
                    "message": f"Wrong developer: story is assigned to {story.get('assigned_to', 'unknown')}, not {self.developer_id}"
                }
            
            # Clone repository
            await self.github.clone_repository(story["repo_url"])
            
            # Publish implementation started event
            await self.event_system.publish("implementation_started", {
                "story_id": story["story_id"],
                "developer_id": self.developer_id
            })
            
            tasks = await self.break_down_story(story)
            implementation = await self.implement_tasks(tasks)
            
            if implementation["failed_tasks"]:
                error_messages = [f"{task['task_id']}: {task['error']}" for task in implementation["failed_tasks"]]
                await self.event_system.publish("implementation_failed", {
                    "story_id": story["story_id"],
                    "developer_id": self.developer_id,
                    "error": '; '.join(error_messages),
                    "status": "error"
                })
                return {
                    "status": "error",
                    "message": f"Implementation failed: {'; '.join(error_messages)}"
                }
                
            pr_url = await self.create_pr(implementation)
            
            # Publish implementation completed event
            await self.event_system.publish("implementation_completed", {
                "story_id": story["story_id"],
                "developer_id": self.developer_id,
                "pr_url": pr_url
            })
            
            return {
                "status": "success",
                "pr_url": pr_url,
                "implementation": implementation
            }
        except Exception as e:
            self.logger.error(f"Failed to handle story assignment: {str(e)}")
            if story:
                await self.event_system.publish("implementation_failed", {
                    "story_id": story.get("story_id", "unknown"),
                    "developer_id": self.developer_id,
                    "error": str(e),
                    "status": "error"
                })
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def handle_review_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code review request.
        
        Args:
            message: Review request message containing:
                - pr_url: URL of the pull request
                - repo_name: Name of the repository
                - branch: Branch name
                - files: List of files changed
                
        Returns:
            Dict[str, Any]: Review results containing:
                - status: Review status (success/error)
                - approved: Whether the changes are approved
                - comments: List of review comments
                - suggestions: List of code suggestions
        """
        try:
            self.logger.info(f"Reviewing PR: {message['pr_url']}")
            
            # Extract PR number from URL
            pr_number = await self.github.get_pull_request_number(message['pr_url'])
            
            # Get PR details
            pr_details = await self.github.get_pull_request(pr_number)
            changed_files = pr_details['changed_files']
            
            review_comments = []
            suggestions = []
            critical_issues = []
            
            # Review each changed file
            for file_path in changed_files:
                file_content = await self.github.get_file_content(file_path, pr_details['head'])
                
                # Skip if file is deleted
                if file_content is None:
                    continue
                
                # 1. Code Quality Checks
                quality_issues = await self._check_code_quality(file_path, file_content)
                review_comments.extend(quality_issues)
                
                # 2. Test Coverage Analysis
                if file_path.endswith('.py') and not file_path.startswith('tests/'):
                    test_issues = await self._check_test_coverage(file_path, file_content)
                    review_comments.extend(test_issues)
                
                # 3. Security Analysis
                security_issues = await self._check_security(file_path, file_content)
                if security_issues:
                    critical_issues.extend(security_issues)
                    review_comments.extend(security_issues)
                
                # 4. Performance Review
                perf_issues = await self._check_performance(file_path, file_content)
                review_comments.extend(perf_issues)
                
                # 5. Documentation Check
                doc_issues = await self._check_documentation(file_path, file_content)
                review_comments.extend(doc_issues)
                
                # 6. Generate Improvement Suggestions
                file_suggestions = await self._generate_suggestions(file_path, file_content)
                suggestions.extend(file_suggestions)
            
            # Determine approval status
            approved = len(critical_issues) == 0 and len(review_comments) <= 5
            
            # Format review message
            review_message = self._format_review_message(
                review_comments,
                suggestions,
                critical_issues,
                approved
            )
            
            # Post review comments
            await self.github.post_review_comments(
                pr_number,
                review_comments,
                approved,
                review_message
            )
            
            return {
                "status": "success",
                "approved": approved,
                "comments": review_comments,
                "suggestions": suggestions,
                "critical_issues": critical_issues
            }
            
        except Exception as e:
            self.logger.error(f"Failed to handle review request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def _check_code_quality(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check code quality using static analysis."""
        issues = []
        
        # Run static analysis
        try:
            # Use ruff for linting
            result = await self.code_validator.run_linter(content)
            
            for issue in result:
                issues.append({
                    "type": "style",
                    "file": file_path,
                    "line": issue["line"],
                    "message": issue["message"],
                    "severity": "low"
                })
                
            # Check complexity
            complexity = await self.code_validator.check_complexity(content)
            if complexity > 10:  # McCabe complexity threshold
                issues.append({
                    "type": "complexity",
                    "file": file_path,
                    "message": f"Function complexity of {complexity} exceeds threshold of 10",
                    "severity": "medium"
                })
                
        except Exception as e:
            self.logger.warning(f"Code quality check failed for {file_path}: {str(e)}")
            
        return issues
        
    async def _check_test_coverage(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Analyze test coverage for the changed code."""
        issues = []
        
        try:
            # Get corresponding test file
            test_file = f"tests/{file_path.replace('src/', '')}"
            test_file = test_file.replace('.py', '_test.py')
            
            # Check if test file exists
            if not await self.github.file_exists(test_file):
                issues.append({
                    "type": "test",
                    "file": file_path,
                    "message": "No corresponding test file found",
                    "severity": "high"
                })
                return issues
                
            # Analyze test coverage
            coverage = await self.code_validator.check_test_coverage(content)
            if coverage < 80:
                issues.append({
                    "type": "test",
                    "file": file_path,
                    "message": f"Test coverage of {coverage}% is below required 80%",
                    "severity": "medium"
                })
                
        except Exception as e:
            self.logger.warning(f"Test coverage check failed for {file_path}: {str(e)}")
            
        return issues
        
    async def _check_security(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check for security issues in the code."""
        issues = []
        
        try:
            # Run security checks using bandit
            security_issues = await self.code_validator.run_security_check(content)
            
            for issue in security_issues:
                issues.append({
                    "type": "security",
                    "file": file_path,
                    "line": issue["line"],
                    "message": issue["message"],
                    "severity": "high"
                })
                
            # Check for hardcoded secrets
            if re.search(r'(password|secret|key|token).*=.*[\'"][^\'"]+[\'"]', content, re.I):
                issues.append({
                    "type": "security",
                    "file": file_path,
                    "message": "Possible hardcoded secret detected",
                    "severity": "critical"
                })
                
        except Exception as e:
            self.logger.warning(f"Security check failed for {file_path}: {str(e)}")
            
        return issues
        
    async def _check_performance(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Analyze code for performance issues."""
        issues = []
        
        try:
            # Run comprehensive performance analysis
            perf_results = await self.code_validator.analyze_performance(content)
            
            # Add complexity issues
            for metric in perf_results.get("complexity_metrics", {}).get("time_complexity", []):
                if "O(n^2)" in metric["complexity"] or "O(n^3)" in metric["complexity"]:
                    issues.append({
                        "type": "performance",
                        "file": file_path,
                        "message": f"High time complexity in {metric['node']}: {metric['complexity']}",
                        "severity": "high"
                    })
                    
            # Add memory issues
            for alloc in perf_results.get("memory_usage", {}).get("large_allocations", []):
                issues.append({
                    "type": "performance",
                    "file": file_path,
                    "message": f"Large memory allocation: {alloc['suggestion']}",
                    "severity": "medium"
                })
                
            # Add bottleneck warnings
            for bottleneck in perf_results.get("bottlenecks", []):
                issues.append({
                    "type": "performance",
                    "file": file_path,
                    "message": f"{bottleneck['description']}: {bottleneck['suggestion']}",
                    "severity": bottleneck["severity"]
                })
                
            # Add optimization suggestions
            for suggestion in perf_results.get("optimization_suggestions", []):
                issues.append({
                    "type": "performance",
                    "file": file_path,
                    "message": f"{suggestion['description']} in {suggestion['target']}",
                    "severity": "low",
                    "example": suggestion.get("example", "")
                })
                
        except Exception as e:
            self.logger.warning(f"Performance check failed for {file_path}: {str(e)}")
            
        return issues
        
    async def _check_documentation(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check for proper documentation."""
        issues = []
        
        try:
            # Check for module docstring
            if not re.search(r'""".*?"""', content, re.DOTALL):
                issues.append({
                    "type": "documentation",
                    "file": file_path,
                    "message": "Missing module docstring",
                    "severity": "low"
                })
                
            # Check function docstrings
            functions = re.finditer(r'def\s+(\w+)\s*\([^)]*\):', content)
            for func in functions:
                func_name = func.group(1)
                if not re.search(rf'def\s+{func_name}\s*\([^)]*\):\s*"""', content):
                    issues.append({
                        "type": "documentation",
                        "file": file_path,
                        "message": f"Missing docstring for function {func_name}",
                        "severity": "low"
                    })
                    
        except Exception as e:
            self.logger.warning(f"Documentation check failed for {file_path}: {str(e)}")
            
        return issues
        
    async def _generate_suggestions(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Generate improvement suggestions for the code."""
        suggestions = []
        
        try:
            # Analyze code patterns
            patterns = await self.code_validator.analyze_patterns(content)
            
            # Generate suggestions based on patterns
            for pattern in patterns:
                if pattern["type"] == "refactoring":
                    suggestions.append({
                        "type": "suggestion",
                        "file": file_path,
                        "message": f"Consider refactoring: {pattern['message']}",
                        "example": pattern.get("example", "")
                    })
                    
        except Exception as e:
            self.logger.warning(f"Failed to generate suggestions for {file_path}: {str(e)}")
            
        return suggestions
        
    def _format_review_message(
        self,
        comments: List[Dict[str, Any]],
        suggestions: List[Dict[str, Any]],
        critical_issues: List[Dict[str, Any]],
        approved: bool
    ) -> str:
        """Format the review message with all findings."""
        message_parts = []
        
        if approved:
            message_parts.append("## ✅ Review Passed\n")
        else:
            message_parts.append("## ❌ Changes Requested\n")
        
        if critical_issues:
            message_parts.append("\n### 🚨 Critical Issues\n")
            for issue in critical_issues:
                message_parts.append(f"- [{issue['file']}] {issue['message']}")
        
        if comments:
            message_parts.append("\n### 💭 Review Comments\n")
            for comment in comments:
                severity_icon = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(comment["severity"], "ℹ️")
                message_parts.append(f"- {severity_icon} [{comment['file']}] {comment['message']}")
        
        if suggestions:
            message_parts.append("\n### 💡 Suggestions\n")
            for suggestion in suggestions:
                message_parts.append(f"- {suggestion['message']}")
                if suggestion.get("example"):
                    message_parts.append(f"  ```python\n  {suggestion['example']}\n  ```")
        
        return "\n".join(message_parts)
        
    async def handle_system_message(self, message: Dict[str, Any]) -> None:
        """Handle system messages.
        
        Args:
            message: System message data
        """
        self.logger.info(f"Received system message: {message}")
        # No specific handling needed for system messages in Developer 