"""Subscription validation middleware."""
from typing import Optional, Dict
from fastapi import Request, HTTPException
from stripe import SubscriptionService

class SubscriptionValidator:
    """Subscription validation middleware."""
    
    def __init__(
        self,
        subscription_service: Optional[SubscriptionService] = None
    ):
        """Initialize subscription validator.
        
        Args:
            subscription_service: Service for checking subscriptions
        """
        self.subscription_service = subscription_service
        
        # Define tier limits
        self.tier_limits = {
            "basic": {
                "projects": 3,
                "agents_per_project": 2,
                "resource_limits": {
                    "cpu": "2",
                    "memory": "4Gi",
                    "pods": "5"
                }
            },
            "premium": {
                "projects": 10,
                "agents_per_project": 5,
                "resource_limits": {
                    "cpu": "8",
                    "memory": "16Gi",
                    "pods": "20"
                }
            },
            "enterprise": {
                "projects": -1,  # Unlimited
                "agents_per_project": -1,  # Unlimited
                "resource_limits": {
                    "cpu": "32",
                    "memory": "64Gi",
                    "pods": "100"
                }
            }
        }
        
    async def validate_limits(
        self,
        organization_id: str,
        metric: str,
        value: int
    ) -> bool:
        """Validate if usage is within subscription limits."""
        # Get organization's subscription tier
        subscription = await self.subscription_service.get_subscription(organization_id)
        if not subscription:
            return False
            
        # Get tier limits
        tier_limits = self.tier_limits.get(subscription.tier)
        if not tier_limits:
            return False
            
        # Check if metric is limited
        limit = tier_limits.get(metric)
        if limit == -1:  # Unlimited
            return True
            
        return value <= limit
        
    async def validate_resources(
        self,
        organization_id: str,
        resources: Dict
    ) -> bool:
        """Validate if resource request is within subscription limits."""
        subscription = await self.subscription_service.get_subscription(organization_id)
        if not subscription:
            return False
            
        tier_limits = self.tier_limits.get(subscription.tier, {}).get("resource_limits", {})
        
        # Compare each resource
        for resource, requested in resources.items():
            limit = tier_limits.get(resource)
            if not limit:
                continue
                
            # Convert to comparable units
            req_value = self._parse_resource(requested)
            limit_value = self._parse_resource(limit)
            
            if req_value > limit_value:
                return False
                
        return True
        
    def _parse_resource(self, value: str) -> float:
        """Parse resource string to numeric value."""
        if isinstance(value, (int, float)):
            return float(value)
            
        # Parse CPU
        if value.endswith("m"):
            return float(value[:-1]) / 1000
            
        # Parse memory
        if value.endswith("Gi"):
            return float(value[:-2])
        if value.endswith("Mi"):
            return float(value[:-2]) / 1024
            
        return float(value)
        
    async def __call__(self, request: Request):
        """Validate subscription for request."""
        # Get organization ID
        org_id = request.state.organization_id
        
        # Check if subscription is active
        subscription = await self.subscription_service.get_subscription(org_id)
        if not subscription or not subscription.is_active:
            raise HTTPException(
                status_code=402,
                detail="Active subscription required"
            )
            
        # For project creation, validate project count
        if request.url.path.endswith("/projects") and request.method == "POST":
            project_count = await self.subscription_service.get_project_count(org_id)
            if not await self.validate_limits(org_id, "projects", project_count + 1):
                raise HTTPException(
                    status_code=402,
                    detail="Project limit reached for subscription tier"
                )
                
        # For agent deployment, validate agent count
        if "agents" in request.url.path and request.method == "POST":
            project_id = request.path_params.get("project_id")
            if project_id:
                agent_count = await self.subscription_service.get_agent_count(project_id)
                if not await self.validate_limits(org_id, "agents_per_project", agent_count + 1):
                    raise HTTPException(
                        status_code=402,
                        detail="Agent limit reached for subscription tier"
                    )
                    
        # For resource updates, validate resource limits
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.json()
            if "resource_limits" in body:
                if not await self.validate_resources(org_id, body["resource_limits"]):
                    raise HTTPException(
                        status_code=402,
                        detail="Resource limits exceed subscription tier"
                    )
                    
        return request 