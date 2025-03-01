from pydantic_settings import SettingsConfigDict, BaseSettings
from typing import Dict, TypedDict
import os

class OperationCost(TypedDict):
    base_cost: float
    per_hundred_items: float
    per_kilobyte: float

class Settings(BaseSettings):
    PROJECT_NAME: str
    PROJECT_URL: str
    
    # List all published versions here. This enables us to manage them better; i.e. gradually phase them out etc...
    API_V1_STR: str
    
    # Security
    SECRET_KEY: str
    
    # Rate Limiting
    GLOBAL_RATE_LIMIT: str
    RATE_LIMIT_PER_USER: str
    
    # OpenAI if used:
    OPENAI_API_KEY: str
    
    # Supabase postgres db settings
    DATABASE_URL: str
    DATABASE_KEY: str
    
    OPERATION_COSTS: Dict[str, OperationCost] = {
        "basic_analysis": {
            "base_cost": 1,
            "per_hundred_items": 1,
            "per_kilobyte": 0.1
        },
        "relationship_graph": {
            "base_cost": 3,
            "per_hundred_items": 2,
            "per_kilobyte": 0.1
        },
        "cluster_names": {
            "base_cost": 3,
            "per_hundred_items": 1,
            "per_kilobyte": 0.1
        }
    }
    
    GUEST_DAILY_CREDITS: int
    GUEST_MAX_CREDITS: int
    USER_DAILY_CREDITS: int
    USER_MAX_CREDITS: int
    
    # Environment
    ENVIRONMENT: str = "DEV"
    
    # Test Configuration
    SKIP_EMAIL_VERIFICATION: bool = False
    
    TEST_API_TOKEN: str = os.getenv("TEST_API_TOKEN", "test-api-token-for-unit-tests")
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
