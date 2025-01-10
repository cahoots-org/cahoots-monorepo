"""SSO session management."""
from typing import Dict, Optional
from datetime import datetime, timedelta
import json
import uuid
from redis.asyncio import Redis
from fastapi import HTTPException, status

class SSOSession:
    """SSO session management."""

    def __init__(self, redis: Redis, session_timeout: int = 3600):
        """Initialize session manager.
        
        Args:
            redis: Redis client instance
            session_timeout: Session timeout in seconds
        """
        self.redis = redis
        self.session_timeout = session_timeout

    async def create_session(self, user_data: Dict, provider_id: str) -> str:
        """Create a new SSO session.
        
        Args:
            user_data: User data from SAML assertion
            provider_id: Identity provider ID
            
        Returns:
            str: Session token
        """
        session_id = str(uuid.uuid4())
        session_data = {
            'user_data': user_data,
            'provider_id': provider_id,
            'created_at': datetime.utcnow().isoformat(),
            'last_accessed': datetime.utcnow().isoformat()
        }

        # Store session in Redis
        await self.redis.setex(
            f"sso_session:{session_id}",
            self.session_timeout,
            json.dumps(session_data)
        )

        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[Dict]: Session data if found
        """
        session_key = f"sso_session:{session_id}"
        session_data = await self.redis.get(session_key)

        if not session_data:
            return None

        # Parse session data
        session = json.loads(session_data)
        
        # Update last accessed time
        session['last_accessed'] = datetime.utcnow().isoformat()
        await self.redis.setex(
            session_key,
            self.session_timeout,
            json.dumps(session)
        )

        return session

    async def validate_session(self, session_id: str) -> Dict:
        """Validate and return session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict: Session data
            
        Raises:
            HTTPException: If session is invalid or expired
        """
        session = await self.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session"
            )

        # Check if session is expired
        last_accessed = datetime.fromisoformat(session['last_accessed'])
        if (datetime.utcnow() - last_accessed) > timedelta(seconds=self.session_timeout):
            await self.end_session(session_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired"
            )

        return session

    async def end_session(self, session_id: str) -> None:
        """End an SSO session.
        
        Args:
            session_id: Session ID to end
        """
        await self.redis.delete(f"sso_session:{session_id}")

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        pattern = "sso_session:*"
        cleaned = 0
        
        # Scan for session keys
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor,
                match=pattern,
                count=100
            )
            
            for key in keys:
                session_data = await self.redis.get(key)
                if session_data:
                    session = json.loads(session_data)
                    last_accessed = datetime.fromisoformat(session['last_accessed'])
                    
                    if (datetime.utcnow() - last_accessed) > timedelta(seconds=self.session_timeout):
                        await self.redis.delete(key)
                        cleaned += 1
            
            if cursor == 0:
                break

        return cleaned 