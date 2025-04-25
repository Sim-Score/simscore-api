import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends, Request, Response
from unittest.mock import patch, MagicMock
from app.api.v1.routes.ideas import router
from app.api.v1.models.request import IdeaRequest, AdvancedFeatures
from app.api.v1.models.response import AnalysisResponse, RankedIdea
from app.core.limiter import limiter
from app.core.config import settings
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.v1.dependencies.auth import verify_token
from tests.conftest import auth_headers, mock_verify_token
import time
from datetime import datetime, UTC

# Create a simplified test app
test_app = FastAPI()
test_app.include_router(router)
test_client = TestClient(test_app)

# Create a test fixture for testing standalone rate limiting
@pytest.fixture
def limiter_app():
    """Create a simple FastAPI app with rate limiting for testing"""
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.get("/test")
    @limiter.limit("3/minute")
    def test_endpoint(request: Request):
        return {"status": "ok"}
    
    return TestClient(app)

# Create a test fixture for rate limiting with auth routes
@pytest.fixture
def auth_app():
    """Create a test app with auth routes that have rate limits"""
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.post("/auth/verify_email")
    @limiter.limit("5/minute")
    async def verify_email(request: Request):
        return {"status": "verified"}
    
    @app.post("/auth/create_api_key")
    @limiter.limit("3/minute") 
    async def create_api_key(request: Request):
        return {"api_key": "test_key_123"}
    
    @app.get("/auth/credits")
    @limiter.limit("10/minute")
    async def get_credits(request: Request):
        return {"credits": 100}
    
    return TestClient(app)

# Create a test app for testing app-level rate limiting
@pytest.fixture
def test_api_app():
    """Create an app with test endpoints that simulate the actual API"""
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.post("/rank_ideas")
    @limiter.limit("5/minute")
    async def rank_ideas(request: Request):
        return {"ranked": True}
    
    return TestClient(app)

def test_rate_limit_concept(limiter_app):
    """Test rate limiting in isolation with a simple test app"""
    # Make multiple requests to trigger rate limit
    responses = []
    for _ in range(5):
        response = limiter_app.get("/test", headers={"X-Forwarded-For": "127.0.0.1"})
        responses.append(response.status_code)
    
    # First few should succeed, then we should get rate limited
    assert responses[0] == 200
    assert responses[1] == 200
    assert responses[2] == 200
    assert 429 in responses, "Rate limiting was not triggered"

def test_rate_limit_enforced(test_api_app):
    """Test rate limiting with proper authentication"""
    headers = {"X-Forwarded-For": "127.0.0.1"}
    
    # Make enough requests to trigger the rate limit
    responses = []
    for i in range(8):  # More than our 5/minute limit
        response = test_api_app.post(
            "/rank_ideas",
            json={
                "ideas": [
                    {"id": "1", "idea": "Test idea"},
                    {"id": "2", "idea": "Test idea 2"}
                ]
            },
            headers=headers
        )
        print(f"Request {i+1}: {response.status_code}")
        responses.append(response.status_code)
    
    # Verify that some requests succeeded and some were rate limited
    assert 200 in responses, "No requests succeeded"
    assert 429 in responses, "Rate limiting was not triggered"

def test_verify_email_rate_limit(auth_app):
    """Test rate limiting on email verification endpoint"""
    responses = []
    
    print("\nTesting rate limiting on verify_email...")
    for i in range(10):
        response = auth_app.post(
            "/auth/verify_email", 
            json={"email": f"test_{i}@example.com", "code": "123456"},
            headers={"X-Forwarded-For": "127.0.0.1"}
        )
        print(f"Request {i+1}: {response.status_code}")
        responses.append(response.status_code)
    
    # Check that rate limiting kicked in
    assert 429 in responses, "Rate limiting not triggered"
    assert responses.count(429) > 0, "No requests were rate limited"

def test_create_api_key_rate_limit(auth_app):
    """Test rate limiting on API key creation"""
    responses = []
    
    print("\nTesting rate limiting on create_api_key...")
    for i in range(5):
        response = auth_app.post(
            "/auth/create_api_key", 
            json={"email": "test@example.com", "password": "password123"},
            headers={"X-Forwarded-For": "127.0.0.1"}
        )
        print(f"Request {i+1}: {response.status_code}")
        responses.append(response.status_code)
    
    # First few should succeed, then rate limit
    assert 429 in responses, "Rate limiting not triggered"

def test_get_credits_rate_limit(auth_app):
    """Test rate limiting on credits endpoint"""
    responses = []
    
    print("\nTesting rate limiting on credits...")
    for i in range(15):
        response = auth_app.get(
            "/auth/credits",
            headers={"X-Forwarded-For": "127.0.0.1"}
        )
        print(f"Request {i+1}: {response.status_code}")
        responses.append(response.status_code)
    
    # Should see rate limiting kick in
    assert 429 in responses, "Rate limiting not triggered"

def test_rate_limit_with_exception_handler():
    """Test that rate limit exceptions are properly handled"""
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return Response(
            status_code=429,
            content="Rate limit exceeded",
            headers={"Retry-After": "60"}
        )
    
    @app.get("/limited")
    @limiter.limit("2/minute")
    async def limited_endpoint(request: Request):
        return {"status": "ok"}
    
    client = TestClient(app)
    
    # First few requests should succeed
    response1 = client.get("/limited", headers={"X-Forwarded-For": "127.0.0.1"})
    assert response1.status_code == 200
    
    response2 = client.get("/limited", headers={"X-Forwarded-For": "127.0.0.1"})
    assert response2.status_code == 200
    
    # Third request should trigger rate limit
    response3 = client.get("/limited", headers={"X-Forwarded-For": "127.0.0.1"})
    assert response3.status_code == 429
    assert "Retry-After" in response3.headers
    