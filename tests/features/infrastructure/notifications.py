"""Mock notification services for tests"""
from typing import Dict, List


class MockEmailService:
    """Mock email service that stores sent emails in memory"""
    
    def __init__(self):
        """Initialize the email service"""
        self.sent_emails = []
    
    def send_verification_email(self, email: str, token: str) -> None:
        """Send a verification email (mock)"""
        self.sent_emails.append({
            'to': email,
            'type': 'verification',
            'token': token
        })
    
    def send_password_reset_email(self, email: str, token: str) -> None:
        """Send a password reset email (mock)"""
        self.sent_emails.append({
            'to': email,
            'type': 'reset',
            'token': token
        })
    
    def send_welcome_email(self, email: str) -> None:
        """Send a welcome email (mock)"""
        self.sent_emails.append({
            'to': email,
            'type': 'welcome'
        }) 