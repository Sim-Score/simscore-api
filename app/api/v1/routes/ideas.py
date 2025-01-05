from fastapi import APIRouter, Depends, Request, Response
from typing import List
import json

from app.core.limiter import limiter
from app.core.settings import settings
from app.services.clustering import summarize_clusters
from ..dependencies.auth import verify_token

from ....services.analyzer import centroid_analysis
from ..models.request import IdeaRequest
from ..models.response import AnalysisResponse, RelationshipGraph
from app.services.types import PlotData, Results, RankedIdea

router = APIRouter(tags=["ideas"])

@router.post("/rank-ideas", response_model=AnalysisResponse)
@limiter.limit(settings.RATE_LIMIT_PER_USER)
async def rank_ideas(
    request: Request,
    ideaRequest: IdeaRequest,
    token: str = Depends(verify_token),   # No effect for now; verification is disabled
) -> AnalysisResponse:
    print('Ranking ideas')
    """
    Analyze and rank ideas based on semantic similarity.
    
    This endpoint processes a list of ideas to:
    - Calculate similarity scores
    - Assign cluster IDs
    - Generate relationship graphs (optional)
    - Create pairwise similarity matrix (optional)
    
    Returns:
        AnalysisResponse containing ranked ideas and optional advanced analysis
    
    Raises:
        HTTPException(400): If input data is invalid
        HTTPException(429): If rate limit is exceeded
    """
        
    # Extract raw ideas for analysis
    ideas = [item.idea for item in ideaRequest.ideas]
    id_mapping = {item.idea: {'id': item.id or 1, 'author_id': item.author_id} for item in ideaRequest.ideas}
    if len(ideas) < 4:
      return Response(status_code=400, content='Please provide at least 4 items to analyze')
    
    # Perform core analysis
    results, plot_data = centroid_analysis(ideas)

    # Create ranked ideas response
    ranked_ideas = [
        RankedIdea(
            id=id_mapping[idea]['id'],
            author_id=id_mapping[idea]['author_id'],
            idea=idea,
            similarity_score=results["similarity"][index],
            cluster_id=plot_data["kmeans_data"]["cluster"][index],
        )
        for index, idea in enumerate(results["ideas"])
    ]
    
    # Sort by similarity score
    ranked_ideas.sort(key=lambda x: x.similarity_score, reverse=True)
    
    # Build response with optional advanced features
    response = {
        "ranked_ideas": ranked_ideas,
        "relationship_graph": None,
        "pairwise_similarity_matrix": None,
        "cluster_names": None
    }
    

    if ideaRequest.advanced_features:
        if ideaRequest.advanced_features.relationship_graph:
            coords = plot_data.get("scatter_points", [])
            nodes = [
                  {
                    "id": idea.id, 
                    "coordinates": {
                      "x": coords[i][0], 
                      "y": coords[i][1]
                    }
                  } 
                  for i, idea in enumerate(ranked_ideas)]
            # Add the centroid:
            nodes.append({"id": "Centroid", "coordinates": {"x": coords[-1][0], "y": coords[-1][0]}})
            response["relationship_graph"] = RelationshipGraph(
                nodes=nodes,
                edges=_generate_edges(ranked_ideas, plot_data.get("pairwise_similarity", []))
            )
            
        if ideaRequest.advanced_features.pairwise_similarity_matrix:
            response["pairwise_similarity_matrix"] = plot_data.get("pairwise_similarity")
            
        if ideaRequest.advanced_features.cluster_names:
            response["cluster_names"] = await summarize_clusters(ranked_ideas)
    print('Results calculated successfully!\n', response)
    return AnalysisResponse(**response)

def _generate_edges(ranked_ideas: List[RankedIdea], similarity_matrix: List) -> List[dict]:
    """Generate graph edges based on similarity scores"""
    edges = []
    
    for i, idea_from in enumerate(ranked_ideas):
      if i+1 > len(similarity_matrix): break
      for j, idea_to in enumerate(ranked_ideas[i+1:], i+1):
          edge = {
                        "from_id": idea_from.id,
                        "to_id": idea_to.id,
                        "similarity": similarity_matrix[i][j]
                    }
          edges.append(edge)
    
    # Add edges to centroid
    for i, idea in enumerate(ranked_ideas):
        edge = {
            "from_id": idea.id,
            "to_id": "Centroid",  # centroid id
            "similarity": idea.similarity_score
        }
        edges.append(edge)
    

    return edges
