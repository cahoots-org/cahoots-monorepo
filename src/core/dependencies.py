"""Centralized dependency management."""
from typing import AsyncGenerator, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from redis.asyncio import Redis

from src.utils.k8s import KubernetesClient
from src.utils.model import Model
from src.utils.event_system import EventSystem
from src.services.github_service import GitHubService
from src.utils.stripe_client import StripeClient
from src.utils.config import Settings, get_settings, config, GitHubConfig

# Core dependency providers
async def get_db(settings: Settings = Depends(get_settings)) -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    engine = create_async_engine(settings.DATABASE_URL)
    session = AsyncSession(bind=engine)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()

async def get_redis(settings: Settings = Depends(get_settings)) -> AsyncGenerator[Redis, None]:
    """Get Redis client."""
    redis = Redis.from_url(settings.REDIS_URL)
    try:
        yield redis
    finally:
        await redis.close()

async def get_event_system(
    settings: Settings = Depends(get_settings),
    redis: Redis = Depends(get_redis)
) -> EventSystem:
    """Get event system instance."""
    return EventSystem(redis=redis)

def get_k8s(settings: Settings = Depends(get_settings)) -> KubernetesClient:
    """Get Kubernetes client."""
    return KubernetesClient(namespace=settings.K8S_NAMESPACE)

def get_model(settings: Settings = Depends(get_settings)) -> Model:
    """Get AI model instance."""
    return Model(model_name=settings.MODEL_NAME)

def get_github() -> GitHubService:
    """Get GitHub service instance."""
    if "github" not in config.services:
        config.services["github"] = GitHubConfig(
            name="github",
            url="https://api.github.com",
            api_key="test-github-key",
            workspace_dir="/tmp/workspace",
            repo_name="test_repo"
        )
    return GitHubService(config=config.services["github"])

def get_stripe(settings: Settings = Depends(get_settings)) -> StripeClient:
    """Get Stripe client instance."""
    return StripeClient(api_key=settings.STRIPE_API_KEY)

class BaseDeps:
    """Base dependencies that are commonly used across services."""
    
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        db: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
        event_system: EventSystem = Depends(get_event_system)
    ):
        self.settings = settings
        self.db = db
        self.redis = redis
        self.event_system = event_system

class ServiceDeps(BaseDeps):
    """Dependencies for services that need additional components."""
    
    def __init__(
        self,
        base: BaseDeps = Depends(),
        k8s: KubernetesClient = Depends(get_k8s),
        model: Model = Depends(get_model),
        github: GitHubService = Depends(get_github),
        stripe: StripeClient = Depends(get_stripe)
    ):
        super().__init__(
            settings=base.settings,
            db=base.db,
            redis=base.redis,
            event_system=base.event_system
        )
        self.k8s = k8s
        self.model = model
        self.github = github
        self.stripe = stripe

# Factory for non-HTTP contexts (background tasks, scripts)
class ServiceFactory:
    """Factory for creating service instances outside of HTTP context."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
    
    async def create_base_deps(self) -> BaseDeps:
        """Create base dependencies."""
        engine = create_async_engine(self.settings.DATABASE_URL)
        db = AsyncSession(bind=engine)
        redis = Redis.from_url(self.settings.REDIS_URL)
        event_system = EventSystem(redis=redis)
        return BaseDeps(
            settings=self.settings,
            db=db,
            redis=redis,
            event_system=event_system
        )
    
    async def create_service_deps(self) -> ServiceDeps:
        """Create full service dependencies."""
        base = await self.create_base_deps()
        k8s = get_k8s(self.settings)
        model = get_model(self.settings)
        github = get_github()
        stripe = get_stripe(self.settings)
        return ServiceDeps(base, k8s, model, github, stripe)
    
    async def cleanup(self, deps: BaseDeps):
        """Cleanup dependencies."""
        await deps.db.close()
        await deps.redis.close()
        await deps.event_system.close() 