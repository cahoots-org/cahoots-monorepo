"""Payment method management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID

from api.dependencies import get_db, get_current_user
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.billing import (
    PaymentMethodCreate,
    PaymentMethodUpdate,
    PaymentMethodResponse,
    SetupIntentResponse
)
from cahoots_core.services.billing import BillingService
from cahoots_core.models.user import User

router = APIRouter(prefix="/payment-methods", tags=["billing-payment-methods"])

@router.post("/setup-intent", response_model=APIResponse[SetupIntentResponse])
async def create_setup_intent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[SetupIntentResponse]:
    """Create a setup intent for adding a new payment method."""
    try:
        service = BillingService(db)
        intent = await service.create_setup_intent(current_user.id)
        
        return APIResponse(
            success=True,
            data=intent
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="SETUP_INTENT_ERROR",
                message=str(e),
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.ERROR
            )
        )

@router.post("", response_model=APIResponse[PaymentMethodResponse])
async def add_payment_method(
    payment_method: PaymentMethodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[PaymentMethodResponse]:
    """Add a new payment method."""
    try:
        service = BillingService(db)
        result = await service.add_payment_method(payment_method, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PAYMENT_METHOD_ADD_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("", response_model=APIResponse[List[PaymentMethodResponse]])
async def list_payment_methods(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[List[PaymentMethodResponse]]:
    """List all payment methods for the current user."""
    try:
        service = BillingService(db)
        methods = await service.list_payment_methods(current_user.id)
        
        return APIResponse(
            success=True,
            data=methods
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PAYMENT_METHOD_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.put("/{payment_method_id}", response_model=APIResponse[PaymentMethodResponse])
async def update_payment_method(
    payment_method_id: str,
    payment_method: PaymentMethodUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[PaymentMethodResponse]:
    """Update a payment method."""
    try:
        service = BillingService(db)
        result = await service.update_payment_method(
            payment_method_id,
            payment_method,
            current_user.id
        )
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PAYMENT_METHOD_UPDATE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.delete("/{payment_method_id}", response_model=APIResponse[bool])
async def delete_payment_method(
    payment_method_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[bool]:
    """Delete a payment method."""
    try:
        service = BillingService(db)
        result = await service.delete_payment_method(payment_method_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PAYMENT_METHOD_DELETE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.post("/{payment_method_id}/default", response_model=APIResponse[bool])
async def set_default_payment_method(
    payment_method_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[bool]:
    """Set a payment method as default."""
    try:
        service = BillingService(db)
        result = await service.set_default_payment_method(payment_method_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="PAYMENT_METHOD_DEFAULT_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        ) 