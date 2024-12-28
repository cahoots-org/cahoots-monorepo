# src/agents/project_manager.py
from .base_agent import BaseAgent
from ..services.trello_service import TrelloService
from ..models.project import Project
from ..models.story import Story

class ProjectManager(BaseAgent):
    def __init__(self):
        super().__init__("gpt2-large")
        self.trello = TrelloService()
        
    def process_message(self, message: dict) -> dict:
        self.logger.info(f"Processing message type: {message['type']}")
        
        if message["type"] == "new_project":
            return self.handle_new_project(message)
        elif message["type"] == "project_complete":
            return self.handle_project_complete(message)
        
        return {"status": "error", "message": "Unknown message type"}
    
    def handle_new_project(self, message: dict) -> dict:
        roadmap = self.create_roadmap(message["description"])
        requirements = self.create_requirements(roadmap)
        board = self.trello.create_board(message["project_name"])
        stories = self.create_stories(requirements)
        
        for story in stories:
            self.trello.add_story_to_board(board, story)
            
        return {
            "status": "success",
            "roadmap": roadmap,
            "requirements": requirements,
            "board_url": board.url
        }
    
    def handle_project_complete(self, message: dict) -> dict:
        project = Project.from_dict(message["project"])
        review_result = self.review_project(project)
        
        if review_result["approved"]:
            return {"status": "success", "message": "Project approved"}
        else:
            return {
                "status": "revision_needed",
                "feedback": review_result["feedback"]
            }