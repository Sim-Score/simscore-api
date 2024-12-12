from pydantic_settings import BaseSettings

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
    
    class Config:
        env_file = ".env"

settings = Settings()
