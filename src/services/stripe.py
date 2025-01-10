"""Stripe service for handling payments and subscriptions."""
import os
from typing import Dict, Any
import stripe

# Initialize Stripe client
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

async def create_customer(
    organization_id: str,
    email: str,
    name: str
) -> Dict[str, Any]:
    """Create a new Stripe customer.
    
    Args:
        organization_id: Organization ID
        email: Customer email
        name: Customer name
        
    Returns:
        Dict[str, Any]: Created customer data
    """
    customer = stripe.Customer.create(
        email=email,
        name=name,
        metadata={
            "organization_id": organization_id
        }
    )
    return customer 