import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from fastapi import FastAPI

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from routes import analyze, manage, categorise, validate  # Import your route modules

app = FastAPI()
app.include_router(analyze.router)
app.include_router(manage.router)
app.include_router(categorise.router)
app.include_router(validate.router)

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