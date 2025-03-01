"""Authentication domain commands"""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class RegisterUser:
    """Command to register a new user"""
    command_id: UUID
    correlation_id: UUID
    email: str
    password: str
    name: Optional[str] = None
    agent_id: Optional[UUID] = None


@dataclass
class VerifyEmail:
    """Command to verify a user's email"""
    command_id: UUID
    correlation_id: UUID
    user_id: UUID
    verification_token: str


@dataclass
class LoginUser:
    """Command to log in a user"""
    command_id: UUID
    correlation_id: UUID
    email: str
    password: str


@dataclass
class RequestPasswordReset:
    """Command to request a password reset"""
    command_id: UUID
    correlation_id: UUID
    email: str


@dataclass
class ResetPassword:
    """Command to reset a password"""
    command_id: UUID
    correlation_id: UUID
    user_id: UUID
    reset_token: str
    new_password: str


@dataclass
class RefreshToken:
    """Command to refresh an access token"""
    command_id: UUID
    correlation_id: UUID
    user_id: UUID
    refresh_token: str


@dataclass
class LogoutUser:
    """Command to log out a user"""
    command_id: UUID
    correlation_id: UUID
    user_id: UUID
    session_id: UUID


@dataclass
class RevokeSession:
    """Command to revoke a session"""
    command_id: UUID
    correlation_id: UUID
    user_id: UUID
    session_id: UUID