import random
import string
from pydantic import BaseModel
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from helpers.Analyzer import centroid_analysis, Results, CentroidAnalysisResult, PlotData
from helpers.db import db_client
from routes.categorise import summarize_clusters, EvaluatedIdea

router = APIRouter()

class RequestData(BaseModel):
    ideas: list[str]
    store_results: bool

@router.post("/process")
async def process_item(request: RequestData):
    print("Received a set of ideas, processing...", request)
    ideas = request.ideas
    res: CentroidAnalysisResult = centroid_analysis(ideas)
    (results, plot_data) = res
    print("Analysis results: ", results)
    
    # Directly calculate the cluster summaries so we don't do it from the frontend whenever the ID page is loaded. (That would result in different titles on each reload 😢)
    evaluated_ideas = create_evaluated_ideas(results, plot_data)
    summaries = await summarize_clusters(evaluated_ideas)
    
    if request.store_results:
      print("storing data in the db")
      simscore = db_client.get_database("SimScore")
      collection = simscore.get_collection("Sessions")
      document = {
          "results": results,
          "plot_data": plot_data,
          "summaries": summaries,
          "ratings": [{"userRatings": []} for _ in range(len(ideas))]
      }
      
      id = str(collection.insert_one(document).inserted_id)
    else:
      print("NOT storing data in the db")
      id = 'temp_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

    return JSONResponse(content={"id": id, "results": results, "plot_data": plot_data, "summaries": summaries})

def create_evaluated_ideas(results: Results, plot_data: PlotData):
    evaluated_ideas = []
    for index in range(len(results["ideas"])):
        evaluated_ideas.append(
            EvaluatedIdea(
                idea=results["ideas"][index],
                similarity=results["similarity"][index],
                distance=results["distance"][index],
                cluster=plot_data["kmeans_data"]["cluster"][index]
            )
        )
    return evaluated_ideas