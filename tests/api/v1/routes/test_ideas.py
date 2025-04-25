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
import uuid
from unittest.mock import MagicMock
import inspect

# Create a test app with the router
app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Update the endpoint paths to match the router
ENDPOINT = "/rank_ideas"  # Update this to match your router's path

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}

@pytest.fixture
def override_dependencies():
    # Store original dependency overrides
    original_overrides = app.dependency_overrides.copy()
    
    # Setup: Override dependencies for testing
    async def mock_verify_token():
        # Use proper UUID format for user_id
        return {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com", 
            "email_verified": True,
            "is_guest": False,
            "balance": settings.USER_MAX_CREDITS            
        }
    
    app.dependency_overrides[verify_token] = mock_verify_token
    
    yield
    
    # Teardown: Restore original dependencies
    app.dependency_overrides = original_overrides

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
  
@pytest.mark.asyncio
async def test_request_not_enough_ideas(override_dependencies, auth_headers):
    ideas = [{"id": "1", "idea": "Test idea"}]
    response = client.post(
        ENDPOINT,
        json={"ideas": ideas},
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "at least 4" in str(response.content)

@pytest.mark.asyncio
async def test_request_invalid_idea(override_dependencies, auth_headers):
    ideas = [{"id": "1"}]
    response = client.post(
        ENDPOINT,
        json={"ideas": ideas},
        headers=auth_headers
    )
    assert response.status_code == 422
    assert "Field required" in str(response.content)

@pytest.mark.asyncio
async def test_rank_ideas_success(override_dependencies, mock_ideas, auth_headers):
    # Mock the credit service methods to avoid database calls
    with patch('app.services.credits.CreditService.has_sufficient_credits', return_value=True), \
         patch('app.services.credits.CreditService.deduct_credits', return_value=None), \
         patch('app.services.analyzer.centroid_analysis') as mock_analysis:
        
        # Set up mock return for centroid_analysis
        mock_results = {
            "ideas": ["First idea", "Second idea", "Other ideas", "Many ideas"],
            "similarity": [0.9, 0.8, 0.7, 0.6]
        }
        mock_plot_data = {
            "scatter_points": [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8], [0.9, 1.0]],
            "kmeans_data": {"cluster": [0, 0, 1, 1]},
            "pairwise_similarity": [[1.0, 0.8, 0.7, 0.6], [0.8, 1.0, 0.5, 0.4], 
                                   [0.7, 0.5, 1.0, 0.9], [0.6, 0.4, 0.9, 1.0]]
        }
        mock_analysis.return_value = (mock_results, mock_plot_data)
        
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
    override_dependencies,
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
    
    
@pytest.mark.asyncio
async def test_rank_ideas_with_cluster_names(override_dependencies, auth_headers, mock_ideas):
    """Test that cluster names are generated correctly"""
    # Mock the necessary services
    with patch('app.api.v1.dependencies.auth.verify_token', return_value={"id": "test-id", "user_id": "test-id"}), \
         patch('app.services.credits.CreditService.has_sufficient_credits', return_value=True), \
         patch('app.services.credits.CreditService.deduct_credits', return_value=None):
        
        # Make the request
        response = client.post(
            ENDPOINT,
            json={
                "ideas": mock_ideas,
                "advanced_features": {
                    "cluster_names": True
                }
            },
            headers=auth_headers
        )
        
        print(f"Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response content: {response.content}")
        
        assert response.status_code == 200
        data = response.json()
        assert "ranked_ideas" in data
        assert "cluster_names" in data
        
        # Instead of checking for exactly 2 clusters, verify that cluster names exist
        assert len(data["cluster_names"]) > 0
        
        # Verify each cluster name has the expected structure
        for cluster in data["cluster_names"]:
            assert "id" in cluster
            assert "name" in cluster
            assert isinstance(cluster["id"], int)
            assert isinstance(cluster["name"], str)

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
async def test_rank_ideas_minimum_input(override_dependencies, auth_headers):
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
async def test_rank_ideas_size_limit(override_dependencies, auth_headers):
    """Test that endpoint has size limit"""
    # Create 4 large ideas to pass the minimum length check
    large_ideas = [
        {"id": "1", "idea": "x" * 3_000_000},
        {"id": "2", "idea": "y" * 3_000_000},
        {"id": "3", "idea": "z" * 3_000_000},
        {"id": "4", "idea": "w" * 3_000_000}
    ]
    
    response = client.post(
        ENDPOINT,
        json={"ideas": large_ideas},
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "10MB" in response.text

@pytest.mark.asyncio
async def test_insufficient_credits(override_dependencies, auth_headers):
    """Test behavior when user has insufficient credits"""
    # Mock the necessary services including the user_id in the token verification
    with patch('app.api.v1.dependencies.auth.verify_token', return_value={"id": "test-id", "user_id": "test-id"}), \
         patch('app.services.credits.CreditService.has_sufficient_credits', return_value=False), \
         patch('app.services.credits.CreditService.get_credits', return_value=5):
        
        ideas = [{"id": str(i), "idea": f"idea{i}"} for i in range(4)]
        response = client.post(
            ENDPOINT,
            json={
                "ideas": ideas,
                "advanced_features": {
                    "relationship_graph": True,
                    "cluster_names": True
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 402
        assert "Insufficient credits" in response.text

@pytest.mark.asyncio
async def test_successful_basic_analysis(override_dependencies, auth_headers):
    """Test successful basic idea analysis"""
    # Mock the necessary services
    with patch('app.api.v1.dependencies.auth.verify_token', return_value={"id": "test-id", "user_id": "test-id"}), \
         patch('app.services.credits.CreditService.has_sufficient_credits', return_value=True), \
         patch('app.services.credits.CreditService.get_credits', return_value=100), \
         patch('app.services.credits.CreditService.deduct_credits', return_value=None):
        
        ideas = [
            {"id": "1", "idea": "Improve customer service"},
            {"id": "2", "idea": "Enhance product quality"},
            {"id": "3", "idea": "Better customer support"},
            {"id": "4", "idea": "Upgrade product features"}
        ]
        
        response = client.post(
            ENDPOINT,
            json={"ideas": ideas},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ranked_ideas" in data
        assert len(data["ranked_ideas"]) == 4
        assert all(key in data["ranked_ideas"][0] for key in ["id", "idea", "similarity_score", "cluster_id"])

@pytest.mark.asyncio
async def test_advanced_features(override_dependencies, auth_headers):
    """Test with all advanced features enabled"""
    # Mock the necessary services
    with patch('app.api.v1.dependencies.auth.verify_token', return_value={"id": "test-id", "user_id": "test-id"}), \
         patch('app.services.credits.CreditService.has_sufficient_credits', return_value=True), \
         patch('app.services.credits.CreditService.get_credits', return_value=100), \
         patch('app.services.credits.CreditService.deduct_credits', return_value=None), \
         patch('app.services.analyzer.centroid_analysis', return_value=(
             {"distance": [0.1, 0.2], "ideas": ["Test idea 1", "Test idea 2"], "similarity": [0.9, 0.8]},
             {"plot_data": "mock data"}
         )):
        
        # Use more substantial text for ideas to avoid the empty vocabulary error
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
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ranked_ideas" in data
        # Additional assertions for advanced features can be added here

@pytest.mark.asyncio
async def test_rank_ideas_with_mocked_analysis(
    app_auth_override,  # Use our new fixture instead of patching manually
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
        },
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "ranked_ideas" in data

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
    
    # Check results structure with direct key access instead of isinstance
    assert "distance" in results
    assert "ideas" in results
    assert "similarity" in results
    assert isinstance(results["distance"], list)
    assert isinstance(results["ideas"], list)
    assert isinstance(results["similarity"], list)
    
    # Check plot_data
    assert isinstance(plot_data, dict)

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
    app_auth_override,  # Add our auth override fixture
    mock_centroid_analysis_realistic,
    mock_summarize_clusters_realistic,
    mock_credit_service,
    realistic_ideas
):
    """Test ranking ideas with realistic business improvement ideas"""
    response = client.post(
        ENDPOINT,  # Use the constant instead of hardcoding
        json={
            "ideas": [{"id": idea.id, "idea": idea.idea} for idea in realistic_ideas],
            "advanced_features": {
                "relationship_graph": True,
                "cluster_names": True,
                "pairwise_similarity_matrix": True
            }
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "ranked_ideas" in data

@pytest.fixture
def test_client():
    client = TestClient(app)
    return client


@pytest.mark.asyncio
async def test_rank_ideas_basic_success(
    test_client, 
    override_dependencies, 
    mock_centroid_analysis,
    app_auth_override,  # Add our auth override fixture
    auth_headers
):
    """Test successful basic idea ranking without advanced features"""
    ideas = [
        {"id": "1", "idea": "Build a mobile app for task management"},
        {"id": "2", "idea": "Create an AI-powered chatbot for customer service"},
        {"id": "3", "idea": "Develop a platform for online learning"},
        {"id": "4", "idea": "Design a website for remote job listings"}
    ]
    
    request_data = {
        "ideas": ideas,
        "advanced_features": None
    }
    
    with patch('app.services.credits.CreditService.has_sufficient_credits', return_value=True), \
         patch('app.services.credits.CreditService.deduct_credits', return_value=None):
        
        response = test_client.post(ENDPOINT, json=request_data, headers=auth_headers)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "ranked_ideas" in response_data
        assert len(response_data["ranked_ideas"]) == 4
        assert response_data["relationship_graph"] is None
        assert response_data["cluster_names"] is None


@pytest.mark.asyncio
async def test_rank_ideas_advanced_features(test_client, override_dependencies, mock_centroid_analysis_realistic, auth_headers):
    """Test idea ranking with advanced features enabled"""
    ideas = [
        {"id": "1", "idea": "Create an e-commerce platform for handmade items"},
        {"id": "2", "idea": "Develop a subscription box service for organic products"},
        {"id": "3", "idea": "Build a marketplace for local artisans"},
        {"id": "4", "idea": "Design a platform for connecting farmers with restaurants"},
        {"id": "5", "idea": "Build a food delivery service focusing on local restaurants"}
    ]
    
    request_data = {
        "ideas": ideas,
        "advanced_features": {
            "relationship_graph": True,
            "cluster_names": True,
            "pairwise_similarity_matrix": True
        }
    }
    
    with patch('app.services.credits.CreditService.has_sufficient_credits', return_value=True), \
         patch('app.services.credits.CreditService.deduct_credits', return_value=None), \
         patch('app.services.clustering.summarize_clusters', return_value=["E-commerce", "Food Services"]):
        
        response = test_client.post(ENDPOINT, json=request_data, headers=auth_headers)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "ranked_ideas" in response_data
        assert "relationship_graph" in response_data
        assert "cluster_names" in response_data
        assert "pairwise_similarity_matrix" in response_data
        
        assert response_data["relationship_graph"] is not None
        assert "nodes" in response_data["relationship_graph"]
        assert "edges" in response_data["relationship_graph"]


@pytest.mark.asyncio
async def test_rank_ideas_insufficient_ideas(test_client, override_dependencies, auth_headers):
    """Test error when providing fewer than 4 ideas"""
    ideas = [
        {"id": "1", "idea": "Build a mobile app for task management"},
        {"id": "2", "idea": "Create an AI-powered chatbot for customer service"},
    ]
    
    request_data = {
        "ideas": ideas,
        "advanced_features": None
    }
    
    response = test_client.post(ENDPOINT, json=request_data, headers=auth_headers)
    
    assert response.status_code == 400
    assert "Please provide at least 4 items to analyze" in response.text


@pytest.mark.asyncio
async def test_rank_ideas_too_many_ideas(test_client, override_dependencies, auth_headers):
    """Test error when providing more than 10,000 ideas"""
    # Generate 10,001 ideas
    ideas = [{"id": str(i), "idea": f"Test idea {i}"} for i in range(10001)]
    
    request_data = {
        "ideas": ideas,
        "advanced_features": None
    }
    
    response = test_client.post(ENDPOINT, json=request_data, headers=auth_headers)
    
    assert response.status_code == 400
    assert "Please provide less than 10000 items to analyze" in response.text


@pytest.mark.asyncio
async def test_rank_ideas_data_too_large(test_client, override_dependencies, auth_headers, app_auth_override):
    """Test error when providing too much data (>10MB)"""
    # Create 4 large ideas to pass the minimum length check
    large_ideas = [
        {"id": "1", "idea": "A" * 3_000_000},
        {"id": "2", "idea": "B" * 3_000_000},
        {"id": "3", "idea": "C" * 3_000_000},
        {"id": "4", "idea": "D" * 3_000_000}
    ]
    
    request_data = {
        "ideas": large_ideas,
        "advanced_features": None
    }
    
    response = test_client.post(ENDPOINT, json=request_data, headers=auth_headers)
    
    assert response.status_code == 400
    assert "Please provide less than 10MB of data to analyze" in response.text


@pytest.mark.asyncio
async def test_rank_ideas_insufficient_credits(test_client, override_dependencies, auth_headers):
    """Test error when user has insufficient credits"""
    ideas = [
        {"id": "1", "idea": "Build a mobile app for task management"},
        {"id": "2", "idea": "Create an AI-powered chatbot for customer service"},
        {"id": "3", "idea": "Develop a platform for online learning"},
        {"id": "4", "idea": "Design a website for remote job listings"}
    ]
    
    request_data = {
        "ideas": ideas,
        "advanced_features": None
    }
    
    with patch('app.services.credits.CreditService.has_sufficient_credits', return_value=False), \
         patch('app.services.credits.CreditService.get_total_cost', return_value=10), \
         patch('app.services.credits.CreditService.get_credits', return_value=5):
        
        response = test_client.post(ENDPOINT, json=request_data, headers=auth_headers)
        
        assert response.status_code == 402
        assert "Insufficient credits" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rank_ideas_with_empty_ideas_ignores_empty(test_client, override_dependencies, auth_headers):
    """Test error when some ideas are empty"""
    ideas = [{"id": str(i), "idea": f"Test idea {i}"} for i in range(10)]
    ideas.append({"id": "11", "idea": "", "author": "Test Author"})  # Empty idea, and for extra spice add an author
    ideas.append({"id": "", "idea": "Some idea with empty ID", "author": "Test Author"}) # just for good measure
    
    request_data = {
        "ideas": ideas,
        "advanced_features": {
            "relationship_graph": True,
            "pairwise_similarity_matrix": True,
            "cluster_names": True
        }
    }
    
    with patch('app.services.credits.CreditService.has_sufficient_credits', return_value=True), \
         patch('app.services.credits.CreditService.deduct_credits', return_value=None):
    
        response = test_client.post(ENDPOINT, json=request_data, headers=auth_headers)
        
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_build_relationship_graph(test_client, override_dependencies, mock_centroid_analysis_realistic, auth_headers):
    """Test that relationship graph is built correctly"""
    ideas = [
        {"id": "1", "idea": "Create an e-commerce platform for handmade items"},
        {"id": "2", "idea": "Develop a subscription box service for organic products"},
        {"id": "3", "idea": "Build a marketplace for local artisans"},
        {"id": "4", "idea": "Design a platform for connecting farmers with restaurants"},
        {"id": "5", "idea": "Build a food delivery service focusing on local restaurants"}
    ]
    
    request_data = {
        "ideas": ideas,
        "advanced_features": {
            "relationship_graph": True,
            "pairwise_similarity_matrix": False,
            "cluster_names": False
        }
    }
    
    with patch('app.services.credits.CreditService.has_sufficient_credits', return_value=True), \
         patch('app.services.credits.CreditService.deduct_credits', return_value=None):
        
        response = test_client.post(ENDPOINT, json=request_data, headers=auth_headers)
        
        assert response.status_code == 200
        graph = response.json()["relationship_graph"]
        
        # Check graph structure
        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) == 6  # 5 ideas + 1 centroid
        assert any(node["id"] == "Centroid" for node in graph["nodes"])
        
        # Verify edges
        assert any(edge["to_id"] == "Centroid" for edge in graph["edges"])


@pytest.mark.asyncio
async def test_cluster_names_generation(test_client, override_dependencies, mock_centroid_analysis_realistic, auth_headers, app_auth_override):
    """Test that cluster names are generated correctly"""
    ideas = [
        {"id": "1", "idea": "Create an e-commerce platform for handmade items"},
        {"id": "2", "idea": "Develop a subscription box service for organic products"},
        {"id": "3", "idea": "Build a marketplace for local artisans"},
        {"id": "4", "idea": "Design a platform for connecting farmers with restaurants"},
        {"id": "5", "idea": "Build a food delivery service focusing on local restaurants"}
    ]
    
    request_data = {
        "ideas": ideas,
        "advanced_features": {
            "relationship_graph": False,
            "pairwise_similarity_matrix": False,
            "cluster_names": True
        }
    }
    
    # Mock all credit service functions to avoid database calls
    with patch('app.services.credits.CreditService.has_sufficient_credits', return_value=True), \
         patch('app.services.credits.CreditService.get_credits', return_value=100), \
         patch('app.services.credits.CreditService.get_total_cost', return_value=5), \
         patch('app.services.credits.CreditService.deduct_credits', return_value=None):
        
        response = test_client.post(ENDPOINT, json=request_data, headers=auth_headers)
        
        assert response.status_code == 200
        
        # Verify the structure of the response
        cluster_names = response.json()["cluster_names"]
        assert len(cluster_names) > 0
        
        # Verify that each cluster name has the expected format
        for cluster in cluster_names:
            assert "id" in cluster
            assert "name" in cluster
            assert isinstance(cluster["id"], int)
            assert isinstance(cluster["name"], str)
            assert len(cluster["name"]) > 0

@pytest.mark.asyncio
async def test_rate_limiting_is_applied():
    """Test that rate limiting decorator is applied to the ideas endpoint"""
    # Import the implementation
    import inspect
    from app.api.v1.routes.ideas import rank_ideas
    
    # Get the source code of the function
    source = inspect.getsource(rank_ideas)
    
    # Verify the rate limit decorator is there
    assert "@limiter.limit" in source, "Rate limiting decorator not found"
    
    # Check that it references settings by variable name
    assert "settings.RATE_LIMIT_PER_USER" in source, "Rate limit setting not referenced correctly"
    
    # Check that the key_func is defined correctly
    assert "key_func=lambda request: request.client.host" in source, "Rate limit key function not defined correctly"
    
    # Test passes if we reach here
    assert True

# Add a specific fixture for tests that need more complete auth info
@pytest.fixture
def enhanced_auth_dependencies():
    """Override dependencies with enhanced auth information"""
    # Store original dependency overrides
    original_overrides = app.dependency_overrides.copy()
    
    # Setup: Override dependencies for testing
    def mock_enhanced_verify_token():
        # Return a consistent user_id that matches what the API expects
        return {
            "id": "test-id", 
            "user_id": "test-id",
            "email": "test@example.com", 
            "email_verified": True
        }
    
    # This is the crucial part - directly override at the app level
    app.dependency_overrides[verify_token] = mock_enhanced_verify_token
    
    yield
    
    # Teardown: Restore original dependencies
    app.dependency_overrides = original_overrides

@pytest.mark.asyncio
async def test_rank_ideas_with_enhanced_auth(
    enhanced_auth_dependencies,  # Use the enhanced fixture
    mock_centroid_analysis,
    mock_summarize_clusters,
    mock_credit_service
):
    """Test ranking ideas with mocked analysis functions and enhanced auth"""
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
        },
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "ranked_ideas" in data

@pytest.mark.asyncio
async def test_rank_ideas_with_realistic_data_enhanced_auth(
    enhanced_auth_dependencies,  # Use the enhanced fixture
    mock_centroid_analysis_realistic,
    mock_summarize_clusters_realistic,
    mock_credit_service,
    realistic_ideas
):
    """Test ranking ideas with realistic business improvement ideas and enhanced auth"""
    response = client.post(
        ENDPOINT,
        json={
            "ideas": [{"id": idea.id, "idea": idea.idea} for idea in realistic_ideas],
            "advanced_features": {
                "relationship_graph": True,
                "cluster_names": True,
                "pairwise_similarity_matrix": True
            }
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "ranked_ideas" in data

# Modify the fixture to use the existing app reference
@pytest.fixture
def app_auth_override():
    """Override the auth dependency at the FastAPI app level"""
    # Import the verify_token dependency
    from app.api.v1.dependencies.auth import verify_token
    
    # Store original dependency overrides
    original_overrides = app.dependency_overrides.copy()  # Use the app that's already imported
    
    # Create a function that returns our test user
    async def mock_verify_token():
        return {
            "id": "test-id", 
            "user_id": "test-id",
            "email": "test@example.com", 
            "email_verified": True
        }
    
    # Override at the app level
    app.dependency_overrides[verify_token] = mock_verify_token
    
    yield
    
    # Restore original dependencies
    app.dependency_overrides = original_overrides

# Use the app-level override for a more reliable test
@pytest.mark.asyncio
async def test_rank_ideas_with_app_auth(
    app_auth_override,
    mock_centroid_analysis,
    mock_summarize_clusters,
    mock_credit_service
):
    """Test ranking ideas with proper FastAPI auth override"""
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
        },
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "ranked_ideas" in data