from pydantic_settings import SettingsConfigDict, BaseSettings
from typing import Dict, TypedDict

class OperationCost(TypedDict):
    base_cost: int
    per_hundred_items: int
    per_kilobyte: int

class Settings(BaseSettings):
    PROJECT_NAME: str
    
    # List all published versions here. This enables us to manage them better; i.e. gradually phase them out etc...
    API_V1_STR: str
    API_V0_STR: str
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # Rate Limiting
    GLOBAL_RATE_LIMIT: str
    RATE_LIMIT_PER_USER: str
    
    # MongoDB settings if we use it
    MONGODB_URI: str
    
    # OpenAI if used:
    OPENAI_API_KEY: str
    
    # Supabase postgres db settings
    DATABASE_URL: str
    DATABASE_POOLER_URL: str
    DATABASE_KEY: str
    DATABASE_PROJECT_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    OPERATION_COSTS: Dict[str, OperationCost] = {
        "basic_analysis": {
            "base_cost": 1,
            "per_hundred_items": 1,
            "per_kilobyte": 1
        },
        "relationship_graph": {
            "base_cost": 3,
            "per_hundred_items": 2,
            "per_kilobyte": 1
        },
        "cluster_names": {
            "base_cost": 3,
            "per_hundred_items": 1,
            "per_kilobyte": 1
        }
    }
    
    GUEST_DAILY_CREDITS: int
    GUEST_MAX_CREDITS: int
    USER_DAILY_CREDITS: int
    USER_MAX_CREDITS: int
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()