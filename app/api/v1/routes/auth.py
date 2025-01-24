from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import authenticate_user, create_user, create_api_key, list_api_keys, remove_api_key, verify_token
from app.core.config import settings

# Define the request body model
class UserCredentials(BaseModel):
    email: str
    password: str

router = APIRouter(tags=["auth"])

@router.post("/auth/sign_up")
async def signup(credentials: UserCredentials):
    try:
        await create_user(credentials.email, credentials.password)
        return {
            "message": "Registration successful. Please check your email to verify your account.",
            "email": credentials.email
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/auth/create_api_key")
async def api_key(credentials: UserCredentials):
    try:
        user = await authenticate_user(credentials.email, credentials.password)
        api_key = create_api_key(user)
        return {"api_key": api_key}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/auth/revoke_api_key/{key}")
async def delete_api_key(
    key: str,
    current_user: dict = Depends(verify_token)
):
    try:
        await remove_api_key(current_user, key)
        return {"message": "API key deleted"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/auth/api_keys")
async def api_keys(credentials: UserCredentials):
    """get a list of all active api keys for the user"""
    try:
        user = await authenticate_user(credentials.email, credentials.password)
        print("User successfully authenticated")
        keys = await list_api_keys(user)
        print("Keys: ", keys) # Debug
        return {"api_keys": keys}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))
      
@router.get("/auth/credits")
async def get_credits(current_user: dict = Depends(verify_token)):
    """Get remaining credits for the authenticated user"""
    try:
        credits = current_user["balance"]
        return {"credits": credits}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))
