"""Stripe API client."""
from typing import Dict, Any, Optional
import stripe
from ..utils.config import config

class StripeClient:
    """Client for interacting with Stripe API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Stripe client.
        
        Args:
            api_key: Optional API key override. If not provided, uses config value.
        """
        stripe.api_key = api_key or config.stripe.secret_key.get_secret_value()
    
    async def create_subscription(
        self,
        customer_id: str,
        payment_method_id: str,
        price_id: str,
        trial_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new subscription.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_id: Payment method ID
            price_id: Price ID for subscription
            trial_days: Optional trial period in days
            
        Returns:
            Dict containing subscription details
            
        Raises:
            stripe.error.StripeError: For Stripe API errors
        """
        # Set default payment method
        await self.set_default_payment_method(customer_id, payment_method_id)
        
        # Create subscription
        subscription_data = {
            "customer": customer_id,
            "items": [{"price": price_id}],
            "default_payment_method": payment_method_id,
            "expand": ["latest_invoice.payment_intent"]
        }
        
        if trial_days:
            subscription_data["trial_period_days"] = trial_days
            
        subscription = stripe.Subscription.create(**subscription_data)
        
        return subscription
    
    async def add_payment_method(
        self,
        customer_id: str,
        payment_method_token: str,
        set_default: bool = True
    ) -> Dict[str, Any]:
        """Add a payment method to customer.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_token: Payment method token
            set_default: Whether to set as default payment method
            
        Returns:
            Dict containing payment method details
            
        Raises:
            stripe.error.StripeError: For Stripe API errors
        """
        # Attach payment method to customer
        payment_method = stripe.PaymentMethod.attach(
            payment_method_token,
            customer=customer_id
        )
        
        if set_default:
            await self.set_default_payment_method(customer_id, payment_method.id)
            
        return payment_method
    
    async def set_default_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Set default payment method for customer.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_id: Payment method ID
            
        Returns:
            Dict containing customer details
            
        Raises:
            stripe.error.StripeError: For Stripe API errors
        """
        return stripe.Customer.modify(
            customer_id,
            invoice_settings={
                "default_payment_method": payment_method_id
            }
        )
    
    async def list_invoices(
        self,
        customer_id: str,
        limit: int = 10,
        starting_after: Optional[str] = None
    ) -> Dict[str, Any]:
        """List customer invoices.
        
        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of invoices to return
            starting_after: Pagination cursor
            
        Returns:
            Dict containing list of invoices
            
        Raises:
            stripe.error.StripeError: For Stripe API errors
        """
        params = {
            "customer": customer_id,
            "limit": limit,
            "expand": ["data.subscription"]
        }
        
        if starting_after:
            params["starting_after"] = starting_after
            
        return stripe.Invoice.list(**params)
    
    async def get_usage(
        self,
        subscription_item_id: str,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get usage records for subscription item.
        
        Args:
            subscription_item_id: Subscription item ID
            start_date: Start timestamp
            end_date: End timestamp
            
        Returns:
            Dict containing usage records
            
        Raises:
            stripe.error.StripeError: For Stripe API errors
        """
        params = {}
        
        if start_date:
            params["timestamp"] = {"gte": start_date}
        if end_date:
            params["timestamp"] = {"lte": end_date}
            
        return stripe.SubscriptionItem.list_usage_record_summaries(
            subscription_item_id,
            **params
        )
    
    def construct_event(
        self,
        payload: bytes,
        signature: str
    ) -> stripe.Event:
        """Construct and verify webhook event.
        
        Args:
            payload: Raw request payload
            signature: Stripe signature header
            
        Returns:
            Verified Stripe event
            
        Raises:
            stripe.error.SignatureVerificationError: If webhook signature is invalid
        """
        return stripe.Webhook.construct_event(
            payload,
            signature,
            config.stripe.webhook_secret.get_secret_value()
        )
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        prorate: bool = True
    ) -> Dict[str, Any]:
        """Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID
            prorate: Whether to prorate charges
            
        Returns:
            Dict containing subscription details
            
        Raises:
            stripe.error.StripeError: For Stripe API errors
        """
        return stripe.Subscription.delete(
            subscription_id,
            prorate=prorate
        ) 