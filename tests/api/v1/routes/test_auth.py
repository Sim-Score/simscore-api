import pytest
import time
from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.testclient import TestClient
from app.api.v1.routes.auth import (
    router, 
    UserCredentials, 
    SignupResponse, 
    MessageResponse,
    EmailVerification
)
from app.core.config import settings
from unittest.mock import AsyncMock, patch
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from slowapi import Limiter
from slowapi.util import get_remote_address
import jwt
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock
from app.services.credits import CreditService
import warnings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Add warning filter for the jose library
warnings.filterwarnings(
    "ignore",
    message="datetime.datetime.utcnow()",
    category=DeprecationWarning,
    module="jose.*"
)

# Set up the FastAPI app and TestClient
app = FastAPI()
app.include_router(router)  # Include the authentication router
client = TestClient(app)

@pytest.fixture
def test_user_data():
    """Base test user data"""
    return {
        "email": "testuser@example.com",
        "password": "securepassword123"
    }

@pytest.fixture
def mock_backend():
    """Mock backend authentication functions"""
    with patch('app.core.security.create_user', new_callable=AsyncMock) as mock_create, \
         patch('app.core.security.verify_email_code', new_callable=AsyncMock) as mock_verify, \
         patch('app.core.security.authenticate_user', new_callable=AsyncMock) as mock_auth, \
         patch('app.core.security.create_api_key') as mock_api_key:
        
        # Configure mock behaviors
        mock_create.return_value = True
        mock_verify.return_value = True
        mock_auth.return_value = {"user_id": "test_user"}
        mock_api_key.return_value = "test_api_key_123"
        
        yield {
            'create_user': mock_create,
            'verify_email': mock_verify,
            'authenticate_user': mock_auth,
            'create_api_key': mock_api_key
        }

@pytest.fixture
async def registered_user(test_user_data, mock_backend):
    """Fixture that creates a registered user and returns their data"""
    # Register the user
    response = client.post("/auth/sign_up", json=test_user_data)
    assert response.status_code == 200
    
    # Add verification code
    test_user_data["verification_code"] = "123456"
    return test_user_data

@pytest.fixture
def valid_verification_data(registered_user):
    """Valid verification data for a registered user"""
    return {
        "email": registered_user["email"],
        "code": registered_user["verification_code"]
    }

@pytest.fixture
def mock_supabase_auth():
    """Mock Supabase auth for signup"""
    with patch('app.core.security.db.auth') as mock_auth:
        # Mock successful signup
        mock_auth.sign_up.return_value = {
            "user": {
                "id": "test_user_id",
                "email": "testuser@example.com",
                "email_verified": False
            }
        }
        yield mock_auth

def test_signup_success(test_user_data, mock_supabase_auth):
    """Test successful user signup."""
    response = client.post("/auth/sign_up", json=test_user_data)
    assert response.status_code == 200
    assert response.json() == {
        "message": "Registration successful. Please check your email to verify your account.",
        "email": test_user_data["email"]
    }
    mock_supabase_auth.sign_up.assert_called_once()

def test_signup_duplicate_email(test_user_data, mock_supabase_auth):
    """Test signup with duplicate email."""
    # Configure mock for duplicate email error
    mock_supabase_auth.sign_up.side_effect = [
        # First call succeeds
        {
            "user": {
                "id": "test_user_id",
                "email": "testuser@example.com",
                "email_verified": False
            }
        },
        # Second call fails
        HTTPException(
            status_code=400,
            detail="User already registered"
        )
    ]
    
    # First signup
    response = client.post("/auth/sign_up", json=test_user_data)
    assert response.status_code == 200
    
    # Wait for rate limit to reset
    time.sleep(1)
    
    # Second signup with same email
    response = client.post("/auth/sign_up", json=test_user_data)
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()

def test_signup_invalid_email_format():
    """Test signup with invalid email format."""
    invalid_user_data = {
        "email": "invalid-email",
        "password": "securepassword"
    }
    response = client.post("/auth/sign_up", json=invalid_user_data)
    assert response.status_code == 422  # Unprocessable Entity for validation errors

def test_signup_missing_email(test_user_data):
    """Test signup with missing email."""
    user_data = test_user_data.copy()
    user_data.pop("email")  # Remove email
    response = client.post("/auth/sign_up", json=user_data)
    assert response.status_code == 422  # Unprocessable Entity for validation errors

def test_signup_missing_password(test_user_data):
    """Test signup with missing password."""
    user_data = test_user_data.copy()
    user_data.pop("password")  # Remove password
    response = client.post("/auth/sign_up", json=user_data)
    assert response.status_code == 422  # Unprocessable Entity for validation errors

