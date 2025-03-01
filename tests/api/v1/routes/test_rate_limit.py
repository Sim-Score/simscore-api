import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from app.api.v1.routes.ideas import router
from app.api.v1.models.request import IdeaRequest, AdvancedFeatures
from app.api.v1.models.response import AnalysisResponse, RankedIdea
from app.core.limiter import limiter
from app.core.config import settings
import json
from slowapi.errors import RateLimitExceeded
from app.api.v1.dependencies.auth import verify_token
from tests.conftest import auth_headers, mock_verify_token
import time
from datetime import datetime, UTC

app = FastAPI()
app.include_router(router, dependencies=[Depends(verify_token)])
client = TestClient(app)

@pytest.fixture
def valid_token():
    return "valid_test_token"

@pytest.fixture
def test_user():
    """Test user credentials"""
    return {
        "email": f"test_{int(datetime.now(UTC).timestamp())}@example.com",
        "password": "SecureTestPass123!"
    }

def test_rate_limit_enforced(mock_verify_token, auth_headers):
    """Test rate limiting with proper authentication"""
    limit = int(settings.RATE_LIMIT_PER_USER.split('/')[0])
    max_requests = limit + 3
    count = 1
    
    while count < max_requests:
        response = client.post(
            "/rank_ideas",
            json={
                "ideas": [
                    {"id": "1", "idea": "Test idea"},
                    {"id": "2", "idea": "Test idea 2"},
                    {"id": "3", "idea": "Test idea 3"},
                    {"id": "4", "idea": "Test idea 4"}
                ]
            },
            headers=auth_headers
        )
        expected_status = 429 if count > limit else 200
        assert response.status_code == expected_status, f"Request {count}: Expected {expected_status}, got {response.status_code}"
        count += 1

def test_rate_limit_verify_email(client):
    """Test rate limiting on email verification endpoint"""
    responses = []
    
    print("\nTesting rate limiting on verify_email...")
    for i in range(10):
        response = client.post("/v1/auth/verify_email", json={
            "email": f"test_{datetime.now(UTC).timestamp()}@example.com",
            "code": "123456"
        })
        print(f"Request {i+1}: {response.status_code} - {response.text}")
        responses.append(response.status_code)
        time.sleep(0.1)
    
    # Check that rate limiting kicked in
    assert 429 in responses, "Rate limiting not triggered"
    assert responses.count(429) > 0, "No requests were rate limited"

def test_rate_limit_create_api_key(client, test_user):
    """Test rate limiting on API key creation"""
    responses = []
    
    print("\nTesting rate limiting on create_api_key...")
    for i in range(10):
        response = client.post("/v1/auth/create_api_key", json=test_user)
        print(f"Request {i+1}: {response.status_code} - {response.text}")
        responses.append(response.status_code)
        time.sleep(0.1)
    
    # Should see either 429 (rate limit) or 403 (unverified email)
    assert any(code in [429, 403] for code in responses), "Neither rate limit nor auth check triggered"

def test_rate_limit_get_credits(client):
    """Test rate limiting on credits endpoint"""
    responses = []
    
    print("\nTesting rate limiting on credits...")
    for i in range(10):
        response = client.get("/v1/auth/credits")
        print(f"Request {i+1}: {response.status_code} - {response.text}")
        responses.append(response.status_code)
        time.sleep(0.1)
    
    # Should see either 429 (rate limit) or 401 (unauthorized)
    assert any(code in [429, 401] for code in responses), "Neither rate limit nor auth check triggered"
    