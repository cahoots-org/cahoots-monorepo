"""User Settings API endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.models import (
    UserSettings,
    UserSettingsUpdateRequest,
    UserSettingsResponse,
    TrelloIntegration,
    JiraIntegration
)
from app.storage import UserSettingsStorage
from app.api.dependencies import get_current_user, get_redis_client
from app.storage.redis_client import RedisClient


router = APIRouter(prefix="/api/settings", tags=["settings"])


async def get_settings_storage(
    redis_client: RedisClient = Depends(get_redis_client)
) -> UserSettingsStorage:
    """Get user settings storage instance."""
    return UserSettingsStorage(redis_client)


@router.get("")
async def get_user_settings(
    current_user: dict = Depends(get_current_user),
    settings_storage: UserSettingsStorage = Depends(get_settings_storage)
) -> UserSettingsResponse:
    """Get current user's settings.

    Returns user settings from Redis. If settings don't exist, returns default settings.
    """
    user_id = current_user["id"]

    # Try to get existing settings
    settings = await settings_storage.get_settings(user_id)

    if not settings:
        # Create default settings for new user
        settings = UserSettings(user_id=user_id)
        await settings_storage.save_settings(settings)

    return UserSettingsResponse(data=settings)


@router.put("")
async def update_user_settings(
    request: UserSettingsUpdateRequest,
    current_user: dict = Depends(get_current_user),
    settings_storage: UserSettingsStorage = Depends(get_settings_storage)
) -> UserSettingsResponse:
    """Update current user's settings.

    Accepts partial updates - only provided fields will be updated.
    """
    user_id = current_user["id"]

    # Get existing settings or create new
    settings = await settings_storage.get_settings(user_id)

    if not settings:
        settings = UserSettings(user_id=user_id)

    # Apply updates (only update fields that are provided)
    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(settings, field):
            # Convert dicts to proper model objects for integration settings
            if field == 'trello_integration' and isinstance(value, dict):
                value = TrelloIntegration(**value)
            elif field == 'jira_integration' and isinstance(value, dict):
                value = JiraIntegration(**value)
            setattr(settings, field, value)

    # Save updated settings
    await settings_storage.save_settings(settings)

    return UserSettingsResponse(data=settings)


@router.patch("")
async def patch_user_settings(
    updates: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    settings_storage: UserSettingsStorage = Depends(get_settings_storage)
) -> UserSettingsResponse:
    """Partially update user settings with arbitrary fields.

    This endpoint allows updating individual settings fields without providing
    the entire settings object. Useful for quick updates from the frontend.
    """
    user_id = current_user["id"]

    # Use the storage's partial update method
    updated_settings = await settings_storage.update_partial(user_id, updates)

    if not updated_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found"
        )

    return UserSettingsResponse(data=updated_settings)


@router.delete("")
async def delete_user_settings(
    current_user: dict = Depends(get_current_user),
    settings_storage: UserSettingsStorage = Depends(get_settings_storage)
) -> Dict[str, str]:
    """Delete current user's settings (reset to defaults)."""
    user_id = current_user["id"]

    deleted = await settings_storage.delete_settings(user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found"
        )

    return {"message": "Settings deleted successfully"}