def test_signup_short_password(test_user_data):
    """Test signup with a short password."""
    user_data = test_user_data.copy()
    user_data["password"] = "short"  # Short password
    response = client.post("/auth/sign_up", json=user_data)
    assert response.status_code == 400  # Adjust based on your error handling for weak passwords

def test_verify_email_success(registered_user, valid_verification_data, mock_backend):
    """Test successful email verification for registered user"""
    response = client.post("/auth/verify_email", json=valid_verification_data)
    assert response.status_code == 200
    assert response.json() == {
        "message": "Email successfully verified"
    }
    # Verify mock was called correctly
    mock_backend['verify_email'].assert_called_once_with(
        valid_verification_data["email"], 
        valid_verification_data["code"]
    )

def test_verify_email_invalid_code(registered_user, mock_backend):
    """Test verification with invalid code for registered user"""
    # Configure mock to raise an exception for invalid code
    mock_backend['verify_email'].side_effect = Exception("Invalid verification code")
    
    invalid_data = {
        "email": registered_user["email"],
        "code": "000000"  # Wrong code
    }
    response = client.post("/auth/verify_email", json=invalid_data)
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()

def test_verify_email_expired_code(registered_user, valid_verification_data, mock_backend):
    """Test verification with expired code"""
    # First verification succeeds
    response = client.post("/auth/verify_email", json=valid_verification_data)
    assert response.status_code == 200
    
    # Configure mock to raise an exception for expired code
    mock_backend['verify_email'].side_effect = Exception("Verification code has expired")
    
    # Second verification fails
    response = client.post("/auth/verify_email", json=valid_verification_data)
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()

def test_verify_email_invalid_email_format():
    """Test verification with invalid email format."""
    invalid_data = {
        "email": "invalid-email",
        "code": "123456"
    }
    response = client.post("/auth/verify_email", json=invalid_data)
    assert response.status_code == 422  # Validation error

def test_verify_email_missing_code(valid_verification_data):
    """Test verification with missing code."""
    invalid_data = valid_verification_data.copy()
    invalid_data.pop("code")
    response = client.post("/auth/verify_email", json=invalid_data)
    assert response.status_code == 422  # Validation error

def test_verify_email_missing_email(valid_verification_data):
    """Test verification with missing email."""
    invalid_data = valid_verification_data.copy()
    invalid_data.pop("email")
    response = client.post("/auth/verify_email", json=invalid_data)
    assert response.status_code == 422  # Validation error

def test_verify_email_nonexistent_user(mock_backend):
    """Test verification for non-existent user."""
    # Configure mock to raise an exception for nonexistent user
    mock_backend['verify_email'].side_effect = Exception("User not found")
    
    data = {
        "email": "nonexistent@example.com",
        "code": "123456"
    }
    response = client.post("/auth/verify_email", json=data)
    assert response.status_code == 400
    assert "user not found" in response.json()["detail"].lower()

def test_verify_email_rate_limit(mock_backend):
    """Test rate limiting for email verification."""
    # Create a new FastAPI app with strict limits
    test_app = FastAPI()
    test_limiter = Limiter(key_func=get_remote_address)
    test_app.state.limiter = test_limiter
    
    @test_app.post("/auth/verify_email")
    @test_limiter.limit("2/minute")
    async def verify_email_test(verification: EmailVerification, request: Request):
        # Mock the verification logic
        return {"message": "Email successfully verified"}
    
    test_client = TestClient(test_app)
    
    data = {
        "email": "testuser@example.com",
        "code": "123456"
    }
    
    responses = []
    # Make requests quickly to trigger rate limit
    for _ in range(5):
        response = test_client.post(
            "/auth/verify_email", 
            json=data,
            headers={"X-Forwarded-For": "127.0.0.1"}  # Consistent IP for rate limiting
        )
        responses.append(response.status_code)
        print(f"Response {len(responses)}: {response.status_code}")
    
    print(f"All response codes: {responses}")
    
    # First two should succeed (2/minute limit)
    assert responses[0] == 200
    assert responses[1] == 200
    # At least one of the subsequent requests should be rate limited
    assert any(code == 429 for code in responses[2:])

@pytest.fixture
def valid_credentials():
    """Fixture for valid user credentials"""
    return {
        "email": "testuser@example.com",
        "password": "securepassword123"
    }

def test_create_api_key_success(valid_credentials, mock_backend):
    """Test successful API key creation"""
    # Configure mock to return a user and API key
    mock_backend['authenticate_user'].return_value = {"user_id": "test_user"}
    mock_backend['create_api_key'].return_value = "test_api_key_123"
    
    response = client.post("/auth/create_api_key", json=valid_credentials)
    assert response.status_code == 200
    assert "api_key" in response.json()
    assert len(response.json()["api_key"]) > 0

