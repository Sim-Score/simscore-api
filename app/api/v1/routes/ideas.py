from fastapi import APIRouter, Depends
from typing import List

from ..models.request import IdeaRequest
from ..models.response import AnalysisResponse, RankedIdea, RelationshipGraph
from ..dependencies.auth import verify_token
from ....services.analyzer import centroid_analysis

router = APIRouter(tags=["ideas"])

def filter_something() -> bool:
    print('Filter applied!')
    return True

@router.post("/rank-ideas", response_model=AnalysisResponse)
async def rank_ideas(
    ideaRequest: IdeaRequest,
    token: str = Depends(verify_token),
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
    id_mapping = {item.idea: item.id for item in ideaRequest.ideas}
    
    # Perform core analysis
    results, plot_data = centroid_analysis(ideas)
    
    # Create ranked ideas response
    ranked_ideas = [
        RankedIdea(
            id=id_mapping[idea],
            idea=idea,
            similarity_score=results["similarity"][idx],
            cluster_id=plot_data["kmeans_data"]["cluster"][idx]
        )
        for idx, idea in enumerate(results["ideas"])
    ]
    
    # Sort by similarity score
    ranked_ideas.sort(key=lambda x: x.similarity_score, reverse=True)
    
    # Build response with optional advanced features
    response = {
        "ranked_ideas": ranked_ideas,
        "relationship_graph": None,
        "pairwise_similarity_matrix": None
    }
    
    if ideaRequest.advanced_features:
        if ideaRequest.advanced_features.relationship_graph:
            response["relationship_graph"] = RelationshipGraph(
                nodes=[{"id": idea.id, "label": idea.idea} for idea in ranked_ideas],
                edges=_generate_edges(ranked_ideas, results)
            )
            
        if ideaRequest.advanced_features.pairwise_similarity_matrix:
            response["pairwise_similarity_matrix"] = results.get("pairwise_similarity")
    print('Results calculated successfully! ', response)
    return AnalysisResponse(**response)

def _generate_edges(ranked_ideas: List[RankedIdea], results: dict) -> List[dict]:
    """Generate graph edges based on similarity scores"""
    edges = []
    similarity_matrix = results.get("pairwise_similarity", [])
    
    for i, idea1 in enumerate(ranked_ideas):
        for j, idea2 in enumerate(ranked_ideas[i+1:], i+1):
            if similarity_matrix[i][j] > 0.5:  # Configurable threshold
                edges.append({
                    "from_id": idea1.id,
                    "to": idea2.id,
                    "weight": similarity_matrix[i][j]
                })
    
    return edges
