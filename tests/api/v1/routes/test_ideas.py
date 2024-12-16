import pytest
from fastapi.testclient import TestClient
from app.api.v1.routes.ideas import router
from app.api.v1.models.request import IdeaRequest, AdvancedFeatures
from app.api.v1.models.response import AnalysisResponse
from fastapi import FastAPI
from app.core.limiter import limiter
from app.core.settings import settings
import json

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

def test_rank_ideas_invalid_request(valid_token):
    ideas = [{"id": "1", "idea": "Test idea"}]
    response = client.post(
        "/rank-ideas",
        json={"ideas": ideas},
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 400, f"Expected status code 400 but got {response.status_code}: {response}"

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

# def test_generate_edges():
#     from app.api.v1.routes.ideas import _generate_edges
#     ranked_ideas = [
#         {"id": "1", "idea": "First"},
#         {"id": "2", "idea": "Second"}
#     ]
#     results = {
#         "pairwise_similarity": [[1.0, 0.6], [0.6, 1.0]]
#     }
#     edges = _generate_edges(ranked_ideas, results)
#     assert isinstance(edges, list)
#     assert len(edges) == 1
#     assert edges[0]["from_id"] == "1"
#     assert edges[0]["to"] == "2"
#     assert edges[0]["weight"] == 0.6
    
@pytest.mark.parametrize('disable_limiter', [], indirect=True)
def test_rate_limit_enforced():
  client.post(
    "/rank-ideas",
        json={"ideas": mock_ideas},
        headers={"Authorization": f"Bearer {valid_token}"}
  )