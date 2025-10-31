"""Allowed Technologies Catalog

Defines the constrained set of technologies supported by Cahoots code generation.
This ensures consistent, maintainable code generation with well-tested technology choices.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class TechnologyOption:
    """Represents a supported technology choice."""
    name: str
    category: str
    use_cases: List[str]
    requires_service: bool = False  # True if third-party service
    description: str = ""


class TechCatalog:
    """Catalog of allowed technologies for code generation.

    Note: Languages are implicit in framework choices:
    - FastAPI → Python
    - Express → TypeScript
    - React/Next.js → TypeScript/JavaScript
    """

    # Frontend Frameworks (TypeScript/JavaScript)
    FRONTEND_FRAMEWORKS = {
        "React": TechnologyOption(
            name="React",
            category="frontend",
            use_cases=["spa", "web_app", "dashboard"],
            description="React with hooks and functional components"
        ),
        "Next.js": TechnologyOption(
            name="Next.js",
            category="frontend",
            use_cases=["ssr", "static_site", "fullstack_app"],
            description="Next.js with app router (v13+)"
        )
    }

    # Backend Frameworks
    BACKEND_FRAMEWORKS = {
        "FastAPI": TechnologyOption(
            name="FastAPI",
            category="backend",
            use_cases=["api", "microservice", "backend"],
            description="FastAPI with async/await support (Python)"
        ),
        "Express": TechnologyOption(
            name="Express",
            category="backend",
            use_cases=["api", "web_server", "backend"],
            description="Express.js with TypeScript"
        )
    }

    # Third-Party Services (require explicit selection via tool calls)
    DATABASES = {
        "PostgreSQL": TechnologyOption(
            name="PostgreSQL",
            category="database",
            use_cases=["relational", "complex_queries", "acid"],
            requires_service=True,
            description="PostgreSQL for relational data with ACID guarantees"
        ),
        "MongoDB": TechnologyOption(
            name="MongoDB",
            category="database",
            use_cases=["document", "flexible_schema", "nosql"],
            requires_service=True,
            description="MongoDB for document storage with flexible schemas"
        ),
        "Redis": TechnologyOption(
            name="Redis",
            category="database",
            use_cases=["cache", "session", "queue", "realtime"],
            requires_service=True,
            description="Redis for caching, sessions, and real-time data"
        )
    }

    CACHING = {
        "Redis": TechnologyOption(
            name="Redis",
            category="cache",
            use_cases=["cache", "session"],
            requires_service=True,
            description="Redis for distributed caching"
        ),
        "In-Memory": TechnologyOption(
            name="In-Memory",
            category="cache",
            use_cases=["simple_cache", "single_instance"],
            requires_service=False,
            description="In-memory caching (application-level)"
        )
    }

    PAYMENT_PROVIDERS = {
        "Stripe": TechnologyOption(
            name="Stripe",
            category="payment",
            use_cases=["subscription", "one_time", "marketplace"],
            requires_service=True,
            description="Stripe for payment processing"
        ),
        "PayPal": TechnologyOption(
            name="PayPal",
            category="payment",
            use_cases=["checkout", "one_time"],
            requires_service=True,
            description="PayPal for payment processing"
        )
    }

    AUTH_PROVIDERS = {
        "Auth0": TechnologyOption(
            name="Auth0",
            category="auth",
            use_cases=["oauth", "social_login", "enterprise"],
            requires_service=True,
            description="Auth0 for authentication and authorization"
        ),
        "Firebase Auth": TechnologyOption(
            name="Firebase Auth",
            category="auth",
            use_cases=["mobile", "web", "social_login"],
            requires_service=True,
            description="Firebase Authentication"
        ),
        "Supabase Auth": TechnologyOption(
            name="Supabase Auth",
            category="auth",
            use_cases=["postgres", "row_level_security"],
            requires_service=True,
            description="Supabase Authentication (works with PostgreSQL)"
        ),
        "JWT": TechnologyOption(
            name="JWT",
            category="auth",
            use_cases=["api", "stateless", "custom"],
            requires_service=False,
            description="Custom JWT-based authentication"
        )
    }

    STORAGE_PROVIDERS = {
        "AWS S3": TechnologyOption(
            name="AWS S3",
            category="storage",
            use_cases=["files", "images", "documents"],
            requires_service=True,
            description="AWS S3 for object storage"
        ),
        "Cloudinary": TechnologyOption(
            name="Cloudinary",
            category="storage",
            use_cases=["images", "media", "cdn"],
            requires_service=True,
            description="Cloudinary for image/video storage and transformation"
        ),
        "Local": TechnologyOption(
            name="Local",
            category="storage",
            use_cases=["development", "simple"],
            requires_service=False,
            description="Local filesystem storage"
        )
    }

    EMAIL_PROVIDERS = {
        "SendGrid": TechnologyOption(
            name="SendGrid",
            category="email",
            use_cases=["transactional", "marketing"],
            requires_service=True,
            description="SendGrid for email delivery"
        ),
        "Mailgun": TechnologyOption(
            name="Mailgun",
            category="email",
            use_cases=["transactional", "validation"],
            requires_service=True,
            description="Mailgun for email delivery"
        ),
        "SMTP": TechnologyOption(
            name="SMTP",
            category="email",
            use_cases=["custom", "simple"],
            requires_service=False,
            description="Custom SMTP server"
        )
    }

    QUEUE_PROVIDERS = {
        "Redis Queue": TechnologyOption(
            name="Redis Queue",
            category="queue",
            use_cases=["background_jobs", "async_tasks"],
            requires_service=True,
            description="Redis-based task queue (Python: RQ, Node: BullMQ)"
        ),
        "Celery": TechnologyOption(
            name="Celery",
            category="queue",
            use_cases=["background_jobs", "scheduled_tasks"],
            requires_service=True,
            description="Celery distributed task queue (Python)"
        ),
        "BullMQ": TechnologyOption(
            name="BullMQ",
            category="queue",
            use_cases=["background_jobs", "async_tasks"],
            requires_service=True,
            description="BullMQ task queue (Node.js)"
        )
    }

    @classmethod
    def get_all_categories(cls) -> Dict[str, Dict[str, TechnologyOption]]:
        """Get all technology categories."""
        return {
            "frontend": cls.FRONTEND_FRAMEWORKS,
            "backend": cls.BACKEND_FRAMEWORKS,
            "database": cls.DATABASES,
            "cache": cls.CACHING,
            "payment": cls.PAYMENT_PROVIDERS,
            "auth": cls.AUTH_PROVIDERS,
            "storage": cls.STORAGE_PROVIDERS,
            "email": cls.EMAIL_PROVIDERS,
            "queue": cls.QUEUE_PROVIDERS
        }

    @classmethod
    def get_technology_by_name(cls, name: str) -> TechnologyOption:
        """Get a technology by name across all categories."""
        for category_dict in cls.get_all_categories().values():
            if name in category_dict:
                return category_dict[name]
        raise ValueError(f"Technology '{name}' not found in catalog")

    @classmethod
    def get_technologies_for_use_case(cls, use_case: str, category: str = None) -> List[TechnologyOption]:
        """Get technologies that match a use case."""
        results = []
        categories = cls.get_all_categories()

        if category:
            categories = {category: categories.get(category, {})}

        for cat_dict in categories.values():
            for tech in cat_dict.values():
                if use_case in tech.use_cases:
                    results.append(tech)

        return results

    @classmethod
    def requires_third_party_service(cls, tech_name: str) -> bool:
        """Check if a technology requires a third-party service."""
        try:
            tech = cls.get_technology_by_name(tech_name)
            return tech.requires_service
        except ValueError:
            return False
