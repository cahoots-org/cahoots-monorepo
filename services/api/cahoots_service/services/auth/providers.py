"""Authentication providers for social login."""
from typing import Dict
import aiohttp
from fastapi import HTTPException, status

class GoogleAuthProvider:
    """Google OAuth authentication provider."""
    
    def __init__(self, client_id: str, client_secret: str):
        """Initialize provider.
        
        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://oauth2.googleapis.com/token"
        self.user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
    async def get_user_info(self, code: str) -> Dict:
        """Get user info from Google.
        
        Args:
            code: Authorization code from OAuth flow
            
        Returns:
            User info dictionary
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Exchange code for tokens
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code"
                }) as resp:
                    if resp.status != 200:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Failed to authenticate with Google"
                        )
                    tokens = await resp.json()
                
                # Get user info
                headers = {"Authorization": f"Bearer {tokens['access_token']}"}
                async with session.get(self.user_info_url, headers=headers) as resp:
                    if resp.status != 200:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Failed to get Google user info"
                        )
                    return await resp.json()
                    
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google authentication failed: {str(e)}"
            )

class GitHubAuthProvider:
    """GitHub OAuth authentication provider."""
    
    def __init__(self, client_id: str, client_secret: str):
        """Initialize provider.
        
        Args:
            client_id: GitHub OAuth client ID
            client_secret: GitHub OAuth client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://github.com/login/oauth/access_token"
        self.user_info_url = "https://api.github.com/user"
        
    async def get_user_info(self, code: str) -> Dict:
        """Get user info from GitHub.
        
        Args:
            code: Authorization code from OAuth flow
            
        Returns:
            User info dictionary
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Exchange code for token
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_url,
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code
                    }
                ) as resp:
                    if resp.status != 200:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Failed to authenticate with GitHub"
                        )
                    tokens = await resp.json()
                
                # Get user info
                headers = {
                    "Authorization": f"Bearer {tokens['access_token']}",
                    "Accept": "application/json"
                }
                async with session.get(self.user_info_url, headers=headers) as resp:
                    if resp.status != 200:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Failed to get GitHub user info"
                        )
                    user_info = await resp.json()
                    
                # Get email if not public
                if not user_info.get("email"):
                    async with session.get(
                        "https://api.github.com/user/emails",
                        headers=headers
                    ) as resp:
                        if resp.status == 200:
                            emails = await resp.json()
                            primary_email = next(
                                (e for e in emails if e["primary"]),
                                emails[0] if emails else None
                            )
                            if primary_email:
                                user_info["email"] = primary_email["email"]
                                
                return user_info
                    
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"GitHub authentication failed: {str(e)}"
            ) 