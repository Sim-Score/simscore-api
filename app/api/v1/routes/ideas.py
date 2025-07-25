from fastapi import APIRouter, Depends, HTTPException, Request, Response
from typing import List
import json

from app.core.limiter import limiter
from app.core.config import settings
from app.services.clustering import summarize_clusters
from app.services.credits import CreditService
from ..dependencies.auth import verify_token

from ....services.analyzer import centroid_analysis
from ....services.analyzer import Analyzer
from ..models.request import IdeaInput, IdeaRequest
from ..models.response import AnalysisResponse, RelationshipGraph
from app.services.types import PlotData, Results, RankedIdea

router = APIRouter(tags=["ideas"])

@router.post("/rank_ideas", response_model=AnalysisResponse)
@limiter.limit(
    settings.RATE_LIMIT_PER_USER,
    key_func=lambda request: request.client.host if request.client else "global"
)
async def rank_ideas(
    request: Request,
    ideaRequest: IdeaRequest,
    user_info: dict = Depends(verify_token),
) -> AnalysisResponse | Response:
    """
    Analyze and rank ideas based on semantic similarity.
    
    This endpoint processes a list of ideas to:
    - Calculate similarity scores
    - Assign cluster IDs
    - Generate relationship graphs (optional)
    - Create pairwise similarity matrix (optional)
    
    Credits required:
    - Basic analysis: 1 credit per 100 ideas
    - Relationship graph: 3 credits
    - Cluster names: 5 credits
    
    Returns:
        AnalysisResponse containing ranked ideas and optional advanced analysis
    
    Raises:
        HTTPException(400): If input data is invalid
        HTTPException(402): If insufficient credits
        HTTPException(429): If rate limit is exceeded
    """
    print('Ranking ideas')
    
    # Filter out empty ideas from the original request
    filtered_idea_inputs = [item for item in ideaRequest.ideas if item.idea.strip()]
        
    # Extract ideas from filtered inputs
    ideas = [item.idea for item in filtered_idea_inputs]
    num_ideas = len(ideas)
    total_bytes = sum(len(idea.encode('utf-8')) for idea in ideas)

    if num_ideas < 4:
        return Response(status_code=400, content='Please provide at least 4 items to analyze')

    if num_ideas > 10_000:
        return Response(status_code=400, content='Please provide less than 10000 items to analyze')

    if total_bytes > 10_000_000:
        return Response(status_code=400, content='Please provide less than 10MB of data to analyze')

    is_valid, message = Analyzer.check_ideas_are_sentences(ideas, 80)
    if not is_valid:
        return Response(status_code=400, content=message)


    # Check credits for basic analysis
    user_id = user_info["user_id"]
    
    operations = ["basic_analysis"]
    
    if ideaRequest.advanced_features:
        if ideaRequest.advanced_features.relationship_graph:
            operations.append("relationship_graph")
        if ideaRequest.advanced_features.cluster_names:
            operations.append("cluster_names")

    if not await CreditService.has_sufficient_credits(
        user_id, operations, num_ideas, total_bytes
    ):
        required = await CreditService.get_total_cost(operations, num_ideas, total_bytes)
        available = await CreditService.get_credits(user_id)
        print(f"Insufficient credits. Required: {required}; Available: {available}")
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits for analysis. Required credits: {required}; Available credits: {available}"
        )
    
    # Perform core analysis
    print('Starting analysis for ideas: \n', ideaRequest)
    results, plot_data = centroid_analysis(ideas)
    await CreditService.deduct_credits(user_id, "basic_analysis", num_ideas, total_bytes)

    response = await build_base_response(ideas, results, plot_data, ideaRequest.ideas)

    if ideaRequest.advanced_features:
        response = await process_advanced_features(
            ideaRequest, response, user_id, ideas, plot_data, num_ideas, total_bytes
        )

    results = AnalysisResponse(**response)
    
    print('Results calculated successfully!')
    if results.ranked_ideas:
        print('First 5 ranked ideas:', results.ranked_ideas[:5])
    if results.pairwise_similarity_matrix:
        print('First 5 similarity scores:', results.pairwise_similarity_matrix[:5])
    if results.cluster_names:
        print('First 5 cluster names:', results.cluster_names[:5])
    if results.relationship_graph:
        print('First 5 graph nodes & edges:', results.relationship_graph.nodes[:5], results.relationship_graph.edges[:5])    
    
    return results

