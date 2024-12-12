import random
import string
import os
from pydantic import BaseModel
from typing import Union, List, Tuple, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..helpers.Analyzer import centroid_analysis, Results, CentroidAnalysisResult, PlotData
from ..helpers.db import db_client
from .categorise import summarize_clusters, EvaluatedIdea

router = APIRouter()

class RequestData(BaseModel):
    ideas: Union[List[str], List[Tuple[str, str]]]
    store_results: bool

    model_config = {
        "json_schema_extra" : {
            "example": {
                "ideas": [
                    ["id1", "First idea"],
                    ["id2", "Second idea"]
                ],
                "store_results": True
            }
        }
    }
    
class AnalyzedResponse(BaseModel):
    id: str
    results: Results
    plot_data: PlotData
    summaries: List[str]

    model_config = {
        "json_schema_extra" : {
            "examples": [{
                "id": "temp_ABC123",
                "results": {
                    "ideas": ["idea1", "idea2"],
                    "similarity": [0.8, 0.6],
                    "distance": [0.2, 0.4]
                },
                "plot_data": {"kmeans_data": {"cluster": [0, 1]}},
                "summaries": ["Cluster 1 summary", "Cluster 2 summary"]
            }]
        }
    }


@router.post("/analyze", response_model=AnalyzedResponse)
async def analyze_ideas(request: RequestData) -> AnalyzedResponse:
    """
    Analyze a list of ideas and calculate similarity scores.
    
    The ideas can be provided in two formats:
    - Simple list of strings: ["idea1", "idea2"]
    - List of ID-idea pairs: [["id1", "idea1"], ["id2", "idea2"]]
    
    Returns:
    - Similarity scores for each idea
    - Distance metrics
    - Cluster assignments
    - Plot data points
    """
    ideas = request.ideas
    hasIds = isinstance(ideas[0], list)
    # It's a 2D array
    if hasIds:
      idea_to_id = {idea: id for id, idea in ideas}
      ideas = [idea[1] for idea in ideas]


    res: CentroidAnalysisResult = centroid_analysis(ideas)
    (results, plot_data) = res
    
    if hasIds:
      results["ids"] = [idea_to_id[idea] for idea in results['ideas']]
      
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

    return AnalyzedResponse(
        id=id,
        results=results,
        plot_data=plot_data,
        summaries=summaries
    )

def create_evaluated_ideas(results: Results, plot_data: PlotData):
    evaluated_ideas = []
    for index in range(len(results["ideas"])):
        evaluated_ideas.append(
            EvaluatedIdea(
                id = results["ids"][index] if "ids" in results else None,
                idea=results["ideas"][index],
                similarity=results["similarity"][index],
                distance=results["distance"][index],
                cluster=plot_data["kmeans_data"]["cluster"][index]
            )
        )
    return evaluated_ideas