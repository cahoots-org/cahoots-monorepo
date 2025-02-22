from dataclasses import dataclass
from uuid import UUID
from ..commands import Command


@dataclass
class RegisterUser(Command):
    email: str
    password: str


@dataclass
class VerifyEmail(Command):
    user_id: UUID
    verification_token: str


@dataclass
class Login(Command):
    email: str
    password: str


@dataclass
class RequestPasswordReset(Command):
    email: str


@dataclass
class ResetPassword(Command):
    user_id: UUID
    reset_token: str
    new_password: str


@dataclass
class RefreshToken(Command):
    refresh_token: str


@dataclass
class Logout(Command):
    user_id: UUID
    session_id: UUID


@dataclass
class RevokeSession(Command):
    user_id: UUID
    session_id: UUID 