def _generate_edges(ranked_ideas: List[RankedIdea], similarity_matrix: List[List[float]]) -> List[dict]:
    """
    Generate graph edges showing relationships between ideas and to centroid.
    
    Creates two types of edges:
    1. Between ideas based on pairwise similarity
    2. From each idea to the centroid based on similarity scores
    """
    edges = []
    
    # Create edges between ideas
    for i, idea_from in enumerate(ranked_ideas):
        if i+1 > len(similarity_matrix): 
            break
        for j, idea_to in enumerate(ranked_ideas[i+1:], i+1):
            edges.append({
                "from_id": idea_from.id,
                "to_id": idea_to.id,
                "similarity": similarity_matrix[i][j]
            })
    
    # Create edges to centroid
    for idea in ranked_ideas:
        edges.append({
            "from_id": idea.id,
            "to_id": "Centroid",
            "similarity": idea.similarity_score
        })
    
    return edges

async def build_base_response(ideas: List[str], results: Results, plot_data: PlotData, idea_inputs: List[IdeaInput]) -> dict:
    """Build base response with ranked ideas and similarity scores"""
    # Create lookup dict from idea string to original input
    idea_to_input = {input.idea: input for input in idea_inputs}
    
    ranked_ideas = [
        RankedIdea(
            id=str(idea_to_input[idea].id) if idea_to_input[idea].id is not None else str(index),
            idea=idea,
            author_id=str(idea_to_input[idea].author_id) if idea_to_input[idea].author_id is not None else '',
            similarity_score=results["similarity"][index],
            cluster_id=plot_data["kmeans_data"]["cluster"][index],
        )
        for index, idea in enumerate(results["ideas"])
    ]
    
    ranked_ideas.sort(key=lambda x: x.similarity_score, reverse=True)
    
    return {
        "ranked_ideas": ranked_ideas,
        "relationship_graph": None,
        "pairwise_similarity_matrix": None,
        "cluster_names": None
    }

async def process_advanced_features(
    request: IdeaRequest,
    response: dict,
    user_id: str,
    ideas: List[str],
    plot_data: PlotData,
    num_ideas: int,
    total_bytes: int
) -> dict:
    """Process and add advanced features if credits are available"""
    if request.advanced_features and request.advanced_features.relationship_graph:
        response["relationship_graph"] = build_relationship_graph(
            response["ranked_ideas"], plot_data
        )
        await CreditService.deduct_credits(user_id, "relationship_graph", num_ideas, total_bytes)
    
    if request.advanced_features and request.advanced_features.cluster_names:
        response["cluster_names"] = await summarize_clusters(response["ranked_ideas"])
        await CreditService.deduct_credits(user_id, "cluster_names", num_ideas, total_bytes)
           
    if request.advanced_features and request.advanced_features.pairwise_similarity_matrix:
        response["pairwise_similarity_matrix"] = plot_data["pairwise_similarity"]
        
    return response

def build_relationship_graph(ranked_ideas: List[RankedIdea], plot_data: PlotData) -> RelationshipGraph:
    """
    Builds a graph representation of idea relationships including:
    - Nodes with coordinates from MDS analysis
    - Edges showing similarity between ideas
    - Centroid connections
    """
    coords = plot_data["scatter_points"]
    
    # Create nodes including centroid
    nodes = [
        {
            "id": idea.id,
            "coordinates": {
                "x": coords[i][0],
                "y": coords[i][1]
            }
        }
        for i, idea in enumerate(ranked_ideas)
    ]
    nodes.append({
        "id": "Centroid",
        "coordinates": {
            "x": coords[-1][0],
            "y": coords[-1][1]
        }
    })
    
    # Generate edges between ideas and to centroid
    edges = _generate_edges(ranked_ideas, plot_data["pairwise_similarity"])
    
    return RelationshipGraph(nodes=nodes, edges=edges)
