"""OAuth providers for authentication."""
import logging
from typing import Dict, Any
import aiohttp
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class GoogleAuthProvider:
    """Google OAuth provider."""
    
    def __init__(self, client_id: str, client_secret: str):
        """Initialize Google auth provider.
        
        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def get_user_info(self, code_or_user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get user info from Google.
        
        Args:
            code_or_user_info: User info from frontend
            
        Returns:
            Dict containing user info
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            # We only handle direct user info now, no more API calls
            if not isinstance(code_or_user_info, dict):
                logger.error("[OAUTH_FLOW] Expected user info dict, got something else")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid user info format"
                )
            
            logger.info("[OAUTH_FLOW] Validating provided user info")
            required_fields = ["email", "id"]
            if not all(field in code_or_user_info for field in required_fields):
                logger.error("[OAUTH_FLOW] Missing required fields in user info")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing required fields in user info"
                )
            return code_or_user_info
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[OAUTH_FLOW] Error validating user info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to validate user info: {str(e)}"
            )

class GitHubAuthProvider:
    """GitHub OAuth provider."""
    
    def __init__(self, client_id: str, client_secret: str):
        """Initialize GitHub auth provider.
        
        Args:
            client_id: GitHub OAuth client ID
            client_secret: GitHub OAuth client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://github.com/login/oauth/access_token"
        self.user_info_url = "https://api.github.com/user"
        self.user_emails_url = "https://api.github.com/user/emails"
    
    async def get_user_info(self, code: str) -> Dict[str, Any]:
        """Get user info from GitHub.
        
        Args:
            code: Authorization code from GitHub
            
        Returns:
            Dict containing user info
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Exchange code for access token
                logger.info("[OAUTH_FLOW] Exchanging code for tokens with GitHub")
                
                token_data = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code
                }
                headers = {"Accept": "application/json"}
                
                async with session.post(self.token_url, json=token_data, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"[OAUTH_FLOW] GitHub OAuth error: {error_text}")
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"GitHub authentication failed: {error_text}"
                        )
                    
                    tokens = await resp.json()
                    if "error" in tokens:
                        logger.error(f"[OAUTH_FLOW] GitHub OAuth error: {tokens['error']}")
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"GitHub authentication failed: {tokens['error']}"
                        )
                
                # Get user info
                headers = {
                    "Authorization": f"token {tokens['access_token']}",
                    "Accept": "application/json"
                }
                
                # Get basic user info
                async with session.get(self.user_info_url, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"[OAUTH_FLOW] Failed to get GitHub user info: {error_text}")
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Failed to get user info from GitHub"
                        )
                    
                    user_info = await resp.json()
                
                # Get user emails since they're not included in basic info
                async with session.get(self.user_emails_url, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"[OAUTH_FLOW] Failed to get GitHub user emails: {error_text}")
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Failed to get user emails from GitHub"
                        )
                    
                    emails = await resp.json()
                    primary_email = next(
                        (email["email"] for email in emails if email["primary"]),
                        None
                    )
                    
                    if not primary_email:
                        logger.error("[OAUTH_FLOW] No primary email found in GitHub account")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No primary email found in GitHub account"
                        )
                    
                    user_info["email"] = primary_email
                    logger.info(f"[OAUTH_FLOW] Successfully retrieved user info for: {primary_email}")
                    return user_info
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[OAUTH_FLOW] Error in GitHub authentication: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"GitHub authentication failed: {str(e)}"
            ) 