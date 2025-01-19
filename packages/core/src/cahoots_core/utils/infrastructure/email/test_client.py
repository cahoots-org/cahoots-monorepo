"""Unit tests for email client module."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import smtplib
from botocore.exceptions import BotoCoreError

from .client import (
    EmailClient,
    EmailClientError,
    SendError,
    ConfigurationError,
    get_email_client
)

@pytest.fixture
def smtp_config():
    """SMTP configuration."""
    return {
        "provider": "smtp",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "user",
        "smtp_password": "pass",
        "smtp_use_tls": True,
        "default_sender": "sender@example.com"
    }

@pytest.fixture
def ses_config():
    """AWS SES configuration."""
    return {
        "provider": "ses",
        "aws_access_key_id": "access_key",
        "aws_secret_access_key": "secret_key",
        "aws_region": "us-east-1",
        "default_sender": "sender@example.com"
    }

@pytest.fixture
def smtp_client(smtp_config):
    """Create an EmailClient instance with SMTP configuration."""
    return EmailClient(**smtp_config)

@pytest.fixture
def ses_client(ses_config):
    """Create an EmailClient instance with SES configuration."""
    with patch("boto3.client"):
        return EmailClient(**ses_config)

def test_init_smtp_missing_config():
    """Test SMTP initialization with missing configuration."""
    with pytest.raises(ConfigurationError, match="SMTP host and port are required"):
        EmailClient(provider="smtp")

def test_init_ses_missing_config():
    """Test SES initialization with missing configuration."""
    with pytest.raises(ConfigurationError, match="AWS credentials and region are required"):
        EmailClient(provider="ses")

def test_init_invalid_provider():
    """Test initialization with invalid provider."""
    with pytest.raises(ConfigurationError, match="Unsupported email provider"):
        EmailClient(provider="invalid")

@pytest.mark.asyncio
async def test_send_email_smtp_success(smtp_client):
    """Test successful email sending via SMTP."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        result = await smtp_client.send_email(
            to_addresses="recipient@example.com",
            subject="Test Subject",
            body="Test Body",
            cc_addresses="cc@example.com",
            bcc_addresses="bcc@example.com",
            is_html=True,
            reply_to="reply@example.com"
        )
        
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.sendmail.assert_called_once()
        
        # Verify recipients
        call_args = mock_server.sendmail.call_args
        assert call_args[0][0] == "sender@example.com"  # From
        assert set(call_args[0][1]) == {
            "recipient@example.com",
            "cc@example.com",
            "bcc@example.com"
        }

@pytest.mark.asyncio
async def test_send_email_smtp_failure(smtp_client):
    """Test failed email sending via SMTP."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_server.sendmail.side_effect = smtplib.SMTPException("Send failed")
        
        with pytest.raises(SendError, match="Failed to send email"):
            await smtp_client.send_email(
                to_addresses="recipient@example.com",
                subject="Test Subject",
                body="Test Body"
            )

@pytest.mark.asyncio
async def test_send_email_ses_success(ses_client):
    """Test successful email sending via SES."""
    mock_ses = Mock()
    ses_client.ses_client = mock_ses
    
    result = await ses_client.send_email(
        to_addresses="recipient@example.com",
        subject="Test Subject",
        body="Test Body",
        cc_addresses="cc@example.com",
        bcc_addresses="bcc@example.com",
        is_html=True,
        reply_to="reply@example.com"
    )
    
    assert result is True
    mock_ses.send_email.assert_called_once()
    
    # Verify email data
    call_args = mock_ses.send_email.call_args[1]
    assert call_args["Source"] == "sender@example.com"
    assert call_args["Destination"]["ToAddresses"] == ["recipient@example.com"]
    assert call_args["Destination"]["CcAddresses"] == ["cc@example.com"]
    assert call_args["Destination"]["BccAddresses"] == ["bcc@example.com"]
    assert call_args["Message"]["Subject"]["Data"] == "Test Subject"
    assert "Html" in call_args["Message"]["Body"]
    assert call_args["ReplyToAddresses"] == ["reply@example.com"]

@pytest.mark.asyncio
async def test_send_email_ses_failure(ses_client):
    """Test failed email sending via SES."""
    mock_ses = Mock()
    mock_ses.send_email.side_effect = BotoCoreError()
    ses_client.ses_client = mock_ses
    
    with pytest.raises(SendError, match="Failed to send email"):
        await ses_client.send_email(
            to_addresses="recipient@example.com",
            subject="Test Subject",
            body="Test Body"
        )

@pytest.mark.asyncio
async def test_send_email_no_sender(smtp_client):
    """Test email sending with no sender address."""
    smtp_client.default_sender = None
    
    with pytest.raises(ConfigurationError, match="Sender email address not specified"):
        await smtp_client.send_email(
            to_addresses="recipient@example.com",
            subject="Test Subject",
            body="Test Body"
        )

@pytest.mark.asyncio
async def test_send_email_with_attachments(smtp_client):
    """Test email sending with attachments."""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        attachments = [
            {
                "filename": "test.txt",
                "content": "Test content",
                "content_type": "text/plain"
            }
        ]
        
        result = await smtp_client.send_email(
            to_addresses="recipient@example.com",
            subject="Test Subject",
            body="Test Body",
            attachments=attachments
        )
        
        assert result is True
        mock_server.sendmail.assert_called_once()

def test_get_email_client():
    """Test global client instance creation."""
    with patch("packages.core.src.utils.infrastructure.email.client.EmailClient") as mock_client:
        client1 = get_email_client(
            provider="smtp",
            smtp_host="smtp.example.com",
            smtp_port=587
        )
        client2 = get_email_client(
            provider="smtp",
            smtp_host="smtp.example.com",
            smtp_port=587
        )
        
        # Should create only one instance
        mock_client.assert_called_once()
        assert client1 == client2 