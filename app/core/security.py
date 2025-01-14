from datetime import datetime, timedelta
import hashlib
from typing import Optional
from uuid import UUID
from jose import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Request, Security
from .db import db
from .config import settings

security = HTTPBearer(auto_error=False) # Authentication is optional!

async def authenticate_user(email: str, password: str):
    user = db.auth.sign_in({
        "email": email,
        "password": password
    })

    token_data = {
        "user_id": user.id,
        "email": email,
        "is_guest": False
    }
    return create_access_token(token_data)

async def create_user(email: str, password: str):
    user = db.auth.sign_up({
        "email": email,
        "password": password
    })
    
    db.table('credits').insert({
        'user_id': user.id,
        'balance': settings.INITIAL_USER_CREDITS
    }).execute()
    
    token_data = {
        "user_id": user.id,
        "email": email,
        "is_guest": False
    }
    return create_access_token(token_data)

def create_access_token(user_data: dict) -> str:
    """Create JWT token for API authentication"""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(datetime.timezone.utc) + expires_delta
    
    to_encode = user_data.copy()
    to_encode.update({"exp": expire})
    
    return jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm="HS256"
    )

async def verify_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> dict:
    """Verify JWT token and return user info with credits"""          
    try:
        if not credentials:
          user = generate_guest_id(request)
        else:
          user = db.auth.get_user(credentials.credentials)
        user_id = user["id"]
        try:
          credits = db.table('credits').select('balance').eq('user_id', user_id).maybe_single().execute()
        except Exception as e:
          if not credentials: 
            # if the user is not in the credits table, create it with the daily credit amount
            init_guest_data = {
              "user_id": id, 
              "is_guest": True, 
              "balance": settings.GUEST_DAILY_CREDITS
            }
            setup_guest(init_guest_data)
            return init_guest_data
        return {
            "user_id": user_id,
            "is_guest": True if not credentials else False,
            "balance": credits.data['balance']
        } 
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication: {str(e)}")

def setup_guest(data: dict):  
    id = data["user_id"]
    db.auth.admin.create_user({
        'id': id,
        'email': f'guest_{id}@temporary.com',
        'password': 'temporary',  # Or generate random password
    })
    with_expiry = data.copy()
    with_expiry.update({"last_free_credit_reset": datetime.now().isoformat()}) 
    db.table('credits').insert(with_expiry).execute()
    
def generate_guest_id(request: Request) -> dict:
    """Generate consistent guest identifier from IP and user agent"""
    ip = request.client.host
    # Hash the IP to get 32 hex chars
    hex_hash = hashlib.sha256(ip.encode()).hexdigest()[:32]
    return {"id": f"{UUID(hex_hash)}"}
