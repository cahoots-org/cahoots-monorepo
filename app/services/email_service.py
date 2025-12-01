"""Email service for sending notifications."""

import os
import logging
from typing import List, Optional
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: List[str]
    subject: str
    html: str
    from_email: Optional[str] = None
    reply_to: Optional[str] = None


class EmailService:
    """Email service supporting multiple providers."""

    def __init__(self):
        self.provider = os.getenv("EMAIL_PROVIDER", "resend")
        self.api_key = os.getenv("EMAIL_API_KEY", "")
        self.from_email = os.getenv("EMAIL_FROM", "Cahoots <noreply@cahoots.cc>")
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.warning("[EmailService] No EMAIL_API_KEY set - emails will be logged but not sent")

    async def send(self, message: EmailMessage) -> bool:
        """Send an email."""
        from_email = message.from_email or self.from_email

        if not self.enabled:
            logger.info(f"[EmailService] Would send email to {message.to}: {message.subject}")
            return True

        try:
            if self.provider == "resend":
                return await self._send_resend(message, from_email)
            else:
                logger.error(f"[EmailService] Unknown provider: {self.provider}")
                return False
        except Exception as e:
            logger.error(f"[EmailService] Failed to send email: {e}")
            return False

    async def _send_resend(self, message: EmailMessage, from_email: str) -> bool:
        """Send email via Resend API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": from_email,
                    "to": message.to,
                    "subject": message.subject,
                    "html": message.html,
                    **({"reply_to": message.reply_to} if message.reply_to else {})
                }
            )

            if response.status_code == 200:
                logger.info(f"[EmailService] Email sent to {message.to}")
                return True
            else:
                logger.error(f"[EmailService] Resend API error: {response.status_code} - {response.text}")
                return False

    async def send_blog_notification(
        self,
        to_emails: List[str],
        post_title: str,
        post_excerpt: str,
        post_url: str
    ) -> int:
        """Send blog post notification to subscribers. Returns count of emails sent."""
        if not to_emails:
            return 0

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">New from Cahoots</h1>
            </div>
            <div style="background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
                <h2 style="color: #1f2937; margin-top: 0;">{post_title}</h2>
                <p style="color: #4b5563;">{post_excerpt}</p>
                <a href="{post_url}" style="display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500; margin-top: 10px;">Read More</a>
            </div>
            <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
                <p>You're receiving this because you subscribed to Cahoots blog updates.</p>
                <p><a href="https://cahoots.cc/blog/unsubscribe" style="color: #9ca3af;">Unsubscribe</a></p>
            </div>
        </body>
        </html>
        """

        sent_count = 0
        # Send individually to avoid exposing emails to each other
        for email in to_emails:
            message = EmailMessage(
                to=[email],
                subject=f"New Post: {post_title}",
                html=html
            )
            if await self.send(message):
                sent_count += 1

        return sent_count


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
