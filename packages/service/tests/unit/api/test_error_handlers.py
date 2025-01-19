"""Tests for API error handlers."""
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.testclient import TestClient
from starlette.middleware.errors import ServerErrorMiddleware

from src.api.error_handlers import register_error_handlers
from src.utils.exceptions import BaseError

# Test app setup
@pytest.fixture
def app():
    """Create test FastAPI app with error handlers."""
    app = FastAPI()
    
    # Register error handlers
    register_error_handlers(app)
    
    class Item(BaseModel):
        name: str = Field(..., min_length=3)
        price: float = Field(..., gt=0)
    
    @app.get("/test-http-error")
    async def test_http_error():
        raise HTTPException(status_code=404, detail="Item not found")
    
    @app.get("/test-generic-error")
    async def test_generic_error():
        raise ValueError("Test generic error")
    
    @app.post("/test-validation-error")
    async def test_validation_error(item: Item):
        return item
    
    @app.get("/test-app-error")
    async def test_app_error():
        raise BaseError(
            code="TEST_ERROR",
            message="Test error message",
            details={"test": "details"}
        )
    
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

def test_http_exception_handler(client):
    """Test handling of HTTP exceptions."""
    response = client.get("/test-http-error")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "HTTP_404"
    assert data["error"]["message"] == "Item not found"
    assert data["error"]["status_code"] == 404

def test_validation_exception_handler(client):
    """Test handling of validation errors."""
    response = client.post(
        "/test-validation-error",
        json={"name": "a", "price": -1}
    )
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Request validation failed"
    assert len(data["error"]["details"]) == 2
    
    errors = {e["field"]: e["message"] for e in data["error"]["details"]}
    assert "name" in errors
    assert "price" in errors

def test_app_exception_handler(client):
    """Test handling of application-specific errors."""
    response = client.get("/test-app-error")
    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "TEST_ERROR"
    assert data["error"]["message"] == "Test error message"
    assert data["error"]["details"] == {"test": "details"}

def test_generic_exception_handler(client):
    """Test handling of unhandled exceptions."""
    try:
        response = client.get("/test-generic-error")
        assert False, "Expected ValueError to be raised"
    except ValueError as e:
        assert str(e) == "Test generic error"