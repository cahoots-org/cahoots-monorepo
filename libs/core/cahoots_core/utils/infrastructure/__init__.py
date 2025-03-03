"""Infrastructure package for managing external services and resources."""

from .database.client import Base
from .database.client import ConnectionError as DBConnectionError
from .database.client import DatabaseClient, DatabaseClientError
from .database.client import OperationError as DBOperationError
from .database.client import get_db_client
from .database.manager import DatabaseManager
from .email.client import ConfigurationError as EmailConfigError
from .email.client import EmailClient, EmailClientError, SendError, get_email_client
from .k8s.client import KubernetesClient, get_k8s_client
from .redis import RateLimiter, RedisManager, get_redis_client
from .redis.client import ConnectionError as RedisConnectionError
from .redis.client import OperationError as RedisOperationError
from .redis.client import RedisClient, RedisClientError, get_redis_client
from .stripe.client import (
    CustomerError,
    PaymentError,
    StripeClient,
    StripeClientError,
    SubscriptionError,
    get_stripe_client,
)

__all__ = [
    # Kubernetes
    "KubernetesClient",
    "get_k8s_client",
    # Redis
    "RedisClient",
    "RedisClientError",
    "RedisConnectionError",
    "RedisOperationError",
    "get_redis_client",
    # Stripe
    "StripeClient",
    "StripeClientError",
    "PaymentError",
    "SubscriptionError",
    "CustomerError",
    "get_stripe_client",
    # Email
    "EmailClient",
    "EmailClientError",
    "SendError",
    "EmailConfigError",
    "get_email_client",
    # Database
    "DatabaseClient",
    "DatabaseClientError",
    "DBConnectionError",
    "DBOperationError",
    "get_db_client",
    "Base",
    "DatabaseManager",
    # Redis utilities
    "RateLimiter",
    "get_redis_client",
    "RedisManager",
]
