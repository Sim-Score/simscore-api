from bson import ObjectId, InvalidBSON
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
    print("Received a rating update request:", request)
    db = db_client.get_database("SimScore")
    collection = db.get_collection("Sessions")
    
    idea_index = int(request.idea_index)
    user_id = request.user_id
    rating = int(request.rating)
    try:
        session_id = ObjectId(request.session_id)
    except Exception: 
        return JSONResponse(content={"averageRating": rating}, status_code=200)
    
    # Add the new rating
    result = collection.update_one(
        {"_id": session_id, f"ratings.{idea_index}.userRatings.userId": {"$ne": user_id}},
        {"$push": {f"ratings.{idea_index}.userRatings": {"userId": user_id, "rating": rating}}}
    )

    if result.modified_count == 0:
        print(f"Tried to update where User {user_id} already rated idea {idea_index} in session {session_id}. Instead of updating, we will now modify that rating.")
        # If no document was modified, it means the userId already exists, so we update it
        result = collection.update_one(
            {"_id": session_id, f"ratings.{idea_index}.userRatings.userId": user_id},
            {"$set": {f"ratings.{idea_index}.userRatings.$.rating": rating}}
        )


    if result.modified_count > 0:

        # Define the aggregation pipeline
        pipeline = [
            {
                '$match': {'_id': session_id}
            },
            {
                '$project': {
                    'result': {'$arrayElemAt': ['$ratings', idea_index]}
                }
            }
        ]

        # Execute the aggregation
        result = list(collection.aggregate(pipeline))
        print("Pipeline Results: ", result)
        if result:
            user_ratings = result[0]['result']['userRatings']
            average_rating = mean([user_rating['rating'] for user_rating in user_ratings])
            print("Average Rating: ", average_rating)
            return JSONResponse(content={"averageRating": average_rating})
    
    return JSONResponse(content={"error": "Failed to update rating"}, status_code=500)