import pytest
import httpx
from datetime import datetime, UTC
import time
from app.core.config import settings

# Constants
BASE_URL = "http://localhost:8000"

@pytest.fixture
def client():
    """Create a test client that connects to the running server"""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        yield client

@pytest.fixture
def test_user():
    """Test user credentials"""
    return {
        "email": f"test_{int(datetime.now(UTC).timestamp())}@example.com",
        "password": "SecureTestPass123!"
    }

@pytest.mark.order(2)
def test_signup_flow(client, test_user):
    """Test basic signup without verification"""
    response = client.post("/v1/auth/sign_up", json=test_user)
    assert response.status_code == 200
    assert "message" in response.json()
    assert "email" in response.json()

@pytest.mark.order(3)
@pytest.mark.rate_limited
def test_rate_limiting_flow(client):
    """Test rate limiting on signup"""
    print("\nTesting rate limiting on signup...")
    # First create a test user that we'll use for other endpoints
    test_email = f"test_{datetime.now(UTC).timestamp()}@example.com"
    test_user = {
        "email": test_email,
        "password": "TestPass123!"
    }
    
    signup_responses = []
    for i in range(7):  # Try more than the limit (5/minute)
        response = client.post("/v1/auth/sign_up", json={
            "email": f"test_{datetime.now(UTC).timestamp()}_{i}@example.com",
            "password": "TestPass123!"
        })
        print(f"Signup request {i+1}: {response.status_code} - {response.text}")
        signup_responses.append(response.status_code)
        time.sleep(0.1)
    
    # Check rate limiting was triggered
    assert 429 in signup_responses, "Rate limiting not triggered"
    assert signup_responses.count(429) > 0, "No requests were rate limited" 