import pytest
import httpx
from datetime import datetime, UTC
import time
from app.core.config import settings
from jose import jwt

@pytest.fixture
def test_user_cleanup(client):    
    # Store created resources for cleanup
    created_resources = {
        "users": [],
        "api_keys": []
    }
    
    yield created_resources
    
    # Cleanup logic that runs even if test fails
    for user in created_resources["users"]:
        print(f"Cleaning up test user: {user['email']}")
        log = user
        response = client.post(f"/v1/auth/remove_user", json=user)
        if response.status_code >= 400:
            print(f"Error cleaning up user {log}: {response.text}")
            raise Exception(f"Error cleaning up user {log}: {response.text}")

@pytest.mark.order(2)
def test_signup_flow(client, test_user):
    """Test basic signup without verification"""
    response = client.post("/v1/auth/sign_up", json=test_user())
    
    # Print detailed debug information
    print(f"\nTest user: {test_user}")
    print(f"Status code: {response.status_code}")
    try:
        response_json = response.json()
        print(f"Response body: {response_json}")
        
        # Check if there's a specific error message
        if "detail" in response_json:
            print(f"Error detail: {response_json['detail']}")
    except Exception as e:
        print(f"Error parsing response: {e}")
        print(f"Raw response: {response.text}")
    
    # Original assertions
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
    
@pytest.mark.order(4)
def test_multiple_users_flow(client, test_user, test_user_cleanup):
    """
    Test multiple users creating and using API keys:
    1. User 1 signs up and creates an API key
    2. User 2 signs up and creates an API key
    3. User 1 uses their API key for an authenticated request
    """
    
    # Create unique emails for our test users
    user1 = test_user("1")
    user2 = test_user("2")
    
    test_user_cleanup["users"].append(user1)
    test_user_cleanup["users"].append(user2)
      
    # Step 1: User 1 signs up
    signup_response1 = client.post(
        "/v1/auth/sign_up",
        json=user1
    )
    assert signup_response1.status_code == 200, f"User 1 signup failed: {signup_response1.text}"  
  
    # ... and User 1 creates an API key
    api_key_response1 = client.post(
        "/v1/auth/create_api_key",
        json=user1
    )
    assert api_key_response1.status_code == 200, f"User 1 API key creation failed: {api_key_response1.text}"
    user1_api_key = api_key_response1.json().get("api_key")
    assert user1_api_key, "No API key returned for User 1"
    
    # Step 2: User 2 signs up
    signup_response2 = client.post(
        "/v1/auth/sign_up",
        json=user2
    )
    assert signup_response2.status_code == 200, f"User 2 signup failed: {signup_response2.text}"
    assert signup_response2.json()["email"] == user2["email"]
    
    # ... and User 2 creates an API key
    api_key_response2 = client.post(
        "/v1/auth/create_api_key",
        json=user2
    )
    assert api_key_response2.status_code == 200, f"User 2 API key creation failed: {api_key_response2.text}"
    user2_api_key = api_key_response2.json().get("api_key")
    assert user2_api_key, "No API key returned for User 2"
    
    # Verify the API keys are different
    assert user1_api_key != user2_api_key, "Both users received the same API key"
    
    # Step 3: At this point, User 2 is the last authenticated user. 
    # Now User 1 makes a request using their API key, which will not involve authentication.
    # Due to row-level security, and User 2 being still authenticated, it should sign out User 2 and use the service_role to check whether the API key is valid.
    # For this example, we'll use the credits endpoint which uses API keys and verification.
    credits_response = client.get(
        "/v1/auth/credits",
        headers={"Authorization": f"Bearer {user1_api_key}"}
    )
    assert credits_response.status_code == 200, f"User 1 authenticated request failed: {credits_response.text}"
    
    # Verify the response contains credits information
    credits_data = credits_response.json()
    assert "credits" in credits_data, "Credits information not found in response"
    
    # Step 4: List API keys for User 1
    list_keys_response = client.post(
        "/v1/auth/api_keys",
        json=user1
    )
    assert list_keys_response.status_code == 200
    api_keys_list = list_keys_response.json().get("api_keys", [])
    assert user1_api_key in api_keys_list, "User's API key not found in their keys list"
    
    # Step 5: Revoke User 1's API key
    revoke_response = client.delete(
        f"/v1/auth/revoke_api_key/{user1_api_key}",
        headers={"Authorization": f"Bearer {user1_api_key}"}
    )
    assert revoke_response.status_code == 200
    
    # Step 6: Verify the key no longer works
    invalid_key_response = client.get(
        "/v1/auth/credits",
        headers={"Authorization": f"Bearer {user1_api_key}"}
    )
    assert invalid_key_response.status_code == 401, "Revoked API key still works"
