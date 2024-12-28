# src/services/huggingface_service.py
from transformers import AutoModelForCausalLM, AutoTokenizer
from ..utils.config import Config
from ..utils.logger import Logger

class HuggingFaceService:
    def __init__(self):
        self.config = Config()
        self.logger = Logger("HuggingFaceService")
        
    def load_model(self, model_name: str):
        self.logger.info(f"Loading model: {model_name}")
        model = AutoModelForCausalLM.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        return model, tokenizer