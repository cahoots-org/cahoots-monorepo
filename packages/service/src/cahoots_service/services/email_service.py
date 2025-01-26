"""Email service for user communications."""
from typing import Optional
from pydantic import EmailStr
from jinja2 import Environment, PackageLoader

from cahoots_service.utils.config import ServiceConfig
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

class EmailService:
    """Service for sending system emails."""
    
    def __init__(self):
        """Initialize email service with configuration."""
        self.config = ConnectionConfig(
            MAIL_USERNAME=ServiceConfig.smtp_user,
            MAIL_PASSWORD=ServiceConfig.smtp_password,
            MAIL_FROM=ServiceConfig.smtp_from_email,
            MAIL_PORT=ServiceConfig.smtp_port,
            MAIL_SERVER=ServiceConfig.smtp_host,
            MAIL_SSL_TLS=ServiceConfig.smtp_use_tls,
            USE_CREDENTIALS=True
        )
        self.fastmail = FastMail(self.config)
        self.templates = Environment(
            loader=PackageLoader('src', 'templates/email')
        )
    
    async def send_verification_email(self, email: EmailStr, token: str):
        """Send account verification email.
        
        Args:
            email: User's email address
            token: Verification token
        """
        template = self.templates.get_template('verify_email.html')
        verify_url = f"{ServiceConfig.frontend_url}/verify-email?token={token}"
        
        html = template.render(
            verify_url=verify_url
        )
        
        message = MessageSchema(
            subject="Verify Your Email Address",
            recipients=[email],
            body=html,
            subtype="html"
        )
        
        await self.fastmail.send_message(message)
    
    async def send_password_reset_email(self, email: EmailStr, token: str):
        """Send password reset email.
        
        Args:
            email: User's email address
            token: Password reset token
        """
        template = self.templates.get_template('reset_password.html')
        reset_url = f"{ServiceConfig.frontend_url}/reset-password?token={token}"
        
        html = template.render(
            reset_url=reset_url
        )
        
        message = MessageSchema(
            subject="Reset Your Password",
            recipients=[email],
            body=html,
            subtype="html"
        )
        
        await self.fastmail.send_message(message)
    
    async def send_welcome_email(self, email: EmailStr, name: str):
        """Send welcome email after verification.
        
        Args:
            email: User's email address
            name: User's full name
        """
        template = self.templates.get_template('welcome.html')
        html = template.render(name=name)
        
        message = MessageSchema(
            subject="Welcome to Cahoots!",
            recipients=[email],
            body=html,
            subtype="html"
        )
        
        await self.fastmail.send_message(message) 