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