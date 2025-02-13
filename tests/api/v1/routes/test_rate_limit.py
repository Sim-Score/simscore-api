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
from app.api.v1.dependencies.auth import verify_token
from tests.conftest import auth_headers, mock_verify_token

app = FastAPI()
app.include_router(router, dependencies=[Depends(verify_token)])
client = TestClient(app)

@pytest.fixture
def valid_token():
    return "valid_test_token"

def test_rate_limit_enforced(mock_verify_token, auth_headers):
    """Test rate limiting with proper authentication"""
    limit = int(settings.RATE_LIMIT_PER_USER.split('/')[0])
    max_requests = limit + 3
    count = 1
    
    while count < max_requests:
        response = client.post(
            "/rank_ideas",
            json={
                "ideas": [
                    {"id": "1", "idea": "Test idea"},
                    {"id": "2", "idea": "Test idea 2"},
                    {"id": "3", "idea": "Test idea 3"},
                    {"id": "4", "idea": "Test idea 4"}
                ]
            },
            headers=auth_headers
        )
        expected_status = 429 if count > limit else 200
        assert response.status_code == expected_status, f"Request {count}: Expected {expected_status}, got {response.status_code}"
        count += 1
    