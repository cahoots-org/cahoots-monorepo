# src/agents/tester.py
from .base_agent import BaseAgent
from ..services.github_service import GitHubService
from ..models.project import Project

class Tester(BaseAgent):
    def __init__(self):
        super().__init__("gpt2-large")
        self.github = GitHubService()
        
    def process_message(self, message: dict) -> dict:
        self.logger.info(f"Processing message type: {message['type']}")
        
        if message["type"] == "test_request":
            return self.handle_test_request(message)
            
        return {"status": "error", "message": "Unknown message type"}
    
    def handle_test_request(self, message: dict) -> dict:
        project = Project.from_dict(message["project"])
        test_suite = self.generate_test_suite(project)
        test_results = self.run_tests(test_suite)
        
        return {
            "status": "success",
            "passed": test_results["passed"],
            "coverage": test_results["coverage"],
            "report": test_results["report"]
        }