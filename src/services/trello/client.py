"""Trello HTTP client implementation."""
from typing import Any, Dict, Optional
import httpx
from src.utils.logger import Logger
from src.utils.metrics import track_time, TRELLO_REQUEST_TIME, TRELLO_ERROR_COUNTER
from src.utils.exceptions import ExternalServiceException

class TrelloClient:
    """Low-level client for Trello API communication."""
    
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
        self.base_url = base_url
        self.timeout = timeout
        self.logger = Logger("TrelloClient")
        self._client = httpx.AsyncClient(timeout=timeout)
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
        
    def _get_auth_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add authentication parameters to the request.
        
        Args:
            params: Optional query parameters
            
        Returns:
            Dict with auth parameters added
        """
        auth_params = {
            "key": self.api_key,
            "token": self.api_token
        }
        if params:
            auth_params.update(params)
        return auth_params
        
    @track_time(TRELLO_REQUEST_TIME, {"method": "GET", "endpoint": "/test"})
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to the Trello API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON request body
            
        Returns:
            Response data as dictionary
            
        Raises:
            ExternalServiceException: If the request fails
        """
        # Ensure base_url has protocol
        base_url = str(self.base_url)  # Convert to string in case it's not
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'https://' + base_url.lstrip('/')
            
        url = f"{base_url}{endpoint}"
        params = self._get_auth_params(params)
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            with track_time(TRELLO_REQUEST_TIME, {"method": method, "endpoint": endpoint}):
                response = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json_data
                )
                await response.raise_for_status()
                return response.json()
                
        except httpx.UnsupportedProtocol as e:
            TRELLO_ERROR_COUNTER.labels(
                method=method,
                endpoint=endpoint,
                status_code=400  # Bad Request
            ).inc()
            self.logger.error(f"Invalid URL protocol: {str(e)}")
            raise ExternalServiceException(
                service="Trello",
                operation=f"{method} {endpoint}",
                error=f"Invalid URL protocol: {str(e)}"
            )
                
        except httpx.ConnectError as e:
            TRELLO_ERROR_COUNTER.labels(
                method=method,
                endpoint=endpoint,
                status_code=503  # Service Unavailable
            ).inc()
            self.logger.error(f"Connection error during Trello request: {str(e)}")
            raise ExternalServiceException(
                service="Trello",
                operation=f"{method} {endpoint}",
                error=f"Failed to connect to Trello API: {str(e)}"
            )
            
        except httpx.HTTPError as e:
            status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
            TRELLO_ERROR_COUNTER.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            self.logger.error(f"HTTP error during Trello request: {str(e)}")
            raise ExternalServiceException(
                service="Trello",
                operation=f"{method} {endpoint}",
                error=f"Trello API request failed: {str(e)}"
            )
            
        except Exception as e:
            TRELLO_ERROR_COUNTER.labels(
                method=method,
                endpoint=endpoint,
                status_code=500
            ).inc()
            self.logger.error(f"Unexpected error during Trello request: {str(e)}")
            raise ExternalServiceException(
                service="Trello",
                operation=f"{method} {endpoint}",
                error=f"Unexpected error during Trello request: {str(e)}"
            ) 