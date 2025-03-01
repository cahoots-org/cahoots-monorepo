"""Authentication service."""
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from uuid import UUID
import secrets
import os
import logging
import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from cahoots_core.models.user import User
from cahoots_core.models.auth import SocialAccount
from services.auth.utils import hash_password, verify_password
from utils.security import SecurityManager
from utils.config import get_settings
from cahoots_core.utils.config import SecurityConfig
from cahoots_core.utils.infrastructure.redis.client import RedisClient, RedisConfig

logger = logging.getLogger(__name__)

class AuthService:
    """Service for handling authentication operations."""

    def __init__(self, db: AsyncSession, security_manager: SecurityManager):
        """Initialize auth service.
        
        Args:
            db: Database session
            security_manager: Security manager instance
        """
        self.db = db
        self._security_manager = security_manager
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        
        self.secret_key = self.settings.jwt_secret_key
        self.jwt_algorithm = self.settings.jwt_algorithm
        self.access_token_expire_minutes = self.settings.auth_token_expire_minutes
        self.refresh_token_expire_days = 30  # Default to 30 days

    async def initialize(self) -> None:
        """Initialize auth service dependencies."""
        try:
            self.logger.info("Auth service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize auth service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize auth service"
            )

    @property
    def security_manager(self) -> SecurityManager:
        """Get security manager instance."""
        if not self._security_manager:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Auth service not initialized"
            )
        return self._security_manager

    async def authenticate_user(self, email: str, password: str) -> Tuple[User, str, str]:
        """Authenticate user with email and password.
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            Tuple of (user, access_token, refresh_token)
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Find user
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"Failed login attempt for non-existent user: {email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # Verify password
            if not verify_password(password, user.hashed_password):
                logger.warning(f"Failed login attempt for user: {email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # Check if verified
            if not user.is_verified:
                logger.info(f"Login attempt from unverified user: {email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email not verified"
                )

            # Generate tokens
            access_token = self._create_access_token(user.id)
            refresh_token = await self._create_refresh_token(user.id)

            # Update last login
            user.last_login = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Successful login for user: {email}")
            return user, access_token, refresh_token

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed"
            )

    async def refresh_tokens(self, refresh_token: str) -> Tuple[str, str]:
        """Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        try:
            # Validate and get new tokens from security manager
            payload = await self.security_manager.validate_token(refresh_token)
            access_token, new_refresh_token = await self.security_manager.create_tokens(payload["sub"])
            
            # Revoke old refresh token
            await self.security_manager.revoke_token(refresh_token)
            
            return access_token, new_refresh_token
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing tokens: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error refreshing tokens"
            )

    async def revoke_token(self, refresh_token: str):
        """Revoke a refresh token.
        
        Args:
            refresh_token: Refresh token to revoke
        """
        await self.security_manager.revoke_token(refresh_token)

    async def authenticate_social(self, provider: str, user_data: Dict[str, Any]) -> Tuple[User, str, str]:
        """Authenticate user with social provider data.
        
        Args:
            provider: Social provider (google/github)
            user_data: User data from social provider
            
        Returns:
            Tuple of (user, access_token, refresh_token)
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Verify we have required fields
            if not user_data.get("id") or not user_data.get("email"):
                logger.error(f"Missing required fields from {provider} data")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required user data fields"
                )

            # Find or create social account
            stmt = select(SocialAccount).where(
                SocialAccount.provider == provider,
                SocialAccount.provider_user_id == str(user_data["id"])
            )
            result = await self.db.execute(stmt)
            social_account = result.scalar_one_or_none()

            if social_account:
                user = await self._get_user(social_account.user_id)
                logger.info(f"Social login for existing user via {provider}: {user.email}")
            else:
                # Create user if doesn't exist
                stmt = select(User).where(User.email == user_data["email"])
                result = await self.db.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    user = User(
                        email=user_data["email"],
                        full_name=user_data.get("name", ""),
                        is_verified=True  # Social users are pre-verified
                    )
                    self.db.add(user)
                    await self.db.commit()
                    logger.info(f"Created new user via {provider}: {user.email}")

                # Create social account
                social_account = SocialAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=str(user_data["id"]),
                    provider_data=user_data
                )
                self.db.add(social_account)
                await self.db.commit()
                logger.info(f"Created social account for {user.email} via {provider}")

            # Generate tokens
            access_token = self._create_access_token(user.id)
            refresh_token = await self._create_refresh_token(user.id)

            # Update last login
            user.last_login = datetime.utcnow()
            await self.db.commit()

            return user, access_token, refresh_token

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in social authentication: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to handle social user: {str(e)}"
            )

    async def change_password(self, user: User, current_password: str, new_password: str):
        """Change user password.
        
        Args:
            user: User to change password for
            current_password: Current password
            new_password: New password
            
        Raises:
            HTTPException: If password change fails
        """
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid current password"
            )
            
        # Update password
        user.hashed_password = hash_password(new_password)
        await self.db.commit()

    async def create_password_reset(self, email: str) -> Tuple[User, str]:
        """Create password reset token.
        
        Args:
            email: User's email
            
        Returns:
            Tuple of (user, reset_token)
            
        Raises:
            HTTPException: If user not found
        """
        # Find user
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Generate reset token
        reset_token = self._generate_token()
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
        await self.db.commit()

        return user, reset_token

    async def reset_password(self, token: str, new_password: str):
        """Reset password using reset token.
        
        Args:
            token: Reset token
            new_password: New password
            
        Raises:
            HTTPException: If reset fails
        """
        # Find user with valid token
        stmt = select(User).where(
            User.reset_token == token,
            User.reset_token_expires > datetime.utcnow()
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired reset token"
            )

        # Update password
        user.hashed_password = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        await self.db.commit()

    async def verify_email(self, token: str) -> User:
        """Verify user email with verification token.
        
        Args:
            token: Verification token
            
        Returns:
            Verified user
            
        Raises:
            HTTPException: If verification fails
        """
        # Find user with token
        stmt = select(User).where(
            User.verification_token == token,
            User.is_verified == False
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid verification token"
            )

        # Mark as verified
        user.is_verified = True
        user.verification_token = None
        await self.db.commit()

        return user

    async def create_verification_token(self, email: str) -> Tuple[User, str]:
        """Create new verification token.
        
        Args:
            email: User's email
            
        Returns:
            Tuple of (user, verification_token)
            
        Raises:
            HTTPException: If user not found or already verified
        """
        # Find user
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )

        # Generate verification token
        verification_token = self._generate_token()
        user.verification_token = verification_token
        await self.db.commit()

        return user, verification_token

    def _generate_token(self) -> str:
        """Generate a secure random token.
        
        Returns:
            Random token string
        """
        return secrets.token_urlsafe(32)

    def _create_access_token(self, user_id: UUID) -> str:
        """Create JWT access token.
        
        Args:
            user_id: User ID to encode in token
            
        Returns:
            Encoded JWT token
        """
        expires = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": str(user_id),
            "exp": expires,
            "type": "access"
        }
        
        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.jwt_algorithm
        )

    async def _create_refresh_token(self, user_id: UUID) -> str:
        """Create refresh token.
        
        Args:
            user_id: User ID to create token for
            
        Returns:
            Refresh token string
        """
        # Use security manager to create tokens
        _, refresh_token = await self.security_manager.create_tokens(str(user_id))
        return refresh_token

    async def _get_user(self, user_id: UUID) -> User:
        """Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object
            
        Raises:
            HTTPException: If user not found
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user

    async def handle_social_user(self, provider: str, user_data: Dict[str, Any]) -> Tuple[User, str, str]:
        """Handle social user authentication.
        
        Args:
            provider: The social provider (e.g. 'google', 'github')
            user_data: User data from social provider
            
        Returns:
            Tuple of (user, access_token, refresh_token)
            
        Raises:
            HTTPException: If user creation/update fails
        """
        try:
            self.logger.info(f"[OAUTH_FLOW] Handling {provider} user")
            
            # Validate required fields
            required_fields = ["email", "name"]
            if not all(field in user_data for field in required_fields):
                self.logger.error("[OAUTH_FLOW] Missing required fields in user data")
                raise ValueError("Missing required user data fields")

            # Check if user exists
            self.logger.info(f"[OAUTH_FLOW] Looking up user by email: {user_data['email']}")
            result = await self.db.execute(
                select(User).where(User.email == user_data["email"])
            )
            user = result.scalar_one_or_none()

            if not user:
                self.logger.info("[OAUTH_FLOW] Creating new user")
                
                # Create default organization for new user
                from cahoots_core.models.db_models import Organization
                import secrets
                
                org = Organization(
                    name=f"{user_data['name']}'s Organization",
                    email=user_data["email"],
                    api_key=f"org_{secrets.token_urlsafe(32)}",
                    subscription_tier="free",
                    subscription_status="active"
                )
                self.db.add(org)
                await self.db.commit()
                
                # Create user with organization
                user = User(
                    email=user_data["email"],
                    name=user_data["name"],
                    picture=user_data.get("picture"),  # Make picture optional
                    organization_id=org.id,  # Set organization ID
                    is_verified=True  # Social users are pre-verified
                )
                self.db.add(user)
                await self.db.commit()
                await self.db.refresh(user)
                self.logger.info(f"[OAUTH_FLOW] Created new user with ID: {user.id}")
            else:
                self.logger.info(f"[OAUTH_FLOW] Found existing user with ID: {user.id}")

            # Create session tokens
            self.logger.info("[OAUTH_FLOW] Creating session tokens")
            access_token, refresh_token = await self.security_manager.create_session(str(user.id))
            self.logger.info("[OAUTH_FLOW] Successfully created session tokens")

            return user, access_token, refresh_token

        except Exception as e:
            self.logger.error(f"[OAUTH_FLOW] Error handling social user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to handle social user: {str(e)}"
            ) 