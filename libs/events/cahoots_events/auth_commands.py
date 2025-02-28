"""Authentication domain commands"""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class RegisterUser:
    """Command to register a new user"""
    email: str
    password: str


@dataclass
class VerifyEmail:
    """Command to verify a user's email"""
    user_id: UUID
    verification_token: str


@dataclass
class LoginUser:
    """Command to log in a user"""
    email: str
    password: str


@dataclass
class RequestPasswordReset:
    """Command to request a password reset"""
    email: str


@dataclass
class ResetPassword:
    """Command to reset a password"""
    user_id: UUID
    reset_token: str
    new_password: str


@dataclass
class RefreshToken:
    """Command to refresh an access token"""
    user_id: UUID
    refresh_token: str


@dataclass
class LogoutUser:
    """Command to log out a user"""
    user_id: UUID
    session_id: UUID


@dataclass
class RevokeSession:
    """Command to revoke a session"""
    user_id: UUID
    session_id: UUID 