"""Stripe service implementation."""
from typing import List, Optional, Dict, Any
import stripe
from fastapi import Depends
from src.utils.config import get_settings

class StripeClient:
    """Stripe client wrapper."""

    def __init__(self, api_key: str):
        """Initialize Stripe client.
        
        Args:
            api_key: Stripe API key
        """
        self.stripe = stripe
        self.stripe.api_key = api_key

    def construct_event(self, payload: bytes, sig_header: str) -> stripe.Event:
        """Construct Stripe event from webhook payload.
        
        Args:
            payload: Request body
            sig_header: Stripe signature header
            
        Returns:
            Stripe event
            
        Raises:
            ValueError: If signature verification fails
        """
        return stripe.Webhook.construct_event(
            payload,
            sig_header,
            get_settings().stripe_webhook_secret
        )

    def create_customer(self, email: str, name: str) -> stripe.Customer:
        """Create Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name
            
        Returns:
            Created customer
        """
        return stripe.Customer.create(
            email=email,
            name=name
        )

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        payment_method_id: Optional[str] = None
    ) -> stripe.Subscription:
        """Create subscription for customer.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            payment_method_id: Optional payment method ID
            
        Returns:
            Created subscription
        """
        subscription_data = {
            "customer": customer_id,
            "items": [{"price": price_id}],
            "expand": ["latest_invoice.payment_intent"]
        }

        if payment_method_id:
            subscription_data["default_payment_method"] = payment_method_id

        return stripe.Subscription.create(**subscription_data)

    def get_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Get subscription by ID.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            Subscription object
        """
        return stripe.Subscription.retrieve(subscription_id)

    def update_subscription(
        self,
        subscription_id: str,
        price_id: str
    ) -> stripe.Subscription:
        """Update subscription price.
        
        Args:
            subscription_id: Stripe subscription ID
            price_id: New price ID
            
        Returns:
            Updated subscription
        """
        subscription = stripe.Subscription.retrieve(subscription_id)
        return stripe.Subscription.modify(
            subscription_id,
            items=[{
                "id": subscription["items"]["data"][0].id,
                "price": price_id,
            }]
        )

    def cancel_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Cancel subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            Canceled subscription
        """
        return stripe.Subscription.delete(subscription_id)

    def list_payment_methods(
        self,
        customer_id: str,
        type: str = "card"
    ) -> List[stripe.PaymentMethod]:
        """List customer payment methods.
        
        Args:
            customer_id: Stripe customer ID
            type: Payment method type
            
        Returns:
            List of payment methods
        """
        return stripe.PaymentMethod.list(
            customer=customer_id,
            type=type
        )

    def attach_payment_method(
        self,
        payment_method_id: str,
        customer_id: str
    ) -> stripe.PaymentMethod:
        """Attach payment method to customer.
        
        Args:
            payment_method_id: Payment method ID
            customer_id: Customer ID
            
        Returns:
            Attached payment method
        """
        return stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id
        )

    def detach_payment_method(self, payment_method_id: str) -> stripe.PaymentMethod:
        """Detach payment method from customer.
        
        Args:
            payment_method_id: Payment method ID
            
        Returns:
            Detached payment method
        """
        return stripe.PaymentMethod.detach(payment_method_id)

    def get_invoice(self, invoice_id: str) -> stripe.Invoice:
        """Get invoice by ID.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Invoice object
        """
        return stripe.Invoice.retrieve(invoice_id)

    def list_invoices(self, customer_id: str) -> List[stripe.Invoice]:
        """List customer invoices.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            List of invoices
        """
        return stripe.Invoice.list(customer=customer_id)

    def pay_invoice(self, invoice_id: str) -> stripe.Invoice:
        """Pay invoice.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Paid invoice
        """
        return stripe.Invoice.pay(invoice_id)

    def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> stripe.billing_portal.Session:
        """Create billing portal session.
        
        Args:
            customer_id: Customer ID
            return_url: Return URL after closing portal
            
        Returns:
            Billing portal session
        """
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )

    async def get_subscription_usage(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription usage details.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            Usage details
            
        Raises:
            ValueError: If subscription not found
        """
        subscription = stripe.Subscription.retrieve(subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
            
        # Get subscription item
        item = subscription.items.data[0]
        
        # Get usage record
        usage_record = stripe.SubscriptionItem.list_usage_record_summaries(
            item.id,
            limit=1
        ).data[0]
        
        # Get billing period
        current_period_start = subscription.current_period_start
        current_period_end = subscription.current_period_end
        
        return {
            "subscription": subscription_id,
            "total_usage": usage_record.total_usage,
            "quota": {
                "limit": item.plan.usage_limit or 0
            },
            "period": {
                "start": current_period_start,
                "end": current_period_end
            }
        }

def get_stripe_client(settings=Depends(get_settings)) -> StripeClient:
    """Get Stripe client instance.
    
    Args:
        settings: Application settings
        
    Returns:
        Stripe client instance
    """
    return StripeClient(settings.stripe_api_key) 