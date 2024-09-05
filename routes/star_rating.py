from bson import ObjectId
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from helpers.db import db_client
from statistics import mean

router = APIRouter()

class RatingUpdateRequest(BaseModel):
    session_id: str
    idea_index: int
    user_id: str
    rating: int

@router.post("/update-rating")
async def update_rating(request: RatingUpdateRequest):
    db = db_client.get_database("SimScore")
    collection = db.get_collection("Sessions")
    
    session_id = ObjectId(request.session_id)
    idea_index = int(request.idea_index)
    user_id = request.user_id
    rating = int(request.rating)
    
    # Add the new rating
    result = collection.update_one(
        {"_id": session_id},
        {"$push": {f"ratings.{idea_index}.userRatings": {"userId": user_id, "rating": rating}}}
    )

    if result.modified_count > 0:
        updated_document = collection.find_one(
            {"_id": session_id},
            {f"ratings.{idea_index}.userRatings": 1}
        )
        if updated_document and 'ratings' in updated_document:
            user_ratings = updated_document['ratings'][0]['userRatings']
            average_rating = mean([user_rating['rating'] for user_rating in user_ratings])
            return JSONResponse(content={"average_rating": average_rating})
    
    return JSONResponse(content={"error": "Failed to update rating"}, status_code=500)