"""Mock notification services for tests"""
from typing import Dict, List


class MockEmailService:
    """Mock email service for tests"""
    
    def __init__(self):
        """Initialize the mock email service"""
        self.sent_emails = []
    
    def send_verification_email(self, email, token):
        """Send a verification email"""
        self.sent_emails.append({
            'type': 'verification',
            'to': email,
            'token': token
        })
    
    def send_password_reset_email(self, email, token):
        """Send a password reset email"""
        self.sent_emails.append({
            'type': 'password_reset',
            'to': email,
            'token': token
        })
    
    def send_notification_email(self, email, subject, body):
        """Send a notification email"""
        self.sent_emails.append({
            'type': 'notification',
            'to': email,
            'subject': subject,
            'body': body
        })
    
    def send_welcome_email(self, email: str) -> None:
        """Send a welcome email (mock)"""
        self.sent_emails.append({
            'to': email,
            'type': 'welcome'
        }) 