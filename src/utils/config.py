# src/utils/config.py
import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self._load_environment_files()
        
        self.github_token = os.getenv("GITHUB_API_KEY")
        self.trello_api_key = os.getenv("TRELLO_API_KEY")
        self.trello_api_secret = os.getenv("TRELLO_API_SECRET")
        self.huggingface_token = os.getenv("HUGGINGFACE_API_KEY")
        
        self.validate_config()
    
    def _load_environment_files(self):
        """Load environment files in order of precedence."""
        # Load base .env file first
        load_dotenv(dotenv_path=".env")
        
        # Load environment-specific file if ENV is set
        env = os.getenv("ENV", "local").lower()
        env_file = f".env.{env}"
        if os.path.exists(env_file):
            load_dotenv(dotenv_path=env_file, override=True)
        
    def validate_config(self):
        required_vars = [
            "GITHUB_API_KEY",
            "TRELLO_API_KEY",
            "TRELLO_API_SECRET",
            "HUGGINGFACE_API_KEY"
        ]
        
        missing = [var for var in required_vars if not getattr(self, var.lower())]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")