from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os

def get_db():
    db_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    client = MongoClient(db_uri, server_api=ServerApi('1'))
    return client

db_client = get_db()