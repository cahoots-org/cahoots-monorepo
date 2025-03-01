"""Billing management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID

from api.dependencies import get_db, get_current_user
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.billing import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    PaymentMethodCreate,
    PaymentMethodResponse,
    InvoiceResponse,
    UsageResponse
)
from cahoots_core.services.billing import BillingService
from cahoots_core.models.user import User

from .subscriptions import router as subscriptions_router
from .payment_methods import router as payment_methods_router
from .invoices import router as invoices_router
from .usage import router as usage_router

router = APIRouter(prefix="/billing", tags=["billing"])

# Include sub-routers
router.include_router(subscriptions_router)
router.include_router(payment_methods_router)
router.include_router(invoices_router)
router.include_router(usage_router)

@router.get("/status", response_model=APIResponse[Dict[str, Any]])
async def get_billing_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[Dict[str, Any]]:
    """Get current billing status including subscription, usage, and payment info."""
    try:
        service = BillingService(db)
        status = await service.get_billing_status(current_user.id)
        
        return APIResponse(
            success=True,
            data=status
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="BILLING_STATUS_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> APIResponse[bool]:
    """Handle Stripe webhook events."""
    try:
        service = BillingService(db)
        await service.handle_webhook(request)
        
        return APIResponse(
            success=True,
            data=True
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="WEBHOOK_ERROR",
                message=str(e),
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.ERROR
            )
        ) 