"""User Settings Models"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class TrelloIntegration(BaseModel):
    """Trello integration settings"""
    enabled: bool = False
    api_key: Optional[str] = None
    token: Optional[str] = None


class JiraIntegration(BaseModel):
    """Jira integration settings"""
    enabled: bool = False
    jira_url: Optional[str] = None
    user_email: Optional[str] = None
    api_token: Optional[str] = None
    account_id: Optional[str] = None


class UserSettings(BaseModel):
    """User settings and preferences"""

    # User identification
    user_id: str

    # General preferences
    dark_mode: bool = False
    notifications: bool = True

    # Integrations
    trello_integration: TrelloIntegration = Field(default_factory=TrelloIntegration)
    jira_integration: JiraIntegration = Field(default_factory=JiraIntegration)

    # Additional settings (for future expansion)
    custom_settings: Dict[str, Any] = Field(default_factory=dict)

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "user_id": self.user_id,
            "dark_mode": self.dark_mode,
            "notifications": self.notifications,
            "trello_integration": self.trello_integration.model_dump() if hasattr(self.trello_integration, 'model_dump') else self.trello_integration,
            "jira_integration": self.jira_integration.model_dump() if hasattr(self.jira_integration, 'model_dump') else self.jira_integration,
            "custom_settings": self.custom_settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSettings":
        """Create UserSettings from dictionary"""
        return cls(
            user_id=data["user_id"],
            dark_mode=data.get("dark_mode", False),
            notifications=data.get("notifications", True),
            trello_integration=TrelloIntegration(**data.get("trello_integration", {})),
            jira_integration=JiraIntegration(**data.get("jira_integration", {})),
            custom_settings=data.get("custom_settings", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        )


class UserSettingsUpdateRequest(BaseModel):
    """Request model for updating user settings"""
    dark_mode: Optional[bool] = None
    notifications: Optional[bool] = None
    trello_integration: Optional[Dict[str, Any]] = None
    jira_integration: Optional[Dict[str, Any]] = None
    custom_settings: Optional[Dict[str, Any]] = None


class UserSettingsResponse(BaseModel):
    """Response model for user settings"""
    data: UserSettings
