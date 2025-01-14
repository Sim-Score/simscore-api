import pytest
from fastapi.testclient import TestClient
from app.api.v1.routes.ideas import router
from app.api.v1.models.request import IdeaRequest, AdvancedFeatures
from app.api.v1.models.response import AnalysisResponse, RankedIdea
from fastapi import FastAPI
from app.core.limiter import limiter
from app.core.config import settings
import json
from slowapi.errors import RateLimitExceeded

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture
def valid_token():
    return "valid_test_token"

def test_rate_limit_enforced():
  limit = int(settings.RATE_LIMIT_PER_USER.split('/')[0])
  max = limit  + 3
  count = 1
  while count < max:
    print(f"Running request #{count}") 
    response = client.post(
      "/rank-ideas",
      # On purpose submitting an invalid request (needs at least 4 ideas to be valid) so that it returns as fast as possible
      json={"ideas": [{"id": "1", "idea": "Test idea"}]},
    )
    print(f"Response: {response.status_code}")
    assert response.status_code == (400 if count <= limit else 429)
    count += 1
    