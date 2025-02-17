from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List
import app.core.security as backend

# Request/Response Models
class UserCredentials(BaseModel):
    email: EmailStr  # More strict email validation
    password: str

class SignupResponse(BaseModel):
    message: str
    email: EmailStr

class ApiKeyResponse(BaseModel):
    api_key: str

class ApiKeysResponse(BaseModel):
    api_keys: List[str]

class MessageResponse(BaseModel):
    message: str

class CreditsResponse(BaseModel):
    credits: float

class EmailVerification(BaseModel):
    email: EmailStr
    code: str

router = APIRouter(tags=["auth"])

@router.post("/auth/sign_up", response_model=SignupResponse)
async def signup(credentials: UserCredentials) -> SignupResponse:
    """
    Register a new user account.
    
    Args:
        credentials: User email and password
        
    Returns:
        Registration confirmation message and email
        
    Raises:
        HTTPException: 400 if registration fails
    """
    try:
        await backend.create_user(credentials.email, credentials.password)
        return SignupResponse(
            message="Registration successful. Please check your email to verify your account.",
            email=credentials.email
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))
      
@router.post("/auth/verify_email", response_model=MessageResponse)
async def verify_email(verification: EmailVerification) -> MessageResponse:
    """
    Verify user email with verification code.
    
    Args:
        verification: Email and verification code
        
    Returns:
        Confirmation message
        
    Raises:
        HTTPException: 400 if verification fails
    """
    try:
        await backend.verify_email_code(verification.email, verification.code)
        return MessageResponse(message="Email successfully verified")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/create_api_key", response_model=ApiKeyResponse)
async def create_api_key(credentials: UserCredentials) -> ApiKeyResponse:
    """
    Create a new API key for authenticated user.
    
    Args:
        credentials: User email and password
        
    Returns:
        Newly created API key
        
    Raises:
        HTTPException: 400 if creation fails, 401 if authentication fails
    """
    try:
        user = await backend.authenticate_user(credentials.email, credentials.password)
        api_key = backend.create_api_key(user)
        return ApiKeyResponse(api_key=api_key)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/auth/revoke_api_key/{key}", response_model=MessageResponse)
async def delete_api_key(
    key: str,
    current_user: dict = Depends(backend.verify_token)
) -> MessageResponse:
    """
    Revoke a specific API key.
    
    Args:
        key: API key to revoke
        current_user: Authenticated user information
        
    Returns:
        Confirmation message
        
    Raises:
        HTTPException: 400 if deletion fails, 401 if unauthorized
    """
    try:
        await backend.remove_api_key(current_user, key)
        return MessageResponse(message="API key deleted")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auth/api_keys", response_model=ApiKeysResponse)
async def api_keys(credentials: UserCredentials) -> ApiKeysResponse:
    """
    List all active API keys for the authenticated user.
    
    Args:
        credentials: User email and password
        
    Returns:
        List of active API keys
        
    Raises:
        HTTPException: 400 if listing fails, 401 if authentication fails
    """
    print("Getting API Keys")
    try:
        user = await backend.authenticate_user(credentials.email, credentials.password)
        keys = await backend.list_api_keys(user)
        return ApiKeysResponse(api_keys=keys)
    except Exception as e:
        print(e)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/auth/credits", response_model=CreditsResponse)
async def get_credits(current_user: dict = Depends(backend.verify_token)) -> CreditsResponse:
    """
    Get remaining credits for the authenticated user.
    
    Args:
        current_user: Authenticated user information
        
    Returns:
        Current credit balance
        
    Raises:
        HTTPException: 400 if retrieval fails, 401 if unauthorized
    """
    try:
        credits = current_user["balance"]
        return CreditsResponse(credits=credits)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))
