import pytest
from fastapi.testclient import TestClient
from app.api.v1.routes.ideas import router
from app.api.v1.models.request import IdeaRequest, AdvancedFeatures
from app.api.v1.models.response import AnalysisResponse, RankedIdea
from fastapi import FastAPI
from app.core.limiter import limiter
from app.core.settings import settings
import json
from slowapi.errors import RateLimitExceeded

app = FastAPI()
app.include_router(router)
client = TestClient(app)

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

def test_request_not_enough_ideas(valid_token):
    ideas = [{"id": "1", "idea": "Test idea"}]  # Some missing fields
    response = client.post(
        "/rank-ideas",
        json={"ideas": ideas},
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 400, f"Expected status code 400 but got {response.status_code}: {response}"
    assert "at least 4" in str(response.content)  

def test_request_invalid_idea(valid_token):
    ideas = [
      {"id": "1"}
    ]  
    response = client.post(
        "/rank-ideas",
        json={"ideas": ideas},
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 422
    error_detail = response.json()
    print(error_detail)
    assert "detail" in error_detail
    assert "idea" in str(error_detail["detail"])

def test_rank_ideas_success(valid_token, mock_ideas):
    response = client.post(
        "/rank-ideas",
        json={
            "ideas": mock_ideas,
        },
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "ranked_ideas" in data
    assert len(data["ranked_ideas"]) == len(mock_ideas)
    assert data["relationship_graph"] is None
    assert data["pairwise_similarity_matrix"] is None

def test_rank_ideas_with_advanced_features(valid_token, mock_ideas):
    response = client.post(
        "/rank-ideas",
        json={
            "ideas": mock_ideas,
            "advanced_features": {
                "relationship_graph": True,
                "pairwise_similarity_matrix": True
            }
        },
        headers={"Authorization": f"Bearer {valid_token}"}
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
    assert isinstance(edges, list)
    assert len(edges) == 1
    assert edges[0]["from_id"] == "1"
    assert edges[0]["to_id"] == "2"
    assert edges[0]["similarity"] == 0.6

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
    assert len(edges) == 3  # 1->2, 1->3, 2->3
    
    assert edges[0]["from_id"] == "1"
    assert edges[0]["to_id"] == "2"
    assert edges[0]["similarity"] == 0.6
    
    assert edges[1]["from_id"] == "1"
    assert edges[1]["to_id"] == "3"
    assert edges[1]["similarity"] == 0.5
    
    assert edges[2]["from_id"] == "2"
    assert edges[2]["to_id"] == "3"
    assert edges[2]["similarity"] == 0.2    