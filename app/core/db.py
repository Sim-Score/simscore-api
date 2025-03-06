from supabase import create_client, Client
from .config import settings

db: Client = create_client(
  settings.DATABASE_URL, 
  settings.DATABASE_KEY
)
