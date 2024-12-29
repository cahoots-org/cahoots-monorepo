# src/agents/project_manager.py
from .base_agent import BaseAgent
from ..services.trello_service import TrelloService
from ..models.project import Project
from ..models.story import Story
from typing import List

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
    
    def create_roadmap(self, description: str) -> dict:
        """Create a project roadmap based on the project description."""
        self.logger.info("Creating project roadmap")
        
        prompt = f"""Create a detailed project roadmap based on this description:
        {description}
        
        Include:
        - Project phases
        - Major milestones
        - Timeline estimates
        - Dependencies
        """
        
        roadmap_response = self.generate_response(prompt)
        
        return {
            "phases": roadmap_response.split("\n"),
            "raw": roadmap_response
        }
    
    def create_requirements(self, roadmap: dict) -> dict:
        """Create detailed requirements based on the roadmap."""
        self.logger.info("Creating project requirements")
        
        prompt = f"""Create detailed requirements based on this roadmap:
        {roadmap['raw']}
        
        Include:
        - Functional requirements
        - Technical requirements
        - Non-functional requirements
        - Constraints
        """
        
        requirements_response = self.generate_response(prompt)
        
        return {
            "requirements": requirements_response.split("\n"),
            "raw": requirements_response
        }
    
    def create_stories(self, requirements: dict) -> List[Story]:
        """Create user stories based on requirements."""
        self.logger.info("Creating user stories")
        
        prompt = f"""Create user stories based on these requirements:
        {requirements['raw']}
        
        Format each story as:
        Title: <title>
        Description: <description>
        ---
        """
        
        stories_response = self.generate_response(prompt)
        
        # Parse stories from response
        stories = []
        story_texts = stories_response.split("---")
        
        for i, story_text in enumerate(story_texts):
            if not story_text.strip():
                continue
                
            # Parse title and description
            lines = story_text.strip().split("\n")
            title = lines[0].replace("Title:", "").strip()
            description = "\n".join(lines[1:]).replace("Description:", "").strip()
            
            story = Story(
                id=f"story_{i}",
                title=title,
                description=description
            )
            stories.append(story)
        
        return stories
    
    def review_project(self, project: Project) -> dict:
        """Review the completed project."""
        self.logger.info(f"Reviewing project: {project.name}")
        
        prompt = f"""Review this project for completion and quality:
        Name: {project.name}
        Description: {project.description}
        Stories: {len(project.stories)} total
        
        Check for:
        - All requirements met
        - Code quality
        - Documentation
        - Test coverage
        """
        
        review_response = self.generate_response(prompt)
        
        # Determine if project is approved
        approved = "approved" in review_response.lower() or "complete" in review_response.lower()
        
        return {
            "approved": approved,
            "feedback": review_response
        }