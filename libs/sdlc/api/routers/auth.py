from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

router = APIRouter()

class UserRegistration(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordReset(BaseModel):
    token: str
    new_password: str

@router.post("/register")
async def register(registration: UserRegistration, request: Request):
    """Register a new user"""
    try:
        events = request.state.auth_handler.handle_register_user(registration)
        return {"message": "Registration successful", "user_id": events[0].user_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
async def login(login_request: LoginRequest, request: Request):
    """Login a user"""
    try:
        events = request.state.auth_handler.handle_login(login_request)
        return {
            "access_token": events[0].access_token,
            "refresh_token": events[0].refresh_token,
            "token_type": "bearer"
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/password-reset/request")
async def request_password_reset(reset_request: PasswordResetRequest, request: Request):
    """Request a password reset"""
    try:
        events = request.state.auth_handler.handle_request_password_reset(reset_request)
        return {"message": "Password reset email sent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/password-reset/reset")
async def reset_password(reset: PasswordReset, request: Request):
    """Reset password with token"""
    try:
        events = request.state.auth_handler.handle_reset_password(reset)
        return {"message": "Password reset successful"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout")
async def logout(request: Request):
    """Logout current user"""
    try:
        events = request.state.auth_handler.handle_logout(request.state.current_user)
        return {"message": "Logged out successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) 