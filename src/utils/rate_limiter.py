"""Rate limiter utility."""
from typing import Dict, Any
from datetime import datetime, timedelta
import time

class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, limit: int = 100, window: int = 60):
        """Initialize rate limiter.
        
        Args:
            limit: Maximum number of requests per window
            window: Time window in seconds
        """
        self.limit = limit
        self.window = window
        self._requests: Dict[str, list] = {}
        
    def check_rate_limit(self, key: str) -> bool:
        """Check if request is within rate limit.
        
        Args:
            key: Identifier for the rate limit bucket
            
        Returns:
            bool: True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        
        # Initialize request list if not exists
        if key not in self._requests:
            self._requests[key] = []
            
        # Remove expired requests
        self._requests[key] = [ts for ts in self._requests[key] if ts > now - self.window]
        
        # Check if limit exceeded
        if len(self._requests[key]) >= self.limit:
            return False
            
        # Add current request
        self._requests[key].append(now)
        return True
        
    def get_limit(self, key: str) -> Dict[str, Any]:
        """Get rate limit information.
        
        Args:
            key: Identifier for the rate limit bucket
            
        Returns:
            Dict containing limit information
        """
        now = time.time()
        
        # Initialize request list if not exists
        if key not in self._requests:
            self._requests[key] = []
            
        # Remove expired requests
        self._requests[key] = [ts for ts in self._requests[key] if ts > now - self.window]
        
        # Calculate remaining requests
        remaining = max(0, self.limit - len(self._requests[key]))
        
        # Calculate reset time
        if len(self._requests[key]) > 0:
            oldest = min(self._requests[key])
            reset_at = datetime.fromtimestamp(oldest + self.window)
        else:
            reset_at = datetime.fromtimestamp(now + self.window)
            
        return {
            "limit": self.limit,
            "remaining": remaining,
            "reset_at": reset_at.isoformat()
        } 