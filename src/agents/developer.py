# src/agents/developer.py
from .base_agent import BaseAgent
from ..services.github_service import GitHubService
from ..models.task import Task
from typing import List

class Developer(BaseAgent):
    def __init__(self, focus: str):
        super().__init__("codellama/CodeLlama-34b-Instruct-hf")
        self.focus = focus  # "frontend" or "backend"
        self.github = GitHubService()
        
    def process_message(self, message: dict) -> dict:
        self.logger.info(f"Processing message type: {message['type']}")
        
        if message["type"] == "new_story":
            return self.handle_new_story(message)
        elif message["type"] == "review_request":
            return self.handle_review_request(message)
            
        return {"status": "error", "message": "Unknown message type"}
    
    def handle_new_story(self, message: dict) -> dict:
        tasks = self.break_down_story(message["story"])
        
        if self.needs_ux_design(tasks):
            return {
                "status": "needs_ux",
                "tasks": [task.to_dict() for task in tasks]
            }
            
        implementation_result = self.implement_tasks(tasks)
        pr_url = self.create_pr(implementation_result)
        
        return {
            "status": "success",
            "pr_url": pr_url,
            "implementation": implementation_result
        }
    
    def handle_review_request(self, message: dict) -> dict:
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
                    id=f"task_{i}",
                    title=f"{self.focus.capitalize()} Task {i+1}",
                    description=desc.strip(),
                    requires_ux=self.focus == "frontend"
                )
                tasks.append(task)
                
        return tasks
    
    def needs_ux_design(self, tasks: List[Task]) -> bool:
        """Determine if any tasks require UX design."""
        return any(task.requires_ux for task in tasks)
    
    def implement_tasks(self, tasks: List[Task]) -> dict:
        """Implement the technical tasks."""
        self.logger.info(f"Implementing {len(tasks)} tasks")
        
        implementations = {}
        for task in tasks:
            prompt = f"""Implement this technical task:
            Task: {task.title}
            Description: {task.description}
            Focus: {self.focus}
            Requirements: Write production-ready code with proper error handling
            """
            
            implementation = self.generate_response(prompt)
            implementations[task.id] = {
                "code": implementation,
                "task": task.to_dict()
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