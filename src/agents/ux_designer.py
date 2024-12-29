# src/agents/ux_designer.py
from .base_agent import BaseAgent
from ..models.task import Task

class UXDesigner(BaseAgent):
    def __init__(self):
        super().__init__("gpt2-large")
        
    def process_message(self, message: dict) -> dict:
        self.logger.info(f"Processing message type: {message['type']}")
        
        if message["type"] == "design_request":
            return self.handle_design_request(message)
            
        return {"status": "error", "message": "Unknown message type"}
    
    def handle_design_request(self, message: dict) -> dict:
        task = Task.from_dict(message["task"])
        design_specs = self.create_design_specs(task)
        mockups = self.create_mockups(design_specs)
        
        return {
            "status": "success",
            "design_specs": design_specs,
            "mockups": mockups
        }
    
    def create_design_specs(self, task: Task) -> dict:
        """Create design specifications for a task."""
        self.logger.info(f"Creating design specs for task: {task.title}")
        
        prompt = f"""Create detailed UX design specifications for:
        Task: {task.title}
        Description: {task.description}
        
        Include:
        - User flow
        - Component hierarchy
        - Interaction patterns
        - Accessibility requirements
        """
        
        specs_response = self.generate_response(prompt)
        
        return {
            "task_id": task.id,
            "specifications": specs_response
        }
    
    def create_mockups(self, design_specs: dict) -> dict:
        """Create UI mockups based on design specifications."""
        self.logger.info(f"Creating mockups for task: {design_specs['task_id']}")
        
        prompt = f"""Create UI mockup descriptions based on these specifications:
        {design_specs['specifications']}
        
        Include:
        - Layout details
        - Color schemes
        - Typography
        - Component styling
        """
        
        mockups_response = self.generate_response(prompt)
        
        return {
            "task_id": design_specs['task_id'],
            "mockups": mockups_response
        }