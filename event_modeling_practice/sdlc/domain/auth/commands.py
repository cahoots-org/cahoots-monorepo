"""Authentication domain commands"""
from dataclasses import dataclass
from uuid import UUID
from ..commands import Command


@dataclass
class RegisterUser(Command):
    """Command to register a new user"""
    email: str
    password: str


@dataclass
class VerifyEmail(Command):
    """Command to verify a user's email"""
    user_id: UUID
    verification_token: str


@dataclass
class Login(Command):
    """Command to log in a user"""
    email: str
    password: str


@dataclass
class RequestPasswordReset(Command):
    """Command to request a password reset"""
    email: str


@dataclass
class ResetPassword(Command):
    """Command to reset a password"""
    user_id: UUID
    reset_token: str
    new_password: str


@dataclass
class RefreshToken(Command):
    """Command to refresh an access token"""
    user_id: UUID
    refresh_token: str


@dataclass
class Logout(Command):
    """Command to log out a user"""
    user_id: UUID
    session_id: UUID


@dataclass
class RevokeSession(Command):
    """Command to revoke a session"""
    user_id: UUID
    session_id: UUID 