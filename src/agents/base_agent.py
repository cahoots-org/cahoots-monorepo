# src/agents/base_agent.py
from abc import ABC, abstractmethod
from transformers import AutoModelForCausalLM, AutoTokenizer
from ..utils.logger import Logger

class BaseAgent(ABC):
    def __init__(self, model_name: str):
        self.logger = Logger(self.__class__.__name__)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
    @abstractmethod
    def process_message(self, message: dict) -> dict:
        pass
    
    def generate_response(self, prompt: str) -> str:
        self.logger.info(f"Generating response for prompt: {prompt[:50]}...")
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(**inputs)
        response = self.tokenizer.decode(outputs[0])
        self.logger.info("Response generated successfully")
        return response