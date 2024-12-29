# src/utils/config.py
import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        # GitHub configuration
        self.github_api_key = os.getenv("GITHUB_API_KEY")

        # Trello configuration
        self.trello_api_key = os.getenv("TRELLO_API_KEY")
        self.trello_api_secret = os.getenv("TRELLO_API_SECRET")

        # Service URLs
        self.pm_url = os.getenv("PM_SERVICE_URL", "http://localhost:8001")
        self.developer_url = os.getenv("DEVELOPER_SERVICE_URL", "http://localhost:8002")
        self.ux_url = os.getenv("UX_SERVICE_URL", "http://localhost:8003")
        self.tester_url = os.getenv("TESTER_SERVICE_URL", "http://localhost:8004")
        self.code_review_url = os.getenv("CODE_REVIEW_SERVICE_URL", "http://localhost:8005")