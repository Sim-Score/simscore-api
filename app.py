import asyncio
import json
import os

from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from Analyzer import CountVectorizer, Analyzer

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from pydantic import BaseModel
from openai import OpenAI


from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

app = FastAPI()

db_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
# Create a new client and connect to the server
db_client = MongoClient(db_uri, server_api=ServerApi('1'))


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

# Send a ping to confirm a successful connection
try:
    db_client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


@app.post("/process")
async def process_item(ideas: list[str]):
    (results, plot_data) = centroid_analysis(ideas)
    print("Analysis results: ", results)
    db = db_client.get_database("SimScore")
    collection = db.get_collection("Sessions")
    document = {
        "results": results,
        "plot_data": plot_data
    }
    id = str(collection.insert_one(document).inserted_id)

    return JSONResponse(content={"id": id, "results": results, "plot_data": plot_data})

@app.get("/session/{id}")
async def retrieve_item(id: str):
    db = db_client.get_database("SimScore")
    collection = db.get_collection("Sessions")
    
    # Convert string id back to ObjectId, that's what MongoDB stores it as
    object_id = ObjectId(id)
    document = collection.find_one({"_id": object_id})
    
    if document:
        document['id'] = str(document.pop('_id'))
        return JSONResponse(content=document)
    else:
        return JSONResponse(content={"error": "Document not found"}, status_code=404)

@app.get("/sessions")
async def retrieve_all_sessions():
    db = db_client.get_database("SimScore")
    collection = db.get_collection("Sessions")
    documents = collection.find({}, {"_id": 1})
    return [str(doc["_id"]) for doc in documents]    

@app.post("/session/{id}")
async def submit_ranking(id: str, data: dict):
    print("Data submitted to submit_ranking: ", data)

    db = db_client.get_database("SimScore")
    collection = db.get_collection("Sessions")
    # Convert string id back to ObjectId
    object_id = ObjectId(id)

    # First, get all reranked ideas, add the new submitted one, calculate a consensus and submit again
    document = collection.find_one({"_id": object_id}, {"reranked_ideas": 1, "_id": 0})    
    if document is None:
        print(f"Document with id {id} not found")
        return None
    
    named_rankings = document.get('reranked_ideas', [])
    rankings = [named_rankings[name] for name in named_rankings]
    ideas = data['ideasAndSimScores']['ideas']
    rankings.append(ideas)
    
    consensus_ranking = calculate_consensus(rankings)

    result = collection.update_one({"_id": object_id}, 
                                   {"$set": {f"reranked_ideas.{data['name']}": ideas,
                                             "consensus_ranking": consensus_ranking}},                                   )
    
    if result.modified_count == 1:
        return JSONResponse(content={"consensus_ranking": consensus_ranking})
    else:
        return JSONResponse(content={"error": "Session not found or not updated"}, status_code=404)

@app.get("/manage/{id}")
async def retrieve_consensus(id: str):
    db = db_client.get_database("SimScore")
    collection = db.get_collection("Sessions")
    
    # Convert string id back to ObjectId, that's what MongoDB stores it as
    object_id = ObjectId(id)
    document = collection.find_one({"_id": object_id}, {"consensus_ranking": 1, "_id": 0})    
    if document:
        return JSONResponse(content=document)
    else:
        return JSONResponse(content={"error": "Document not found / no ranking submitted yet"}, status_code=404)

@app.post("/validate")
async def validate_idea(request: dict):
    print(request)
  
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI()
    client.api_key = api_key

    thread = client.beta.threads.create()
    print("Created thread: ", thread.id)

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=request["idea"],
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id="asst_Y9q7vWLJJUG24uWwnQNznZia",
        instructions="Format your response as JSON object with error: {'singlePointFocusError': string, 'sentimentError': string}",        
        response_format={"type": "json_object"},
    )

    while run.status in ['queued', 'in_progress']:
        print("Waiting for OpenAI to finish processing")
        await asyncio.sleep(0.1)  # Wait for 100ms
    
    if run.status == 'completed':
      result = client.beta.threads.messages.list(
          thread_id=thread.id
      )
      result_json = result.data[0].content[0].text.value
      print("Result: ", result_json)
      return JSONResponse(result_json)

    raise Exception("OpenAI finished with: ", run.status)    


def centroid_analysis(ideas: list):
    # Initialize CountVectorizer to convert text into numerical vectors
    count_vectorizer = CountVectorizer()
    analyzer = Analyzer(ideas, count_vectorizer)
    coords, marker_sizes, kmeans_data = analyzer.process_get_data()

    results = {
        "ideas": analyzer.ideas, 
        "similarity": [x[0] for x in analyzer.cos_similarity.tolist()], 
        "distance": [x[0] for x in analyzer.distance_to_centroid.tolist()]
    }
    plot_data = {
        "scatter_points": coords.tolist(),
        "marker_sizes": marker_sizes.tolist(),
        "ideas": analyzer.ideas,
        "pairwise_similarity": analyzer.pairwise_similarity.tolist(),
        "kmeans_data": kmeans_data
    }
    return (results, plot_data)


def calculate_consensus(rankings: list[list[str]]):   
    # For simplicity, we use the 'borda count' method,
    # where every idea has a score according to its rank and we simply accumulate the scores.
    # I personally like this method, it seems more consensus based and avoids extremes.
    scores = {}
    for ranking in rankings:
        for position, idea in enumerate(ranking):
            scores[idea] = scores.get(idea, 0) + (len(ranking) - position)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

@app.get("/")
def index():
    return {"message": "Hello There! To process ideas, send a list of strings to the /process endpoint."}