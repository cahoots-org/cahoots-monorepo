from typing import Generator, AsyncGenerator
from sqlalchemy.orm import Session
from fastapi import Depends
from kubernetes import client, config
import redis.asyncio as redis

from src.db.database import SessionLocal
from src.utils.context_utils import ContextClient
from src.utils.auth import get_project_id

async def get_db() -> AsyncGenerator[Session, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    try:
        yield redis_client
    finally:
        await redis_client.close()

async def get_k8s() -> AsyncGenerator[client.AppsV1Api, None]:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    yield client.AppsV1Api()

async def get_context_client(
    redis_client: redis.Redis = Depends(get_redis)
) -> ContextClient:
    return ContextClient(redis_client)

class TeamServiceDeps:
    def __init__(
        self,
        db: Session = Depends(get_db),
        redis_client: redis.Redis = Depends(get_redis),
        k8s_client: client.AppsV1Api = Depends(get_k8s),
        context_client: ContextClient = Depends(get_context_client),
        project_id: str = Depends(get_project_id)
    ):
        self.db = db
        self.redis = redis_client
        self.k8s = k8s_client
        self.context = context_client
        self.project_id = project_id 