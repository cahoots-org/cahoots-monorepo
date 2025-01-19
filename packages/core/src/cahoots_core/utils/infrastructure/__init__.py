"""Infrastructure package for managing external services and resources."""
from .k8s.client import (
    KubernetesClient,
    get_k8s_client
)
from .redis.client import (
    RedisClient,
    RedisClientError,
    ConnectionError as RedisConnectionError,
    OperationError as RedisOperationError,
    get_redis_client
)
from .stripe.client import (
    StripeClient,
    StripeClientError,
    PaymentError,
    SubscriptionError,
    CustomerError,
    get_stripe_client
)
from .email.client import (
    EmailClient,
    EmailClientError,
    SendError,
    ConfigurationError as EmailConfigError,
    get_email_client
)
from .database.client import (
    DatabaseClient,
    DatabaseClientError,
    ConnectionError as DBConnectionError,
    OperationError as DBOperationError,
    get_db_client,
    Base
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
] 