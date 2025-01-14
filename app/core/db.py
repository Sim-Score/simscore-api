from supabase import create_client, Client
from .config import settings

db: Client = create_client(
  settings.DATABASE_PROJECT_URL, 
  settings.SUPABASE_SERVICE_ROLE_KEY
  )