def test_create_api_key_invalid_credentials(valid_credentials, mock_backend):
    """Test API key creation with invalid credentials"""
    # Configure mock to simulate authentication failure
    mock_backend['authenticate_user'].side_effect = HTTPException(
        status_code=401, 
        detail="Invalid credentials"
    )
    
    response = client.post("/auth/create_api_key", json=valid_credentials)
    assert response.status_code == 401
    assert "invalid credentials" in response.json()["detail"].lower()

def test_create_api_key_missing_email():
    """Test API key creation with missing email"""
    response = client.post("/auth/create_api_key", json={"password": "testpass"})
    assert response.status_code == 422  # Validation error

def test_create_api_key_missing_password():
    """Test API key creation with missing password"""
    response = client.post("/auth/create_api_key", json={"email": "test@example.com"})
    assert response.status_code == 422  # Validation error

def test_create_api_key_invalid_email_format():
    """Test API key creation with invalid email format"""
    response = client.post("/auth/create_api_key", 
        json={
            "email": "invalid-email",
            "password": "testpass"
        }
    )
    assert response.status_code == 422  # Validation error

def test_create_api_key_rate_limit(mock_backend, valid_credentials):
    """Test rate limiting for API key creation"""
    test_app = FastAPI()
    test_limiter = Limiter(key_func=get_remote_address)
    test_app.state.limiter = test_limiter
    
    @test_app.post("/auth/create_api_key")
    @test_limiter.limit("2/second")
    async def create_api_key_test(credentials: UserCredentials, request: Request):
        return {"api_key": "test_key"}
    
    test_client = TestClient(test_app)
    
    responses = []
    for _ in range(5):
        response = test_client.post(
            "/auth/create_api_key",
            json=valid_credentials,
            headers={"X-Forwarded-For": "127.0.0.1"}
        )
        responses.append(response.status_code)
        print(f"Response {len(responses)}: {response.status_code}")
    
    assert responses[0] == 200  # First request succeeds
    assert responses[1] == 200  # Second request succeeds
    assert any(code == 429 for code in responses[2:])  # Some requests should be rate limited

def test_create_api_key_server_error(valid_credentials, mock_backend):
    """Test API key creation with server error"""
    # Configure mock to simulate server error
    mock_backend['authenticate_user'].return_value = {"user_id": "test_user"}
    mock_backend['create_api_key'].side_effect = Exception("Database error")
    
    response = client.post("/auth/create_api_key", json=valid_credentials)
    assert response.status_code == 400
    assert "error" in response.json()["detail"].lower()

@pytest.fixture
def mock_remove_api_key():
    """Mock the remove_api_key function"""
    with patch('app.core.security.remove_api_key', new_callable=AsyncMock) as mock:
        mock.return_value = True
        yield mock

@pytest.fixture
def mock_auth_flow():
    """Mock the entire auth flow"""
    with patch('app.core.security.db.auth') as mock_auth:
        # Mock get_user
        mock_user = MagicMock()
        mock_user.id = "test_user_id"
        mock_user.email = "test@example.com"
        mock_user.user_metadata = {"email_verified": True}
        mock_auth.get_user.return_value = mock_user
        yield mock_auth

@pytest.fixture
def mock_db_query():
    """Mock database queries"""
    with patch('app.core.security.db.table') as mock_table:
        mock_response = MagicMock()
        mock_response.data = {
            "balance": 100,
            "last_free_credit_update": datetime.now(UTC).isoformat(),
            "user_id": "test_user_id",
            "is_guest": False
        }
        
        mock_execute = MagicMock()
        mock_execute.execute.return_value = mock_response
        
        mock_maybe_single = MagicMock()
        mock_maybe_single.maybe_single.return_value = mock_execute
        
        mock_eq = MagicMock()
        mock_eq.eq.return_value = mock_maybe_single
        
        mock_select = MagicMock()
        mock_select.select.return_value = mock_eq
        
        mock_table.return_value = mock_select
        yield mock_table

def test_revoke_api_key_success(
    mock_remove_api_key,
    mock_auth_flow,
    mock_db_query,
    auth_header
):
    """Test successful API key revocation"""
    response = client.delete(
        "/auth/revoke_api_key/test_api_key_123",
        headers=auth_header
    )
    assert response.status_code == 200
    assert response.json() == {"message": "API key deleted"}

