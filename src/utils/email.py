"""Email notification system."""
import os
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from jinja2 import Environment, PackageLoader, select_autoescape

# Load email templates
env = Environment(
    loader=PackageLoader("src", "templates/email"),
    autoescape=select_autoescape(["html", "xml"])
)

# Email configuration
email_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@aidevteam.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_TLS=True,
    MAIL_SSL=False,
    USE_CREDENTIALS=True
)

# Initialize FastMail
fastmail = FastMail(email_config)

async def send_email(
    recipients: List[EmailStr],
    subject: str,
    template_name: str,
    template_data: dict,
    cc: Optional[List[EmailStr]] = None,
    bcc: Optional[List[EmailStr]] = None
) -> None:
    """Send an email using a template.
    
    Args:
        recipients: List of recipient email addresses
        subject: Email subject
        template_name: Name of the template to use
        template_data: Data to pass to the template
        cc: List of CC email addresses
        bcc: List of BCC email addresses
    """
    # Load template
    template = env.get_template(f"{template_name}.html")
    
    # Render HTML content
    html_content = template.render(**template_data)
    
    # Create message
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=html_content,
        cc=cc or [],
        bcc=bcc or [],
        subtype="html"
    )
    
    # Send email
    await fastmail.send_message(message)

async def send_subscription_created(
    organization_name: str,
    tier_name: str,
    admin_email: EmailStr,
    amount: float,
    next_billing_date: str
) -> None:
    """Send subscription created notification.
    
    Args:
        organization_name: Organization name
        tier_name: Subscription tier name
        admin_email: Admin email address
        amount: Subscription amount
        next_billing_date: Next billing date
    """
    await send_email(
        recipients=[admin_email],
        subject=f"Welcome to {tier_name} Plan - AI Dev Team",
        template_name="subscription_created",
        template_data={
            "organization_name": organization_name,
            "tier_name": tier_name,
            "amount": amount,
            "next_billing_date": next_billing_date
        }
    )

async def send_payment_failed(
    organization_name: str,
    admin_email: EmailStr,
    amount: float,
    retry_date: str
) -> None:
    """Send payment failed notification.
    
    Args:
        organization_name: Organization name
        admin_email: Admin email address
        amount: Failed payment amount
        retry_date: Next retry date
    """
    await send_email(
        recipients=[admin_email],
        subject=f"Payment Failed - Action Required - AI Dev Team",
        template_name="payment_failed",
        template_data={
            "organization_name": organization_name,
            "amount": amount,
            "retry_date": retry_date
        }
    )

async def send_invoice_paid(
    organization_name: str,
    admin_email: EmailStr,
    amount: float,
    invoice_number: str,
    payment_date: str
) -> None:
    """Send invoice paid notification.
    
    Args:
        organization_name: Organization name
        admin_email: Admin email address
        amount: Payment amount
        invoice_number: Invoice number
        payment_date: Payment date
    """
    await send_email(
        recipients=[admin_email],
        subject=f"Payment Received - Invoice {invoice_number} - AI Dev Team",
        template_name="invoice_paid",
        template_data={
            "organization_name": organization_name,
            "amount": amount,
            "invoice_number": invoice_number,
            "payment_date": payment_date
        }
    )

async def send_usage_warning(
    organization_name: str,
    admin_email: EmailStr,
    metric: str,
    current_usage: int,
    limit: int
) -> None:
    """Send usage warning notification.
    
    Args:
        organization_name: Organization name
        admin_email: Admin email address
        metric: Usage metric name
        current_usage: Current usage value
        limit: Usage limit
    """
    await send_email(
        recipients=[admin_email],
        subject=f"Usage Warning - {metric} - AI Dev Team",
        template_name="usage_warning",
        template_data={
            "organization_name": organization_name,
            "metric": metric,
            "current_usage": current_usage,
            "limit": limit,
            "percentage": round((current_usage / limit) * 100, 1)
        }
    ) 