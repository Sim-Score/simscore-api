import os
import random
import string
from pydantic import BaseModel, Field
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from helpers.Analyzer import centroid_analysis
from helpers.db import db_client


router = APIRouter()

class RequestData(BaseModel):
    ideas: list[str]
    store_results: bool

@router.post("/process")
async def process_item(request: RequestData):
    print("Received a set of ideas, processing...", request)
    ideas = request.ideas
    (results, plot_data) = centroid_analysis(ideas)
    print("Analysis results: ", results)
    if request.store_results:
      print("storing data in the db")
      simscore = db_client.get_database("SimScore")
      collection = simscore.get_collection("Sessions")
      document = {
          "results": results,
          "plot_data": plot_data
      }
      id = str(collection.insert_one(document).inserted_id)
    else:
      print("NOT storing data in the db")
      id = 'temp_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return JSONResponse(content={"id": id, "results": results, "plot_data": plot_data})