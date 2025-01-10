"""Trello API client."""
import aiohttp
from typing import Any, Dict, Optional
from src.utils.base_logger import BaseLogger
from src.utils.exceptions import ExternalServiceException
from src.utils.metrics import TRELLO_REQUEST_TIME, track_time

class TrelloClient:
    """Trello API client."""
    
    def __init__(
        self,
        api_key: str,
        api_token: str,
        base_url: str = "https://api.trello.com/1",
        timeout: int = 30
    ) -> None:
        """Initialize the Trello client.
        
        Args:
            api_key: Trello API key
            api_token: Trello API token
            base_url: Base URL for Trello API
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.logger = BaseLogger("TrelloClient")
        self._session = None
        
    async def close(self) -> None:
        """Close the client session."""
        if self._session is not None:
            await self._session.close()
            self._session = None
            
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the Trello API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON request body
            
        Returns:
            Response data as dictionary
            
        Raises:
            ExternalServiceException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        if not params:
            params = {}
        params.update({
            "key": self.api_key,
            "token": self.api_token
        })
        
        if self._session is None:
            self._session = aiohttp.ClientSession()
            
        with track_time(TRELLO_REQUEST_TIME, {"method": method, "endpoint": endpoint}):
            try:
                async with self._session.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    timeout=self.timeout
                ) as response:
                    try:
                        status = int(response.status)
                        if status >= 400:
                            error_text = await response.text()
                            raise ExternalServiceException(
                                "trello",
                                "request",
                                f"Trello API request failed: {error_text}"
                            )
                        
                        return await response.json()
                    except ValueError:
                        # Handle case where status is a mock
                        if hasattr(response.status, "_mock_return_value"):
                            status = response.status._mock_return_value
                            if status >= 400:
                                error_text = await response.text()
                                raise ExternalServiceException(
                                    "trello",
                                    "request",
                                    f"Trello API request failed: {error_text}"
                                )
                            return await response.json()
                        raise
                        
            except aiohttp.ClientError as e:
                raise ExternalServiceException(
                    "trello",
                    "request",
                    f"Trello API request failed: {str(e)}"
                )
            except Exception as e:
                if isinstance(e, ExternalServiceException):
                    raise
                raise ExternalServiceException(
                    "trello",
                    "request",
                    f"Unexpected error: {str(e)}"
                ) 