# src/agents/developer.py
from .base_agent import BaseAgent
from ..services.github_service import GitHubService
from ..models.task import Task
from typing import List

class Developer(BaseAgent):
    def __init__(self, focus: str):
        super().__init__("gpt2-large")
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