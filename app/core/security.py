from datetime import datetime, timedelta, timezone
import hashlib
from typing import Optional
from uuid import UUID, uuid4
from jose import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, Request, Security
from .db import db
from .config import settings

security = HTTPBearer(auto_error=False) # Authentication is optional!

async def create_user(email: str, password: str):
    db.auth.sign_up({
        "email": email,
        "password": password
    })
    
async def authenticate_user(email: str, password: str):
    session = db.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    user = session.user
    if not user.user_metadata["email_verified"]:
        raise HTTPException(status_code=401, detail="Email not verified. Please check your inpox & spam")

    print("User authenticated:", user)
    user_id = user.id
    print("User ID:", user_id)
    # Check if user has credits entry
    credits = db.table('credits').select('*').eq('user_id', user.id).execute()
    print("User credits:", credits.data)
    if not credits.data:
        # Create initial credits entry if none exists
        db.rpc('add_credits', {
            'p_user_id': user_id,
            'amount': settings.USER_DAILY_CREDITS
        }).execute()    
    return user

async def verify_email_code(email: str, code: str):
    try:
        # Verify the code against stored verification code
        db.auth.verify_otp({"email": email, "token": code, "type": "email"})
        return True
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
def create_api_key(user) -> str:
    """Create JWT token for API authentication"""
  
    key_id = str(uuid4())

    user_data = {
        "user_id": user.id,
        "email": user.email,
        "is_guest": False,
        "key_id": key_id,
        "token_type": "api_key"
    }
    
    api_key = jwt.encode(
        user_data, 
        settings.SECRET_KEY, 
        algorithm="HS256"
    )
    
    # Store API key metadata in database
    db.table('api_keys').insert({
        'key_id': key_id,
        'user_id': user.id,
        'created_at': datetime.now(timezone.utc).isoformat()
    }).execute()
    
    return api_key

async def remove_api_key(user, key):
  decoded = jwt.decode(key, settings.SECRET_KEY, algorithms=["HS256"])
  key_id = decoded["key_id"]
  db.table('api_keys').delete().eq('key_id', key_id).eq('user_id', user["user_id"]).execute()

async def list_api_keys(user):
  stored_keys = db.table('api_keys').select('*').eq('user_id', user.id).execute().data
  
  #Reconstruct full API keys
  api_keys = []
  for key_meta in stored_keys:
      # Recreate the same user_data used in create_api_key
      user_data = {
          "user_id": user.id,
          "email": user.email,
          "is_guest": False,
          "key_id": str(key_meta['key_id']),
          "token_type": "api_key"
      }
      
      # Encode with same algorithm to reconstruct the original key
      encoded_key = jwt.encode(
          user_data,
          settings.SECRET_KEY,
          algorithm="HS256"
      )
      
      # Add both metadata and full key
      api_keys.append(encoded_key)
  
  return api_keys

async def verify_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> dict:
    """Verify JWT token and return user info with credits"""          
    try:
        if not credentials:
          print("No credentials supplied, continuing as guest...")
          user = generate_guest_id(request)
          user["email_verified"] = True
        else:
          decoded = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
            
          # Check if token is API key
          if decoded.get("token_type") == "api_key":
              print("Got API key, verifying...")
              user = {
                      "id": decoded["user_id"],
                      "email": decoded["email"],
                      "email_verified": True  # API keys are only created for verified users
                  }
              print("User data:", user)
              key_id = decoded["key_id"]
              print("Key: ", key_id)
              # Verify key hasn't been removed
              results = db.table("api_keys").select('*').eq('key_id', key_id).execute()
              print("Query results:", results)
              if results.data and results.data[0]:
                key = results.data[0]
                print("Key data:", key)
              if not key:
                  raise HTTPException(status_code=401, detail="API key not found (it may have been removed)")
          else:
            user = db.auth.get_user(credentials.credentials)
          
        user_id = user["id"]
        if not user["email_verified"]:
          raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox & spam")
        try:
          print("getting credits for user:", user_id)
          query = db.table('credits').select('balance').eq('user_id', user_id)
          credits = query.maybe_single().execute()
        except Exception as e:
          print('Exception getting credits:', str(e))
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
    with_expiry.update({"last_free_credit_update": datetime.now().isoformat()}) 
    db.table('credits').insert(with_expiry).execute()
    
def generate_guest_id(request: Request) -> dict:
    """Generate consistent guest identifier from IP and user agent"""
    ip = request.client.host
    # Hash the IP to get 32 hex chars
    hex_hash = hashlib.sha256(ip.encode()).hexdigest()[:32]
    return {"id": f"{UUID(hex_hash)}"}
