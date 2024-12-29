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
    
    def generate_test_suite(self, project: Project) -> dict:
        """Generate a comprehensive test suite for the project."""
        self.logger.info(f"Generating test suite for project: {project.name}")
        
        test_suite = {}
        for story in project.stories:
            prompt = f"""Generate test cases for this user story:
            Title: {story.title}
            Description: {story.description}
            
            Include:
            - Unit tests
            - Integration tests
            - End-to-end tests
            - Edge cases
            - Performance tests
            """
            
            test_cases = self.generate_response(prompt)
            test_suite[story.id] = {
                "story": story.to_dict(),
                "test_cases": test_cases
            }
            
        return test_suite
    
    def run_tests(self, test_suite: dict) -> dict:
        """Run the test suite and generate a test report."""
        self.logger.info("Running test suite")
        
        total_tests = 0
        passed_tests = 0
        test_results = {}
        
        for story_id, details in test_suite.items():
            prompt = f"""Execute and evaluate these test cases:
            {details['test_cases']}
            
            Provide:
            - Pass/fail status
            - Error messages
            - Performance metrics
            """
            
            results = self.generate_response(prompt)
            
            # Parse results
            story_total = len(results.split("\n"))
            story_passed = len([r for r in results.split("\n") if "PASS" in r])
            
            total_tests += story_total
            passed_tests += story_passed
            
            test_results[story_id] = {
                "story": details['story'],
                "results": results,
                "passed": story_passed,
                "total": story_total
            }
        
        coverage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "passed": passed_tests == total_tests,
            "coverage": coverage,
            "report": test_results
        }