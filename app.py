import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from app.api.v0.helpers.Analyzer import init_nltk_resources
import app.api.v0.routes as v0 
import app.api.v1.routes as v1

from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()


# Main app for requests at the base url. This will serve documentation etc, but all API endpoints must go to a versioned one.
app = FastAPI(
    title="SimScore API",
    description="API for calculating semantic similarity scores between ideas",
    version="0.1.0",
    contact={
        "name": "SimScore Team",
        "url": "https://simscore.xyz"
    }
)

v0_app = FastAPI(
    title="SimScore API",
    description="API for calculating semantic similarity scores between ideas",
    version="0.1.0",
    contact={
        "name": "SimScore Team",
        "url": "https://simscore.xyz"
    }
)

app.mount("/v0", v0_app)
v0_app.include_router(v0.analyze.router)
v0_app.include_router(v0.session.router)
v0_app.include_router(v0.categorise.router)
v0_app.include_router(v0.validate.router)
v0_app.include_router(v0.star_rating.router)

v1_app = FastAPI(
    title="SimScore API",
    description="API for calculating semantic similarity scores between ideas",
    version="1.0.0",
    contact={
        "name": "SimScore Team",
        "url": "https://simscore.xyz"
    }
)

app.mount("/v1", v1_app)
v1_app.include_router(v1.ideas)

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

@app.get("/")
def index():
    return {"message": "Hello There! To process ideas, send a list of strings to the /process endpoint."}