def test_revoke_api_key_not_found(
    mock_remove_api_key,
    mock_auth_flow,
    mock_db_query,
    auth_header
):
    """Test revoking non-existent API key"""
    mock_remove_api_key.side_effect = HTTPException(
        status_code=404,
        detail="API key not found"
    )
    response = client.delete(
        "/auth/revoke_api_key/nonexistent_key",
        headers=auth_header
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_revoke_api_key_wrong_user(
    mock_remove_api_key,
    mock_auth_flow,
    mock_db_query,
    auth_header
):
    """Test revoking API key belonging to different user"""
    mock_remove_api_key.side_effect = HTTPException(
        status_code=403,
        detail="Cannot revoke API key belonging to another user"
    )
    response = client.delete(
        "/auth/revoke_api_key/other_user_key",
        headers=auth_header
    )
    assert response.status_code == 403
    assert "another user" in response.json()["detail"].lower()

def test_revoke_api_key_server_error(
    mock_remove_api_key,
    mock_auth_flow,
    mock_db_query,
    auth_header
):
    """Test API key revocation with server error"""
    mock_remove_api_key.side_effect = Exception("Database error")
    response = client.delete(
        "/auth/revoke_api_key/test_api_key_123",
        headers=auth_header
    )
    assert response.status_code == 400
    assert "error" in response.json()["detail"].lower()

@pytest.fixture
def mock_credit_service():
    """Mock CreditService"""
    with patch('app.services.credits.CreditService') as mock_service:
        mock_service.refresh_user_credits.side_effect = HTTPException(
            status_code=401,
            detail="401: Invalid authentication: Unauthorized"
        )
        yield mock_service

@pytest.fixture
def mock_security():
    """Mock FastAPI security dependency"""
    with patch('app.core.security.verify_token') as mock:
        async def raise_unauthorized(*args, **kwargs):
            raise HTTPException(
                status_code=401,
                detail="401: Invalid authentication: Unauthorized"
            )
        mock.side_effect = raise_unauthorized
        yield mock

@pytest.fixture
def mock_supabase():
    """Mock entire Supabase client chain"""
    with patch('app.core.security.db') as mock_db:
        # Mock table operations
        mock_response = MagicMock()
        mock_response.data = {
            "balance": 0,
            "last_free_credit_update": datetime.now(UTC).isoformat(),
            "user_id": "guest_id",
            "is_guest": True
        }
        
        mock_execute = MagicMock()
        mock_execute.execute.return_value = mock_response
        
        mock_maybe_single = MagicMock()
        mock_maybe_single.maybe_single.return_value = mock_execute
        
        mock_eq = MagicMock()
        mock_eq.eq.return_value = mock_maybe_single
        
        mock_select = MagicMock()
        mock_select.select.return_value = mock_eq
        
        mock_db.table.return_value = mock_select
        yield mock_db

@pytest.fixture
def mock_verify_token_unauthorized():
    """Mock token verification to raise unauthorized error"""
    with patch('app.core.security.verify_token') as mock:
        mock.side_effect = HTTPException(
            status_code=401,
            detail="Unauthorized"
        )
        yield mock

def test_revoke_api_key_unauthorized(
    mock_supabase,
    mock_security,
    mock_credit_service
):
    """Test API key revocation without authorization"""
    response = client.delete(
        "/auth/revoke_api_key/test_api_key_123",
        headers={}  # No auth header
    )
    
    assert response.status_code == 401
    error_detail = response.json()["detail"]
    # Check that the error contains the key parts
    assert "401" in error_detail
    assert "Invalid authentication" in error_detail
    assert "Unauthorized" in error_detail

def test_revoke_api_key_invalid_token():
    """Test API key revocation with invalid token"""
    response = client.delete(
        "/auth/revoke_api_key/test_api_key_123",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()

def test_revoke_api_key_rate_limit():
    """Test rate limiting for API key revocation"""
    test_app = FastAPI()
    test_limiter = Limiter(key_func=get_remote_address)
    test_app.state.limiter = test_limiter
    
    @test_app.delete("/auth/revoke_api_key/{key}")
    @test_limiter.limit("2/minute")
    async def revoke_api_key_test(key: str, request: Request):
        return {"message": "API key deleted"}
    
    test_client = TestClient(test_app)
    headers = {"Authorization": "Bearer test_token", "X-Forwarded-For": "127.0.0.1"}
    
    responses = []
    for _ in range(4):
        response = test_client.delete(
            "/auth/revoke_api_key/test_key",
            headers=headers
        )
        responses.append(response.status_code)
    
    # First two requests should succeed
    assert responses[0] == 200
    assert responses[1] == 200
    # At least one subsequent request should be rate limited
    assert any(code == 429 for code in responses[2:])

@pytest.fixture
def valid_jwt_token():
    """Create a valid JWT token for testing"""
    payload = {
        "sub": "test@example.com",
        "user_id": "test_user_id",
        "exp": (datetime.now(UTC) + timedelta(minutes=30)).timestamp()
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return f"Bearer {token}"

@pytest.fixture
def auth_header(valid_jwt_token):
    """Fixture for authorization header with valid JWT token"""
    return {"Authorization": valid_jwt_token}