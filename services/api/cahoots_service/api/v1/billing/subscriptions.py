"""Subscription management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID

from cahoots_service.api.dependencies import get_db, get_current_user
from cahoots_service.schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from cahoots_service.schemas.billing import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionPreviewResponse
)
from cahoots_core.services.billing import BillingService
from cahoots_core.models.user import User

router = APIRouter(prefix="/subscriptions", tags=["billing-subscriptions"])

@router.post("", response_model=APIResponse[SubscriptionResponse])
async def create_subscription(
    subscription: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[SubscriptionResponse]:
    """Create a new subscription."""
    try:
        service = BillingService(db)
        result = await service.create_subscription(subscription, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="SUBSCRIPTION_CREATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("", response_model=APIResponse[List[SubscriptionResponse]])
async def list_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[SubscriptionResponse]]:
    """List all subscriptions for the current user."""
    try:
        service = BillingService(db)
        subscriptions = await service.list_subscriptions(current_user.id)
        
        return APIResponse(
            success=True,
            data=subscriptions
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="SUBSCRIPTION_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/{subscription_id}", response_model=APIResponse[SubscriptionResponse])
async def get_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[SubscriptionResponse]:
    """Get a specific subscription by ID."""
    try:
        service = BillingService(db)
        subscription = await service.get_subscription(subscription_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=subscription
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="SUBSCRIPTION_GET_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.put("/{subscription_id}", response_model=APIResponse[SubscriptionResponse])
async def update_subscription(
    subscription_id: UUID,
    subscription: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[SubscriptionResponse]:
    """Update a subscription."""
    try:
        service = BillingService(db)
        result = await service.update_subscription(subscription_id, subscription, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="SUBSCRIPTION_UPDATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.delete("/{subscription_id}", response_model=APIResponse[bool])
async def cancel_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[bool]:
    """Cancel a subscription."""
    try:
        service = BillingService(db)
        result = await service.cancel_subscription(subscription_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="SUBSCRIPTION_CANCEL_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.post("/preview", response_model=APIResponse[SubscriptionPreviewResponse])
async def preview_subscription(
    subscription: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[SubscriptionPreviewResponse]:
    """Preview subscription costs and details before creation."""
    try:
        service = BillingService(db)
        preview = await service.preview_subscription(subscription, current_user.id)
        
        return APIResponse(
            success=True,
            data=preview
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="SUBSCRIPTION_PREVIEW_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        ) 