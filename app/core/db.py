from supabase import create_client, Client
from .config import settings

print("Creating Supabase client with url ", settings.DATABASE_URL)

db: Client = create_client(
  settings.DATABASE_URL, 
  settings.DATABASE_SERVICE_ROLE_KEY
)
