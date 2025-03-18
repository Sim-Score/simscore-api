from datetime import datetime, timedelta, timezone
import hashlib
import traceback
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
    print("Auth'ing")
    try:
      session = db.auth.sign_in_with_password({
        "email": email,
        "password": password
      })  
    except Exception as e:
      raise HTTPException(status_code=401, detail="This user or password does not exist.")
    
    print("Auth'ed")
    user = session.user
    
    if not user.user_metadata.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Email not verified. Please check your inbox & spam")

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
            'amount': settings.USER_MAX_CREDITS
        }).execute()    
    return user

async def verify_email_code(email: str, code: str):
    try:
        # Regular verification logic
        db.auth.verify_otp({
            "email": email, 
            "token": code, 
            "type": "email",
            "options": { "redirect_to": settings.PROJECT_URL + settings.API_V1_STR + "/docs"}})
        return True
    except Exception as e:
        print(f"Verification error: {str(e)}")
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
  stored_keys = [key["key_id"] for key in db.table('api_keys').select('key_id').eq('user_id', user.id).execute().data]  

  #Reconstruct full API keys
  api_keys = []
  for key_id in stored_keys:
      # Recreate the same user_data used in create_api_key
      user_data = {
          "user_id": user.id,
          "email": user.email,
          "is_guest": False,
          "key_id": str(key_id),
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
        # Skip email verification in test environment
        if settings.ENVIRONMENT == "TEST" and settings.SKIP_EMAIL_VERIFICATION:
            print("Test environment detected - skipping email verification")
            is_guest = not credentials
            if is_guest:
                return generate_guest_id(request)
                
            # Fix: When in test environment, we need to use a safe way to get user_id
            # If we have credentials, try to decode them, otherwise use a test value
            user_id = "test_user"
            if credentials:
                try:
                    decoded = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
                    user_id = decoded.get("user_id", "test_user")
                except:
                    pass
                
            return {
                "user_id": user_id,
                "is_guest": False,
                "email_verified": True,  # Always verified in tests
                "balance": settings.USER_MAX_CREDITS
            }
            
        # Regular verification logic...
        is_guest = not credentials
        if is_guest:
          print("No credentials supplied, continuing as guest...")
          user = generate_guest_id(request)
          user["email_verified"] = True
        else:
          print("Credentials supplied, decoding token: ", credentials)
          decoded = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
          # Check if token is API key
          if decoded.get("token_type") == "api_key":
              print("Got API key, verifying...")
              user = {
                      "id": decoded["user_id"],
                      "email": decoded["email"],
                      "email_verified": True  # API keys are only created for verified users
                  }
              key_id = decoded["key_id"]
              # Verify key hasn't been removed
              results = db.table("api_keys").select('*').eq('key_id', key_id).execute()
              if results.data and results.data[0]:
                key = results.data[0]
              if not key:
                  raise HTTPException(status_code=401, detail="API key not found (it may have been removed)")
          else:
            user = db.auth.get_user(credentials.credentials)
          
        user_id = user["id"]
        if not user["email_verified"]:
          raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox & spam")
        print("getting credits for user:", user_id)
        credits = db.table('credits').select('*').eq('user_id', user_id).maybe_single().execute()
        print("Credits:", credits)
        if not credits.data:            
          print(f"No credits yet for {user_id if credentials else 'anonymous user'}. Creating...")
          if is_guest: # if the guest is not in the credits table, create it with the max credit amount
            init_guest_data = {
              "user_id": user_id, 
              "is_guest": True, 
              "balance": settings.GUEST_MAX_CREDITS
            }
            setup_guest(init_guest_data)
            return init_guest_data
          else:
            # Should we fail here or handle it gracefully? Let's not fail for now.
            print("Error: Existing user doesn't exist in credits table. This really shouldn't be happening... Creating it now.")
            db.rpc('add_credits', {
                'p_user_id': user_id,
                'amount': settings.USER_MAX_CREDITS
            }).execute()  
            
        from app.services.credits import CreditService
        balance = await CreditService.refresh_user_credits(user_id, is_guest, credits)        
        return {
            "user_id": user_id,
            "is_guest": is_guest,
            "balance": balance
        } 
    except Exception as e:
        print("Error: Something went wrong while verifying the token: ", e)
        traceback.print_exc()        
        raise HTTPException(status_code=401, detail=f"Invalid authentication: {str(e)}")

def setup_guest(data: dict):  
    id = data["user_id"]
    db.auth.admin.create_user({
        'id': id,
        'email': f'guest_{id}@temporary.com',
        'password': 'temporary',  # Or generate random password; doesn't matter, does it?
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
