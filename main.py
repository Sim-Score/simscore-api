import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.config import settings

from app.services.analyzer import init_nltk_resources
import app.api.v1.routes as v1

from dotenv import load_dotenv
# Load environment variables from .env file
os.environ.clear()
load_dotenv(override=True)

# Main app for requests at the base url. This will serve documentation etc, but all API endpoints must go to a versioned one.
app = FastAPI(
  title=settings.PROJECT_NAME
)

### V1 ###
v1_app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
)
app.mount("/v1", v1_app)
v1_app.include_router(v1.ideas.router)
### /V1 ###

init_nltk_resources()

ACCESS_CONTROL_ALLOW_CREDENTIALS = os.environ.get(
    'ACCESS_CONTROL_ALLOW_CREDENTIALS', 
    True)
ACCESS_CONTROL_ALLOW_ORIGIN = os.environ.get(
    'ACCESS_CONTROL_ALLOW_ORIGIN', 
    "*").split(",")
ACCESS_CONTROL_ALLOW_METHODS = os.environ.get(
    'ACCESS_CONTROL_ALLOW_METHODS', 
    "GET,OPTIONS,PATCH,DELETE,POST,PUT").split(",")
ACCESS_CONTROL_ALLOW_HEADERS = os.environ.get(
    'ACCESS_CONTROL_ALLOW_HEADERS', 
    "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version").split(",")

app.add_middleware(CORSMiddleware, 
                   allow_origins=ACCESS_CONTROL_ALLOW_ORIGIN,
                   allow_credentials=ACCESS_CONTROL_ALLOW_CREDENTIALS,
                   allow_methods=ACCESS_CONTROL_ALLOW_METHODS,
                   allow_headers=ACCESS_CONTROL_ALLOW_HEADERS
                   )

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
