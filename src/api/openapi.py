"""OpenAPI specification configuration."""
from fastapi.openapi.utils import get_openapi
from src.api.main import app

def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="AI Dev Team API",
        version="1.0.0",
        description="""
        AI Dev Team API provides a set of endpoints for managing AI-powered software development projects.
        
        ## Features
        
        * Project Management
        * Task Automation
        * Code Generation
        * Code Review
        * Testing
        
        ## Authentication
        
        All endpoints require API key authentication using the `X-API-Key` header.
        
        ## Rate Limiting
        
        API requests are limited to 60 requests per minute per API key.
        
        ## Error Handling
        
        The API uses standard HTTP status codes and returns error details in the response body:
        
        ```json
        {
            "detail": "Error message"
        }
        ```
        """,
        routes=app.routes,
    )

    # Custom extension to add authentication
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication"
        }
    }

    # Apply security globally
    openapi_schema["security"] = [{"ApiKeyAuth": []}]

    # Add response schemas
    openapi_schema["components"]["schemas"].update({
        "HTTPError": {
            "type": "object",
            "properties": {
                "detail": {
                    "type": "string",
                    "description": "Error message"
                }
            }
        },
        "HealthCheck": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "example": "healthy"
                },
                "environment": {
                    "type": "string",
                    "example": "production"
                },
                "redis_connected": {
                    "type": "boolean",
                    "example": True
                }
            }
        }
    })

    # Add tags for better organization
    openapi_schema["tags"] = [
        {
            "name": "Projects",
            "description": "Project management operations"
        },
        {
            "name": "Monitoring",
            "description": "Health and metrics endpoints"
        }
    ]

    # Customize servers based on environment
    openapi_schema["servers"] = [
        {
            "url": "https://api.aidevteam.com",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.aidevteam.com",
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Set custom OpenAPI schema
app.openapi = custom_openapi 