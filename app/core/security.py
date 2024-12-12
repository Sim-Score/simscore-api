from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Security

from .settings import settings

security = HTTPBearer(auto_error=False) # Authentication is optional!

def create_access_token(data: dict) -> str:
    """Create JWT token for API authentication"""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(datetime.timezone.utc) + expires_delta
    
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    
    return jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm="HS256"
    )

def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> str:
    """Verify JWT token and return user_id"""
    if credentials:
      print('Token credentials: ', credentials)
      try:
          payload = jwt.decode(
              credentials.credentials, 
              settings.SECRET_KEY, 
              algorithms=["HS256"]
          )
          return payload.get("sub")
      except JWTError:
          raise HTTPException(
              status_code=401,
              detail="Invalid authentication credentials"
          )
    return 'anonymous'
