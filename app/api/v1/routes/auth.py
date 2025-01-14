from fastapi import APIRouter
import supabase

from app.core.security import authenticate_user, create_user
from app.core.config import settings

router = APIRouter(tags=["auth"])

@router.post("/auth/signup")
async def signup(email: str, password: str):
    token_data = await create_user(email, password)
    return {"access_token": token_data}

@router.post("/auth/login")
async def login(email: str, password: str):
    token_data = await authenticate_user(email, password)
    
    return {"access_token": token_data}
