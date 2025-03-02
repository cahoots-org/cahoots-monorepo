"""Email client for sending emails using SMTP or AWS SES."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Union

import boto3
from botocore.exceptions import BotoCoreError

logger = logging.getLogger(__name__)


class EmailClientError(Exception):
    """Base exception for email client errors."""

    pass


class SendError(EmailClientError):
    """Exception raised for email sending errors."""

    pass


class ConfigurationError(EmailClientError):
    """Exception raised for configuration errors."""

    pass


class EmailClient:
    """Client for sending emails using SMTP or AWS SES."""

    def __init__(
        self,
        provider: str = "smtp",
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_use_tls: bool = True,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: Optional[str] = None,
        default_sender: Optional[str] = None,
    ):
        """Initialize the email client.

        Args:
            provider: Email provider ("smtp" or "ses")
            smtp_host: SMTP host (required for SMTP)
            smtp_port: SMTP port (required for SMTP)
            smtp_username: SMTP username (optional)
            smtp_password: SMTP password (optional)
            smtp_use_tls: Whether to use TLS for SMTP
            aws_access_key_id: AWS access key ID (required for SES)
            aws_secret_access_key: AWS secret access key (required for SES)
            aws_region: AWS region (required for SES)
            default_sender: Default sender email address

        Raises:
            ConfigurationError: If required configuration is missing
        """
        self.provider = provider.lower()
        self.default_sender = default_sender

        if self.provider == "smtp":
            if not smtp_host or not smtp_port:
                raise ConfigurationError("SMTP host and port are required for SMTP provider")
            self.smtp_config = {
                "host": smtp_host,
                "port": smtp_port,
                "username": smtp_username,
                "password": smtp_password,
                "use_tls": smtp_use_tls,
            }

        elif self.provider == "ses":
            if not aws_access_key_id or not aws_secret_access_key or not aws_region:
                raise ConfigurationError("AWS credentials and region are required for SES provider")
            self.ses_client = boto3.client(
                "ses",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region,
            )

        else:
            raise ConfigurationError(f"Unsupported email provider: {provider}")

    async def send_email(
        self,
        to_addresses: Union[str, List[str]],
        subject: str,
        body: str,
        from_address: Optional[str] = None,
        cc_addresses: Optional[Union[str, List[str]]] = None,
        bcc_addresses: Optional[Union[str, List[str]]] = None,
        is_html: bool = False,
        reply_to: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Send an email.

        Args:
            to_addresses: Recipient email address(es)
            subject: Email subject
            body: Email body
            from_address: Sender email address (defaults to default_sender)
            cc_addresses: CC recipient(s)
            bcc_addresses: BCC recipient(s)
            is_html: Whether body is HTML
            reply_to: Reply-to address(es)
            attachments: List of attachment dictionaries with keys:
                - filename: Attachment filename
                - content: Attachment content
                - content_type: MIME type

        Returns:
            True if email sent successfully

        Raises:
            SendError: If email sending fails
            ConfigurationError: If sender address not specified
        """
        # Validate sender
        sender = from_address or self.default_sender
        if not sender:
            raise ConfigurationError("Sender email address not specified")

        # Convert single addresses to lists
        if isinstance(to_addresses, str):
            to_addresses = [to_addresses]
        if isinstance(cc_addresses, str):
            cc_addresses = [cc_addresses]
        if isinstance(bcc_addresses, str):
            bcc_addresses = [bcc_addresses]
        if isinstance(reply_to, str):
            reply_to = [reply_to]

        try:
            if self.provider == "smtp":
                return await self._send_smtp(
                    sender=sender,
                    to_addresses=to_addresses,
                    subject=subject,
                    body=body,
                    cc_addresses=cc_addresses,
                    bcc_addresses=bcc_addresses,
                    is_html=is_html,
                    reply_to=reply_to,
                    attachments=attachments,
                )
            else:  # ses
                return await self._send_ses(
                    sender=sender,
                    to_addresses=to_addresses,
                    subject=subject,
                    body=body,
                    cc_addresses=cc_addresses,
                    bcc_addresses=bcc_addresses,
                    is_html=is_html,
                    reply_to=reply_to,
                    attachments=attachments,
                )

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise SendError(f"Failed to send email: {str(e)}")

    async def _send_smtp(
        self,
        sender: str,
        to_addresses: List[str],
        subject: str,
        body: str,
        cc_addresses: Optional[List[str]] = None,
        bcc_addresses: Optional[List[str]] = None,
        is_html: bool = False,
        reply_to: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Send email using SMTP."""
        # Create message
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(to_addresses)
        msg["Subject"] = subject

        if cc_addresses:
            msg["Cc"] = ", ".join(cc_addresses)
        if reply_to:
            msg["Reply-To"] = ", ".join(reply_to)

        # Add body
        content_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, content_type))

        # Add attachments
        if attachments:
            for attachment in attachments:
                part = MIMEText(attachment["content"], _subtype=attachment["content_type"])
                part.add_header(
                    "Content-Disposition", "attachment", filename=attachment["filename"]
                )
                msg.attach(part)

        # Send email
        with smtplib.SMTP(self.smtp_config["host"], self.smtp_config["port"]) as server:
            if self.smtp_config["use_tls"]:
                server.starttls()

            if self.smtp_config["username"] and self.smtp_config["password"]:
                server.login(self.smtp_config["username"], self.smtp_config["password"])

            recipients = to_addresses
            if cc_addresses:
                recipients.extend(cc_addresses)
            if bcc_addresses:
                recipients.extend(bcc_addresses)

            server.sendmail(sender, recipients, msg.as_string())

        logger.info(f"Sent email via SMTP to {', '.join(to_addresses)}")
        return True

    async def _send_ses(
        self,
        sender: str,
        to_addresses: List[str],
        subject: str,
        body: str,
        cc_addresses: Optional[List[str]] = None,
        bcc_addresses: Optional[List[str]] = None,
        is_html: bool = False,
        reply_to: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Send email using AWS SES."""
        try:
            # Prepare message
            message = {"Subject": {"Data": subject}, "Body": {}}

            if is_html:
                message.get("Body", {}).setdefault("Html", {}).setdefault("Data", body)
            else:
                message.get("Body", {}).setdefault("Text", {}).setdefault("Data", body)

            # Prepare destination
            destination = {"ToAddresses": to_addresses}
            if cc_addresses:
                destination["CcAddresses"] = cc_addresses
            if bcc_addresses:
                destination["BccAddresses"] = bcc_addresses

            # Send email
            kwargs = {"Source": sender, "Destination": destination, "Message": message}

            if reply_to:
                kwargs["ReplyToAddresses"] = reply_to

            self.ses_client.send_email(**kwargs)

            logger.info(f"Sent email via SES to {', '.join(to_addresses)}")
            return True

        except BotoCoreError as e:
            logger.error(f"SES error: {str(e)}")
            raise SendError(f"SES error: {str(e)}")


# Global client instance
_email_client: Optional[EmailClient] = None


def get_email_client(
    provider: str = "smtp",
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_username: Optional[str] = None,
    smtp_password: Optional[str] = None,
    smtp_use_tls: bool = True,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region: Optional[str] = None,
    default_sender: Optional[str] = None,
) -> EmailClient:
    """Get or create the global email client instance.

    Args:
        provider: Email provider ("smtp" or "ses")
        smtp_host: SMTP host (required for SMTP)
        smtp_port: SMTP port (required for SMTP)
        smtp_username: SMTP username (optional)
        smtp_password: SMTP password (optional)
        smtp_use_tls: Whether to use TLS for SMTP
        aws_access_key_id: AWS access key ID (required for SES)
        aws_secret_access_key: AWS secret access key (required for SES)
        aws_region: AWS region (required for SES)
        default_sender: Default sender email address

    Returns:
        EmailClient instance
    """
    global _email_client
    if _email_client is None:
        _email_client = EmailClient(
            provider=provider,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_use_tls=smtp_use_tls,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            default_sender=default_sender,
        )
    return _email_client
