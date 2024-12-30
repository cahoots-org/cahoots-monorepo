# src/agents/developer.py
from .base_agent import BaseAgent
from ..services.github_service import GitHubService
from ..utils.event_system import EventSystem, CHANNELS
from ..models.task import Task
from typing import List, Dict
import asyncio
import os
import uuid

class Developer(BaseAgent):
    def __init__(self, developer_id: str):
        """Initialize the developer agent."""
        super().__init__("codellama/CodeLlama-34b-Instruct-hf")
        self.developer_id = developer_id
        self.github = GitHubService()
        
    async def setup_events(self):
        """Initialize event system and subscribe to channels"""
        self.logger.info("Setting up event system")
        await self.event_system.connect()
        await self.event_system.subscribe("system", self.handle_system_message)
        await self.event_system.subscribe("story_assigned", self.handle_story_assigned)
        self._listening_task = asyncio.create_task(self.event_system.start_listening())
        self.logger.info("Event system setup complete")
        
    def process_message(self, message: dict) -> dict:
        """Process incoming messages"""
        self.logger.info(f"Processing message type: {message['type']}")
        
        if message["type"] == "new_story":
            return self.handle_new_story(message)
        elif message["type"] == "review_request":
            return self.handle_review_request(message)
            
        return {"status": "error", "message": "Unknown message type"}
    
    async def handle_story_assigned(self, data: Dict):
        """Handle story assignment event"""
        self.logger.info(f"Received story assignment: {data}")
        
        # Ensure we have all required fields
        required_fields = ["story_id", "title", "description", "repo_url", "assigned_to"]
        if not all(field in data for field in required_fields):
            self.logger.error(f"Missing required fields in story assignment. Required: {required_fields}, Got: {list(data.keys())}")
            return
            
        if data.get("assigned_to") != self.developer_id:
            self.logger.info(f"Story assigned to {data.get('assigned_to')}, but I am {self.developer_id}. Ignoring.")
            return
            
        try:
            # Extract repository name from URL
            repo_url = data["repo_url"]
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            
            # Clone the repository
            self.logger.info(f"Cloning repository {repo_url}")
            repo_path = self.github.clone_repository(repo_url)
            self.logger.info(f"Repository cloned to {repo_path}")
            
            # Create a feature branch for the story
            branch_name = f"feature/{data['story_id']}"
            self.logger.info(f"Creating branch {branch_name}")
            self.github.create_branch(repo_name, branch_name)
            
            # Break down story into tasks
            self.logger.info("Breaking down story into tasks")
            tasks = self.break_down_story({
                "title": data["title"],
                "description": data["description"]
            })
            self.logger.info(f"Story broken down into {len(tasks)} tasks")
            completed_tasks = []
            
            # Implement each task in sequence
            for task in tasks:
                try:
                    # Create initial implementation for the task
                    self.logger.info(f"Implementing task: {task.title}")
                    implementation = self.implement_task(task)
                    
                    # Commit changes to the feature branch
                    files = {
                        implementation["file_path"]: implementation["code"]
                    }
                    
                    self.logger.info(f"Committing changes for task {task.id}")
                    self.github.commit_changes(
                        repo_name,
                        branch_name,
                        files,
                        f"feat: {task.title}"
                    )
                    
                    # Add to completed tasks
                    completed_tasks.append(task)
                    
                    # Notify about task completion
                    self.logger.info(f"Publishing task completion event for task {task.id}")
                    await self.event_system.publish("task_completed", {
                        "story_id": data["story_id"],
                        "task_id": task.id,
                        "developer_id": self.developer_id,
                        "repo_name": repo_name,
                        "branch_name": branch_name,
                        "completed_count": len(completed_tasks),
                        "total_count": len(tasks)
                    })
                except Exception as e:
                    self.logger.error(f"Failed to implement task {task.id}: {str(e)}")
                    continue
                    
            # Only create PR if all tasks were completed
            if len(completed_tasks) == len(tasks):
                # Create pull request after all tasks are implemented
                self.logger.info("Creating pull request")
                pr_url = self.create_pr({
                    task.id: {
                        "code": self.implement_task(task)["code"],
                        "task": task.dict()
                    } for task in completed_tasks
                })
                
                # Extract PR number and notify about PR creation
                try:
                    pr_number = self.github.get_pull_request_number(pr_url)
                    self.logger.info(f"Publishing PR creation event for PR #{pr_number}")
                    await self.event_system.publish("pr_created", {
                        "story_id": data["story_id"],
                        "pr_number": pr_number,
                        "repo_name": repo_name,
                        "developer_id": self.developer_id,
                        "pr_url": pr_url,
                        "completed_tasks": [task.id for task in completed_tasks]
                    })
                    
                except ValueError as e:
                    self.logger.error(f"Failed to process PR: {str(e)}")
            else:
                self.logger.warning(f"Not all tasks were completed ({len(completed_tasks)}/{len(tasks)}). Skipping PR creation.")
                
        except Exception as e:
            self.logger.error(f"Failed to handle story assignment: {str(e)}")
            self.logger.error(f"Stack trace:", exc_info=True)
    
    def handle_new_story(self, message: dict) -> dict:
        """Handle new story assignment"""
        tasks = self.break_down_story(message["story"])
        
        if self.needs_ux_design(tasks):
            return {
                "status": "needs_ux",
                "tasks": [task.dict() for task in tasks]
            }
            
        implementation_result = self.implement_tasks(tasks)
        pr_url = self.create_pr(implementation_result)
        
        return {
            "status": "success",
            "pr_url": pr_url,
            "implementation": implementation_result
        }
    
    def handle_review_request(self, message: dict) -> dict:
        """Handle code review request"""
        review_result = self.review_code(message["pr_url"])
        
        return {
            "status": "success",
            "approved": review_result["approved"],
            "comments": review_result["comments"]
        }
    
    def break_down_story(self, story: dict) -> List[Task]:
        """Break down a user story into smaller technical tasks."""
        self.logger.info(f"Breaking down story: {story['title']}")
        
        # Generate task breakdown using the model
        prompt = f"""Break down this user story into technical tasks:
        Title: {story['title']}
        Description: {story['description']}
        Focus: {self.focus}
        """
        
        response = self.generate_response(prompt)
        
        # Parse response into tasks
        tasks = []
        task_descriptions = response.split("\n")
        for i, desc in enumerate(task_descriptions):
            if desc.strip():
                task = Task(
                    id=str(uuid.uuid4()),
                    title=f"{self.focus.capitalize()} Task {i+1}",
                    description=desc.strip(),
                    requires_ux=self.focus == "frontend"
                )
                tasks.append(task)
                
        return tasks
    
    def needs_ux_design(self, tasks: List[Task]) -> bool:
        """Determine if any tasks require UX design."""
        return any(task.requires_ux for task in tasks)
    
    def implement_task(self, task: Task) -> dict:
        """Implement a single task"""
        # Determine the appropriate file path based on the task
        if "model" in task.title.lower() or "database" in task.title.lower():
            file_path = "src/models/model.py"
        elif "endpoint" in task.title.lower() or "api" in task.title.lower():
            file_path = "src/api/routes.py"
        elif "component" in task.title.lower() or "ui" in task.title.lower():
            file_path = "src/ui/components.py"
        elif "test" in task.title.lower():
            file_path = "tests/test_main.py"
        else:
            file_path = f"src/core/{task.title.lower().replace(' ', '_')}.py"
            
        # Generate implementation based on task description
        prompt = f"""Implement this technical task:
        Task: {task.title}
        Description: {task.description}
        Focus: {self.focus}
        Requirements: Write production-ready code with proper error handling
        """
        
        code = self.generate_response(prompt)
        
        return {
            "file_path": file_path,
            "code": code
        }
    
    def implement_tasks(self, tasks: List[Task]) -> dict:
        """Implement multiple technical tasks."""
        self.logger.info(f"Implementing {len(tasks)} tasks")
        
        implementations = {}
        for task in tasks:
            implementation = self.implement_task(task)
            implementations[task.id] = {
                "code": implementation["code"],
                "task": task.dict()
            }
            
        return implementations
    
    def create_pr(self, implementation_result: dict) -> str:
        """Create a pull request with the implemented changes."""
        self.logger.info("Creating pull request")
        
        # Prepare PR description
        pr_description = "## Implementation Details\n\n"
        for task_id, details in implementation_result.items():
            pr_description += f"### {details['task']['title']}\n"
            pr_description += f"{details['task']['description']}\n\n"
            pr_description += "```python\n"
            pr_description += details['code']
            pr_description += "\n```\n\n"
        
        # Create PR using GitHub service
        pr_url = self.github.create_pull_request(
            repo_name="ai-dev-team",
            title=f"{self.focus}: Implement new features",
            body=pr_description
        )
        
        return pr_url
    
    def review_code(self, pr_url: str) -> dict:
        """Review code in a pull request."""
        self.logger.info(f"Reviewing PR: {pr_url}")
        
        # Generate code review using the model
        prompt = f"""Review this pull request for:
        - Code quality
        - Best practices
        - Potential bugs
        - Performance issues
        PR URL: {pr_url}
        """
        
        review_response = self.generate_response(prompt)
        
        # Parse review response
        approved = "LGTM" in review_response or "looks good" in review_response.lower()
        
        return {
            "approved": approved,
            "comments": review_response
        }