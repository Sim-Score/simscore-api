from bson import ObjectId
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ..helpers.db import db_client

router = APIRouter()

@router.get("/session/{id}")
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

@router.get("/sessions")
async def retrieve_all_sessions():
    db = db_client.get_database("SimScore")
    collection = db.get_collection("Sessions")
    documents = collection.find({}, {"_id": 1})
    return [str(doc["_id"]) for doc in documents]    

@router.post("/session/{id}")
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

def calculate_consensus(rankings: list[list[str]]):   
    # For simplicity, we use the 'borda count' method,
    # where every idea has a score according to its rank and we simply accumulate the scores.
    # I personally like this method, it seems more consensus based and avoids extremes.
    scores = {}
    for ranking in rankings:
        for position, idea in enumerate(ranking):
            scores[idea] = scores.get(idea, 0) + (len(ranking) - position)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)


@router.get("/manage/{id}")
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