"""Service tier models."""
from enum import Enum

class ServiceTier(str, Enum):
    """Service tier levels."""
    
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    
    @property
    def project_limit(self) -> int:
        """Get max number of projects allowed for this tier."""
        limits = {
            self.FREE: 1,
            self.BASIC: 3,
            self.PROFESSIONAL: 10,
            self.ENTERPRISE: -1  # Unlimited
        }
        return limits[self]
    
    @property
    def agent_limit(self) -> int:
        """Get max number of concurrent agents allowed for this tier."""
        limits = {
            self.FREE: 1,
            self.BASIC: 2,
            self.PROFESSIONAL: 5,
            self.ENTERPRISE: -1  # Unlimited
        }
        return limits[self]
    
    @property
    def features(self) -> set[str]:
        """Get set of features enabled for this tier."""
        base_features = {"code_generation", "code_review"}
        tier_features = {
            self.FREE: base_features,
            self.BASIC: base_features | {"ux_design"},
            self.PROFESSIONAL: base_features | {"ux_design", "qa_testing", "deployment"},
            self.ENTERPRISE: base_features | {"ux_design", "qa_testing", "deployment", "custom_agents"}
        }
        return tier_features[self] 