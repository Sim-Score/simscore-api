import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app.api.v1.routes.auth import router, UserCredentials, SignupResponse, MessageResponse
from app.core.config import settings

# Set up the FastAPI app and TestClient
app = FastAPI()
app.include_router(router)  # Include the authentication router
client = TestClient(app)

@pytest.fixture
def valid_user_data():
    """Fixture for valid user data."""
    return {
        "email": "testuser@example.com",
        "password": "securepassword"
    }

@pytest.fixture
def duplicate_user_data():
    """Fixture for duplicate user data."""
    return {
        "email": "duplicateuser@example.com",
        "password": "securepassword"
    }

def test_signup_success(valid_user_data):
    """Test successful user signup."""
    response = client.post("/auth/sign_up", json=valid_user_data)
    assert response.status_code == 200
    assert response.json() == {
        "message": "Registration successful. Please check your email to verify your account.",
        "email": valid_user_data["email"]
    }

def test_signup_duplicate_email(duplicate_user_data):
    """Test signup with duplicate email."""
    # First signup
    response = client.post("/auth/sign_up", json=duplicate_user_data)
    assert response.status_code == 200  # First registration should succeed

    # Second signup with the same email
    response = client.post("/auth/sign_up", json=duplicate_user_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()  # Adjust based on your error message

def test_signup_invalid_email_format():
    """Test signup with invalid email format."""
    invalid_user_data = {
        "email": "invalid-email",
        "password": "securepassword"
    }
    response = client.post("/auth/sign_up", json=invalid_user_data)
    assert response.status_code == 422  # Unprocessable Entity for validation errors

def test_signup_missing_email(valid_user_data):
    """Test signup with missing email."""
    user_data = valid_user_data.copy()
    user_data.pop("email")  # Remove email
    response = client.post("/auth/sign_up", json=user_data)
    assert response.status_code == 422  # Unprocessable Entity for validation errors

def test_signup_missing_password(valid_user_data):
    """Test signup with missing password."""
    user_data = valid_user_data.copy()
    user_data.pop("password")  # Remove password
    response = client.post("/auth/sign_up", json=user_data)
    assert response.status_code == 422  # Unprocessable Entity for validation errors

def test_signup_short_password(valid_user_data):
    """Test signup with a short password."""
    user_data = valid_user_data.copy()
    user_data["password"] = "short"  # Short password
    response = client.post("/auth/sign_up", json=user_data)
    assert response.status_code == 400  # Adjust based on your error handling for weak passwords

# Additional tests can be added as needed 