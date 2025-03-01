"""Authentication notification services"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailService(ABC):
    """Abstract base class for email services"""

    @abstractmethod
    def send_verification_email(self, email: str, verification_token: str) -> None:
        """Send email verification link"""
        pass

    @abstractmethod
    def send_password_reset_email(self, email: str, reset_token: str) -> None:
        """Send password reset link"""
        pass


class SMTPEmailService(EmailService):
    """SMTP implementation of email service"""

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str,
                 from_email: str, verification_url: str, reset_url: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.verification_url = verification_url
        self.reset_url = reset_url

    def _send_email(self, to_email: str, subject: str, body_html: str) -> None:
        """Send email via SMTP"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_email
        msg['To'] = to_email

        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)

    def send_verification_email(self, email: str, verification_token: str) -> None:
        """Send email verification link"""
        verification_link = f"{self.verification_url}?token={verification_token}"
        subject = "Verify your email address"
        body_html = f"""
        <html>
            <body>
                <h2>Welcome to our platform!</h2>
                <p>Please click the link below to verify your email address:</p>
                <p><a href="{verification_link}">{verification_link}</a></p>
                <p>This link will expire in 24 hours.</p>
            </body>
        </html>
        """
        self._send_email(email, subject, body_html)

    def send_password_reset_email(self, email: str, reset_token: str) -> None:
        """Send password reset link"""
        reset_link = f"{self.reset_url}?token={reset_token}"
        subject = "Reset your password"
        body_html = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Click the link below to reset your password:</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request this, please ignore this email.</p>
            </body>
        </html>
        """
        self._send_email(email, subject, body_html)


class MockEmailService(EmailService):
    """Mock email service for testing"""

    def __init__(self):
        self.sent_emails = []

    def send_verification_email(self, email: str, verification_token: str) -> None:
        """Record verification email"""
        self.sent_emails.append({
            'type': 'verification',
            'to': email,
            'token': verification_token
        })

    def send_password_reset_email(self, email: str, reset_token: str) -> None:
        """Record password reset email"""
        self.sent_emails.append({
            'type': 'reset',
            'to': email,
            'token': reset_token
        }) 