"""Stripe client for managing payments and subscriptions."""

import logging
from typing import Any, Dict, List, Optional

import stripe
from stripe import StripeError

logger = logging.getLogger(__name__)


class StripeClientError(Exception):
    """Base exception for Stripe client errors."""

    pass


class PaymentError(StripeClientError):
    """Exception raised for payment errors."""

    pass


class SubscriptionError(StripeClientError):
    """Exception raised for subscription errors."""

    pass


class CustomerError(StripeClientError):
    """Exception raised for customer errors."""

    pass


class StripeClient:
    """Client for interacting with Stripe API."""

    def __init__(self, api_key: str):
        """Initialize the Stripe client.

        Args:
            api_key: Stripe API key
        """
        stripe.api_key = api_key

    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe customer.

        Args:
            email: Customer email
            name: Optional customer name
            description: Optional customer description
            metadata: Optional metadata

        Returns:
            Created customer object

        Raises:
            CustomerError: If customer creation fails
        """
        try:
            customer = stripe.Customer.create(
                email=email, name=name, description=description, metadata=metadata
            )

            logger.info(f"Created Stripe customer: {customer.id}")
            return customer

        except StripeError as e:
            logger.error(f"Failed to create customer: {str(e)}")
            raise CustomerError(f"Failed to create customer: {str(e)}")

    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get a Stripe customer.

        Args:
            customer_id: Stripe customer ID

        Returns:
            Customer object

        Raises:
            CustomerError: If customer retrieval fails
        """
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer

        except StripeError as e:
            logger.error(f"Failed to get customer {customer_id}: {str(e)}")
            raise CustomerError(f"Failed to get customer {customer_id}: {str(e)}")

    async def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Update a Stripe customer.

        Args:
            customer_id: Stripe customer ID
            email: Optional new email
            name: Optional new name
            description: Optional new description
            metadata: Optional new metadata

        Returns:
            Updated customer object

        Raises:
            CustomerError: If customer update fails
        """
        try:
            updates = {}
            if email is not None:
                updates["email"] = email
            if name is not None:
                updates["name"] = name
            if description is not None:
                updates["description"] = description
            if metadata is not None:
                updates["metadata"] = metadata

            customer = stripe.Customer.modify(customer_id, **updates)

            logger.info(f"Updated Stripe customer: {customer.id}")
            return customer

        except StripeError as e:
            logger.error(f"Failed to update customer {customer_id}: {str(e)}")
            raise CustomerError(f"Failed to update customer {customer_id}: {str(e)}")

    async def delete_customer(self, customer_id: str) -> bool:
        """Delete a Stripe customer.

        Args:
            customer_id: Stripe customer ID

        Returns:
            True if deleted, False if customer not found

        Raises:
            CustomerError: If customer deletion fails
        """
        try:
            deleted = stripe.Customer.delete(customer_id)

            logger.info(f"Deleted Stripe customer: {customer_id}")
            return deleted.deleted

        except StripeError as e:
            logger.error(f"Failed to delete customer {customer_id}: {str(e)}")
            raise CustomerError(f"Failed to delete customer {customer_id}: {str(e)}")

    async def create_payment_method(
        self, customer_id: str, card_number: str, exp_month: int, exp_year: int, cvc: str
    ) -> Dict[str, Any]:
        """Create a payment method for a customer.

        Args:
            customer_id: Stripe customer ID
            card_number: Card number
            exp_month: Card expiry month
            exp_year: Card expiry year
            cvc: Card CVC

        Returns:
            Created payment method object

        Raises:
            PaymentError: If payment method creation fails
        """
        try:
            payment_method = stripe.PaymentMethod.create(
                type="card",
                card={
                    "number": card_number,
                    "exp_month": exp_month,
                    "exp_year": exp_year,
                    "cvc": cvc,
                },
            )

            # Attach payment method to customer
            payment_method = stripe.PaymentMethod.attach(payment_method.id, customer=customer_id)

            logger.info(
                f"Created payment method {payment_method.id} " f"for customer {customer_id}"
            )
            return payment_method

        except StripeError as e:
            logger.error(f"Failed to create payment method: {str(e)}")
            raise PaymentError(f"Failed to create payment method: {str(e)}")

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        payment_method_id: Optional[str] = None,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a subscription for a customer.

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            payment_method_id: Optional payment method ID
            trial_days: Optional trial period in days
            metadata: Optional metadata

        Returns:
            Created subscription object

        Raises:
            SubscriptionError: If subscription creation fails
        """
        try:
            subscription_data = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata,
            }

            if payment_method_id:
                subscription_data["default_payment_method"] = payment_method_id

            if trial_days:
                subscription_data["trial_period_days"] = trial_days

            subscription = stripe.Subscription.create(**subscription_data)

            logger.info(f"Created subscription {subscription.id} " f"for customer {customer_id}")
            return subscription

        except StripeError as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise SubscriptionError(f"Failed to create subscription: {str(e)}")

    async def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = False
    ) -> Dict[str, Any]:
        """Cancel a subscription.

        Args:
            subscription_id: Stripe subscription ID
            at_period_end: Whether to cancel at period end

        Returns:
            Cancelled subscription object

        Raises:
            SubscriptionError: If subscription cancellation fails
        """
        try:
            subscription = stripe.Subscription.modify(
                subscription_id, cancel_at_period_end=at_period_end
            )

            if not at_period_end:
                subscription = stripe.Subscription.delete(subscription_id)

            logger.info(f"Cancelled subscription: {subscription_id}")
            return subscription

        except StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {str(e)}")
            raise SubscriptionError(f"Failed to cancel subscription {subscription_id}: {str(e)}")

    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get a subscription.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription object

        Raises:
            SubscriptionError: If subscription retrieval fails
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription

        except StripeError as e:
            logger.error(f"Failed to get subscription {subscription_id}: {str(e)}")
            raise SubscriptionError(f"Failed to get subscription {subscription_id}: {str(e)}")

    async def list_subscriptions(
        self, customer_id: Optional[str] = None, status: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List subscriptions.

        Args:
            customer_id: Optional customer ID to filter by
            status: Optional status to filter by
            limit: Maximum number of subscriptions to return

        Returns:
            List of subscription objects

        Raises:
            SubscriptionError: If subscription listing fails
        """
        try:
            filters = {"limit": limit}
            if customer_id:
                filters["customer"] = customer_id
            if status:
                filters["status"] = status

            subscriptions = stripe.Subscription.list(**filters)
            return subscriptions.data

        except StripeError as e:
            logger.error(f"Failed to list subscriptions: {str(e)}")
            raise SubscriptionError(f"Failed to list subscriptions: {str(e)}")


# Global client instance
_stripe_client: Optional[StripeClient] = None


def get_stripe_client(api_key: str) -> StripeClient:
    """Get or create the global Stripe client instance.

    Args:
        api_key: Stripe API key

    Returns:
        StripeClient instance
    """
    global _stripe_client
    if _stripe_client is None:
        _stripe_client = StripeClient(api_key)
    return _stripe_client
