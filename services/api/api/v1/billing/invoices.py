"""Invoice management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID

from api.dependencies import get_db, get_current_user
from schemas.base import APIResponse, ErrorDetail, ErrorCategory, ErrorSeverity
from schemas.billing import (
    InvoiceResponse,
    InvoiceListResponse,
    UpcomingInvoiceResponse
)
from cahoots_core.services.billing import BillingService
from cahoots_core.models.user import User

router = APIRouter(prefix="/invoices", tags=["billing-invoices"])

@router.get("", response_model=APIResponse[InvoiceListResponse])
async def list_invoices(
    limit: int = 10,
    starting_after: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[InvoiceListResponse]:
    """List all invoices with pagination."""
    try:
        service = BillingService(db)
        result = await service.list_invoices(
            current_user.id,
            limit=limit,
            starting_after=starting_after
        )
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="INVOICE_LIST_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/upcoming", response_model=APIResponse[UpcomingInvoiceResponse])
async def get_upcoming_invoice(
    subscription_id: UUID = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[UpcomingInvoiceResponse]:
    """Get the upcoming invoice for a subscription."""
    try:
        service = BillingService(db)
        invoice = await service.get_upcoming_invoice(current_user.id, subscription_id)
        
        return APIResponse(
            success=True,
            data=invoice
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="UPCOMING_INVOICE_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.get("/{invoice_id}", response_model=APIResponse[InvoiceResponse])
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[InvoiceResponse]:
    """Get a specific invoice by ID."""
    try:
        service = BillingService(db)
        invoice = await service.get_invoice(invoice_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=invoice
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="INVOICE_GET_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        )

@router.post("/{invoice_id}/pay", response_model=APIResponse[InvoiceResponse])
async def pay_invoice(
    invoice_id: str,
    payment_method_id: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> APIResponse[InvoiceResponse]:
    """Pay a specific invoice."""
    try:
        service = BillingService(db)
        result = await service.pay_invoice(invoice_id, payment_method_id, current_user.id)
        
        return APIResponse(
            success=True,
            data=result
        )
    except Exception as e:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code="INVOICE_PAYMENT_ERROR",
                message=str(e),
                category=ErrorCategory.BUSINESS_LOGIC,
                severity=ErrorSeverity.ERROR
            )
        ) 