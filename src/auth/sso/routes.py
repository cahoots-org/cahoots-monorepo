"""SSO authentication routes."""
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from src.database.session import get_session
from src.utils.redis_client import get_redis_client
from src.auth.sso.saml.metadata import SAMLMetadata
from src.auth.sso.saml.processor import SAMLProcessor
from src.auth.sso.session import SSOSession
from src.models.identity_provider import IdentityProvider
from src.models.user import User
from src.utils.config import config

router = APIRouter(prefix="/auth/sso", tags=["auth"])

async def get_sso_session(redis: Redis = Depends(get_redis_client)) -> SSOSession:
    """Get SSO session manager."""
    return SSOSession(redis)

@router.get("/metadata")
async def get_sp_metadata() -> Response:
    """Get service provider SAML metadata."""
    metadata_handler = SAMLMetadata(
        entity_id=config.saml.entity_id,
        cert_path=config.saml.cert_path
    )
    
    metadata_xml = metadata_handler.generate_sp_metadata(
        acs_url=f"{config.app.base_url}/auth/sso/acs"
    )
    
    return Response(
        content=metadata_xml,
        media_type="application/xml"
    )

@router.post("/providers/{provider_id}/metadata")
async def update_idp_metadata(
    provider_id: str,
    metadata: str,
    db: AsyncSession = Depends(get_session)
) -> Dict:
    """Update identity provider metadata.
    
    Args:
        provider_id: Identity provider ID
        metadata: SAML metadata XML
        db: Database session
        
    Returns:
        Dict: Updated provider details
    """
    # Parse metadata
    metadata_handler = SAMLMetadata(config.saml.entity_id)
    idp_data = metadata_handler.parse_idp_metadata(metadata)
    
    # Update provider in database
    provider = await db.get(IdentityProvider, provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identity provider not found"
        )
    
    provider.metadata = idp_data
    provider.entity_id = idp_data['entity_id']
    await db.commit()
    
    return {
        "id": provider.id,
        "name": provider.name,
        "entity_id": provider.entity_id,
        "updated_at": provider.updated_at.isoformat()
    }

@router.get("/login/{provider_id}")
async def initiate_sso(
    provider_id: str,
    db: AsyncSession = Depends(get_session)
) -> RedirectResponse:
    """Initiate SSO login flow.
    
    Args:
        provider_id: Identity provider ID
        db: Database session
        
    Returns:
        RedirectResponse: Redirect to IdP login
    """
    # Get provider details
    provider = await db.get(IdentityProvider, provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identity provider not found"
        )
    
    # Create SAML request
    processor = SAMLProcessor(
        entity_id=config.saml.entity_id,
        cert_path=config.saml.cert_path,
        private_key_path=config.saml.private_key_path
    )
    
    # Get SSO URL from metadata
    sso_url = provider.metadata['sso_urls'].get(
        'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
    )
    if not sso_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider does not support HTTP-Redirect binding"
        )
    
    # Generate auth request
    saml_request = processor.create_auth_request(
        idp_url=sso_url,
        acs_url=f"{config.app.base_url}/auth/sso/acs"
    )
    
    # Redirect to IdP
    return RedirectResponse(
        url=f"{sso_url}?SAMLRequest={saml_request}",
        status_code=status.HTTP_302_FOUND
    )

@router.post("/acs")
async def handle_sso_response(
    request: Request,
    db: AsyncSession = Depends(get_session),
    sso_session: SSOSession = Depends(get_sso_session)
) -> RedirectResponse:
    """Handle SAML response from IdP.
    
    Args:
        request: Request instance
        db: Database session
        sso_session: SSO session manager
        
    Returns:
        RedirectResponse: Redirect to application
    """
    # Get form data
    form_data = await request.form()
    saml_response = form_data.get('SAMLResponse')
    if not saml_response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing SAML response"
        )
    
    # Process SAML response
    processor = SAMLProcessor(config.saml.entity_id)
    try:
        assertion_data = processor.process_response(saml_response)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Get or create user
    user = await get_or_create_user(db, assertion_data)
    
    # Create SSO session
    session_id = await sso_session.create_session(
        user_data={
            'id': str(user.id),
            'email': user.email,
            'name': user.name
        },
        provider_id=assertion_data['audience']
    )
    
    # Redirect to application with session
    response = RedirectResponse(
        url=f"{config.app.frontend_url}",
        status_code=status.HTTP_302_FOUND
    )
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    
    return response

@router.post("/logout")
async def logout(
    session_id: str,
    sso_session: SSOSession = Depends(get_sso_session)
) -> Dict:
    """End SSO session.
    
    Args:
        session_id: Session ID
        sso_session: SSO session manager
        
    Returns:
        Dict: Success response
    """
    await sso_session.end_session(session_id)
    return {"status": "success"}

async def get_or_create_user(
    db: AsyncSession,
    assertion_data: Dict
) -> User:
    """Get or create user from SAML assertion.
    
    Args:
        db: Database session
        assertion_data: SAML assertion data
        
    Returns:
        User: User instance
    """
    # Extract user details from assertion
    email = assertion_data['attributes'].get('email')
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email attribute missing from assertion"
        )
    
    # Look up existing user
    user = await db.scalar(
        select(User).where(User.email == email)
    )
    
    if not user:
        # Create new user
        user = User(
            email=email,
            name=assertion_data['attributes'].get('name', email),
            is_active=True
        )
        db.add(user)
        await db.commit()
    
    return user 