import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from app.api.v1.routes.ideas import router
from app.api.v1.models.request import IdeaRequest, AdvancedFeatures
from app.api.v1.models.response import AnalysisResponse, RankedIdea
from app.core.limiter import limiter
from app.core.config import settings
import json
from slowapi.errors import RateLimitExceeded
from unittest.mock import patch
from app.api.v1.dependencies.auth import verify_token
from app.services.types import (
    Results,
    PlotData,
    RankedIdea,
    ClusterName
)

from app.services.clustering import summarize_clusters

# Update the router setup
app = FastAPI()
app.include_router(router, dependencies=[Depends(verify_token)])  # Add dependency
client = TestClient(app)

# Update the endpoint paths to match the router
ENDPOINT = "/rank_ideas"  # Update this to match your router's path

@pytest.fixture
def valid_token():
    return "valid_test_token"

@pytest.fixture
def mock_ideas():
    return [
        {"id": "1", "idea": "First idea"},
        {"id": "2", "idea": "Second idea"},
        {"id": "3", "idea": "Other ideas"},
        {"id": "4", "idea": "Many ideas"}
    ]
        
@pytest.fixture(autouse=True)
def disable_limiter():
    limiter.enabled = False
    yield
    limiter.enabled = True
  
def test_request_not_enough_ideas(mock_verify_token, auth_headers):
    ideas = [{"id": "1", "idea": "Test idea"}]
    response = client.post(
        ENDPOINT,
        json={"ideas": ideas},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "at least 4" in str(response.content)

def test_request_invalid_idea(auth_headers):
    ideas = [{"id": "1"}]
    response = client.post(
        ENDPOINT,
        json={"ideas": ideas},
        headers=auth_headers
    )
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_rank_ideas_success(mock_verify_token, mock_ideas, auth_headers):
    response = client.post(
        ENDPOINT,
        json={"ideas": mock_ideas},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "ranked_ideas" in data
    assert len(data["ranked_ideas"]) == len(mock_ideas)
    assert data["relationship_graph"] is None
    assert data["pairwise_similarity_matrix"] is None

@pytest.mark.asyncio
async def test_rank_ideas_with_advanced_features(
    mock_verify_token,
    mock_credit_service,
    mock_ideas
):
    response = client.post(
        ENDPOINT,
        json={
            "ideas": mock_ideas,
            "advanced_features": {
                "relationship_graph": True,
                "cluster_names": True,
                "pairwise_similarity_matrix": True
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "ranked_ideas" in data
    assert data["relationship_graph"] is not None
    assert data["pairwise_similarity_matrix"] is not None
    assert "nodes" in data["relationship_graph"]
    assert "edges" in data["relationship_graph"]

def test_generate_edges_2x2():
    from app.api.v1.routes.ideas import _generate_edges
    ranked_ideas = [
        RankedIdea(
            id="1", 
            idea="First",
            similarity_score=1.0,
            cluster_id=0,
        ),
        RankedIdea(
            id="2", 
            idea="Second",
            similarity_score=0.8,
            cluster_id=0,
        )
    ]

    matrix = [[1.0, 0.6], [0.6, 1.0]]
    edges = _generate_edges(ranked_ideas, matrix)
    print(edges)
    assert isinstance(edges, list)
    # The [C]entroid is always added as well, so we need one more edge for each idea
    assert len(edges) == 3 # 1-2, 1-C, 2-C
    assert edges[0]["from_id"] == "1"
    assert edges[0]["to_id"] == "2"
    assert edges[0]["similarity"] == 0.6
    
    assert edges[1]["from_id"] == "1"
    assert edges[1]["to_id"] == "Centroid"
    assert edges[1]["similarity"] == 1.0
    
    assert edges[2]["from_id"] == "2"
    assert edges[2]["to_id"] == "Centroid"
    assert edges[2]["similarity"] == 0.8
    

def test_generate_edges_3x3():
    from app.api.v1.routes.ideas import _generate_edges
    ranked_ideas = [
        RankedIdea(
            id="1", 
            idea="First",
            similarity_score=1.0,
            cluster_id=0,
        ),
        RankedIdea(
            id="2", 
            idea="Second",
            similarity_score=0.8,
            cluster_id=0,
        ),
        RankedIdea(
            id="3", 
            idea="Third",
            similarity_score=0.6,
            cluster_id=1,
        )
    ]
    matrix = [[1.0, 0.6, 0.5], [0.6, 1.0, 0.2], [0.5, 0.2, 1.0]]
    edges = _generate_edges(ranked_ideas, matrix)
    assert isinstance(edges, list)
    assert len(edges) == len(ranked_ideas) * 2  # 1->2, 1->3, 2->3 1->C, 2->C, 3->C
    
    assert edges[0]["from_id"] == "1"
    assert edges[0]["to_id"] == "2"
    assert edges[0]["similarity"] == 0.6
    
    assert edges[1]["from_id"] == "1"
    assert edges[1]["to_id"] == "3"
    assert edges[1]["similarity"] == 0.5
    
    assert edges[2]["from_id"] == "2"
    assert edges[2]["to_id"] == "3"
    assert edges[2]["similarity"] == 0.2    
    
    assert edges[3]["from_id"] == "1"
    assert edges[3]["to_id"] == "Centroid"
    assert edges[3]["similarity"] == 1.0
    
    assert edges[4]["from_id"] == "2"
    assert edges[4]["to_id"] == "Centroid"
    assert edges[4]["similarity"] == 0.8
    
    assert edges[5]["from_id"] == "3"
    assert edges[5]["to_id"] == "Centroid"
    assert edges[5]["similarity"] == 0.6
    
    
def test_rank_ideas_with_cluster_names(valid_token, mock_ideas):
    response = client.post(
        ENDPOINT,
        json={
            "ideas": mock_ideas,
            "advanced_features": {
                "cluster_names": True
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "cluster_names" in data
    assert data["cluster_names"] is not None
    assert isinstance(data["cluster_names"], list)
    # Verify cluster name structure
    for cluster in data["cluster_names"]:
        assert "id" in cluster
        assert "name" in cluster


@pytest.mark.asyncio
async def test_summarize_clusters():
    ranked_ideas = [
        RankedIdea(id=1, idea="Mobile app development", similarity_score=0.9, cluster_id=0),
        RankedIdea(id=2, idea="Web application creation", similarity_score=0.8, cluster_id=0),
        RankedIdea(id=3, idea="Data analysis tools", similarity_score=0.7, cluster_id=1),
        RankedIdea(id=4, idea="Machine learning platform", similarity_score=0.6, cluster_id=1),
        RankedIdea(id=5, idea="Cloud infrastructure", similarity_score=0.5, cluster_id=2)
    ]
    
    # Get unique cluster IDs
    unique_clusters = set(idea.cluster_id for idea in ranked_ideas)
    mock_categories = [{"id": cluster_id, "name": f"Cluster {cluster_id} Name"} for cluster_id in unique_clusters]
    
    with patch('app.services.clustering.get_category_names') as mock_get_names:
        mock_get_names.return_value = mock_categories
        cluster_names = await summarize_clusters(ranked_ideas)
        
        assert len(cluster_names) == len(unique_clusters)
        assert all(isinstance(c["id"], int) for c in cluster_names)
        assert all(isinstance(c["name"], str) for c in cluster_names)
        mock_get_names.assert_called_once()

@pytest.mark.asyncio
async def test_rank_ideas_minimum_input(mock_verify_token, auth_headers):
    """Test that endpoint requires at least 4 ideas"""
    response = client.post(
        ENDPOINT,
        json={
            "ideas": [
                {"id": "1", "idea": "idea1"},
                {"id": "2", "idea": "idea2"},
                {"id": "3", "idea": "idea3"}
            ]
        },
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "at least 4" in str(response.content)

@pytest.mark.asyncio
async def test_rank_ideas_max_limit():
    """Test that endpoint has upper limit on ideas"""
    # Create 10001 ideas
    ideas = [{"id": str(i), "idea": f"idea{i}"} for i in range(10001)]
    response = client.post(ENDPOINT, json={"ideas": ideas})
    assert response.status_code == 400
    assert "Please provide less than 10000 items" in response.text

@pytest.mark.asyncio
async def test_rank_ideas_size_limit():
    """Test that endpoint has size limit"""
    large_idea = "x" * 10_000_001  # Over 10MB
    response = client.post(
        ENDPOINT,
        json={
            "ideas": [{"id": "1", "idea": large_idea}]
        }
    )
    assert response.status_code == 400
    assert "Please provide less than 10MB of data" in response.text

@pytest.mark.asyncio
async def test_insufficient_credits():
    """Test behavior when user has insufficient credits"""
    # Mock CreditService to return insufficient credits
    ideas = [{"id": str(i), "idea": f"idea{i}"} for i in range(5)]
    response = client.post(
        ENDPOINT,
        json={
            "ideas": ideas,
            "advanced_features": {
                "relationship_graph": True,
                "cluster_names": True
            }
        }
    )
    assert response.status_code == 402
    assert "Insufficient credits" in response.detail

@pytest.mark.asyncio
async def test_successful_basic_analysis():
    """Test successful basic idea analysis"""
    ideas = [
        {"id": "1", "idea": "Improve customer service"},
        {"id": "2", "idea": "Enhance product quality"},
        {"id": "3", "idea": "Better customer support"},
        {"id": "4", "idea": "Upgrade product features"}
    ]
    
    response = client.post(
        ENDPOINT,
        json={"ideas": ideas}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "ranked_ideas" in data
    assert len(data["ranked_ideas"]) == 4
    assert all(key in data["ranked_ideas"][0] for key in ["id", "idea", "similarity_score", "cluster_id"])

@pytest.mark.asyncio
async def test_advanced_features(mock_verify_token, auth_headers):
    ideas = [{"id": str(i), "idea": f"idea{i}"} for i in range(4)]
    response = client.post(
        ENDPOINT,
        json={
            "ideas": ideas,
            "advanced_features": {
                "relationship_graph": True,
                "cluster_names": True,
                "pairwise_similarity_matrix": True
            }
        },
        headers=auth_headers
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_rank_ideas_with_mocked_analysis(
    mock_centroid_analysis,
    mock_summarize_clusters,
    mock_credit_service
):
    """Test ranking ideas with mocked analysis functions"""
    ideas = [
        {"id": "1", "idea": "Implement automated customer support system"},
        {"id": "2", "idea": "Create customer feedback surveys"},
        {"id": "3", "idea": "Develop customer service training program"},
        {"id": "4", "idea": "Set up customer complaint tracking system"}
    ]
    
    response = client.post(
        ENDPOINT,
        json={
            "ideas": ideas,
            "advanced_features": {
                "relationship_graph": True,
                "cluster_names": True,
                "pairwise_similarity_matrix": True
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check basic analysis results
    assert len(data["ranked_ideas"]) == 4
    assert data["ranked_ideas"][0]["similarity_score"] == 0.92  # Highest mock score
    
    # Check cluster names
    assert data["cluster_names"] is not None
    assert len(data["cluster_names"]) == 2
    cluster_names = {c["name"] for c in data["cluster_names"]}
    assert "Automation Solutions" in cluster_names
    assert "Customer Feedback & Training" in cluster_names
    
    # Check relationship graph
    assert data["relationship_graph"] is not None
    assert len(data["relationship_graph"]["nodes"]) == 5  # 4 ideas + 1 centroid
    
    # Check pairwise similarity matrix
    assert data["pairwise_similarity_matrix"] is not None
    assert len(data["pairwise_similarity_matrix"]) == 4
    # Verify that automated support has high similarity with complaint tracking
    assert data["pairwise_similarity_matrix"][0][3] >= 0.7

@pytest.mark.asyncio
async def test_centroid_analysis_mock(mock_centroid_analysis):
    """Test that centroid analysis mock returns expected structure"""
    from app.services.analyzer import centroid_analysis
    
    test_ideas = [
        "Implement automated customer support system",
        "Create customer feedback surveys",
        "Develop customer service training program",
        "Set up customer complaint tracking system"
    ]
    results, plot_data = centroid_analysis(test_ideas)
    
    # Check results structure
    assert isinstance(results, Results)
    assert len(results.similarity) == len(test_ideas)
    assert results.similarity[0] == 0.92  # Highest similarity for automated support
    
    # Check plot data structure
    assert isinstance(plot_data, PlotData)
    assert len(plot_data.scatter_points) == len(test_ideas) + 1  # +1 for centroid
    assert len(plot_data.kmeans_data["cluster"]) == len(test_ideas)
    assert len(plot_data.pairwise_similarity) == len(test_ideas)
    # Verify that feedback surveys and complaint tracking have high similarity
    assert plot_data.pairwise_similarity[1][3] >= 0.85

@pytest.mark.asyncio
async def test_summarize_clusters_mock(mock_summarize_clusters):
    """Test that cluster summarization mock returns expected structure"""
    from app.services.clustering import summarize_clusters
    from app.services.types import RankedIdea
    
    test_ideas = [
        RankedIdea(id="1", idea="idea1", similarity_score=0.9, cluster_id=0),
        RankedIdea(id="2", idea="idea2", similarity_score=0.8, cluster_id=0),
        RankedIdea(id="3", idea="idea3", similarity_score=0.7, cluster_id=1),
        RankedIdea(id="4", idea="idea4", similarity_score=0.6, cluster_id=1)
    ]
    
    cluster_names = await summarize_clusters(test_ideas)
    
    # Check cluster names structure
    assert len(cluster_names) == 2  # Should have 2 unique clusters
    assert all(isinstance(cluster, ClusterName) for cluster in cluster_names)
    assert cluster_names[0].id == 0
    assert cluster_names[1].id == 1
    assert cluster_names[0].name == "Test Cluster 0"
    assert cluster_names[1].name == "Test Cluster 1"

@pytest.mark.asyncio
async def test_rank_ideas_with_realistic_data(
    mock_centroid_analysis_realistic,
    mock_summarize_clusters_realistic,
    mock_credit_service,
    realistic_ideas
):
    """Test ranking ideas with realistic business improvement ideas"""
    response = client.post(
        ENDPOINT,
        json={
            "ideas": [{"id": idea.id, "idea": idea.idea} for idea in realistic_ideas],
            "advanced_features": {
                "relationship_graph": True,
                "cluster_names": True,
                "pairwise_similarity_matrix": True
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check basic analysis results
    assert len(data["ranked_ideas"]) == len(realistic_ideas)
    assert data["ranked_ideas"][0]["similarity_score"] == 0.95  # Highest score
    
    # Verify cluster names are meaningful
    assert data["cluster_names"] is not None
    cluster_names = {c["name"] for c in data["cluster_names"]}
    assert "Digital Solutions" in cluster_names
    assert "Customer Feedback" in cluster_names
    assert "Support Infrastructure" in cluster_names
    
    # Check relationship graph structure
    graph = data["relationship_graph"]
    assert len(graph["nodes"]) == len(realistic_ideas) + 1  # +1 for centroid
    
    # Verify ideas are clustered logically
    digital_solutions = [idea for idea in data["ranked_ideas"] 
                        if idea["cluster_id"] == 0]
    assert any("website" in idea["idea"].lower() for idea in digital_solutions)
    assert any("mobile app" in idea["idea"].lower() for idea in digital_solutions)
    assert any("chatbot" in idea["idea"].lower() for idea in digital_solutions)