import sys
from pathlib import Path
import pytest
from typing import List, Tuple, Dict
from jose import jwt
from app.core.db import db
from datetime import datetime, UTC
from app.core.config import settings
import time

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Now we can import from app
from app.api.v1.models.request import IdeaInput
from app.services.types import Results, PlotData, RankedIdea, ClusterName

# Configure pytest-asyncio
def pytest_configure(config):
    config.inicfg['asyncio_mode'] = 'auto'
    config.inicfg['asyncio_default_fixture_loop_scope'] = 'function'

@pytest.fixture
def mock_user_info():
    return {"user_id": "test_user"}

@pytest.fixture
def sample_ideas() -> List[IdeaInput]:
    """Basic set of related business ideas for simple tests"""
    return [
        IdeaInput(id="1", idea="Implement automated customer support system"),
        IdeaInput(id="2", idea="Create customer feedback surveys"),
        IdeaInput(id="3", idea="Develop customer service training program"),
        IdeaInput(id="4", idea="Set up customer complaint tracking system")
    ]

@pytest.fixture
def mock_credit_service(monkeypatch):
    """Mock credit service for testing"""
    class MockCredits:
        data = {"credits": 100}
        
    async def mock_has_sufficient_credits(*args, **kwargs):
        return True
        
    async def mock_deduct_credits(*args, **kwargs):
        return True
        
    async def mock_get_credits(*args, **kwargs):
        return MockCredits()
    
    monkeypatch.setattr("app.services.credits.CreditService.has_sufficient_credits", 
                        mock_has_sufficient_credits)
    monkeypatch.setattr("app.services.credits.CreditService.deduct_credits",
                        mock_deduct_credits)
    monkeypatch.setattr("app.services.credits.CreditService.get_credits",
                        mock_get_credits)

@pytest.fixture
def realistic_ideas() -> List[IdeaInput]:
    """Fixture with realistic business improvement ideas"""
    return [
        IdeaInput(id="1", idea="Implement a customer feedback system to gather real-time insights"),
        IdeaInput(id="2", idea="Create an automated email response system for customer inquiries"),
        IdeaInput(id="3", idea="Develop a mobile app for customer support"),
        IdeaInput(id="4", idea="Set up a customer satisfaction survey program"),
        IdeaInput(id="5", idea="Launch employee training program for better customer service"),
        IdeaInput(id="6", idea="Optimize the website loading speed for better user experience"),
        IdeaInput(id="7", idea="Implement AI chatbot for 24/7 customer support"),
        IdeaInput(id="8", idea="Create a knowledge base for common customer questions")
    ]

@pytest.fixture
def mock_centroid_analysis(monkeypatch):
    """Basic mock for centroid analysis with realistic but simplified data"""
    def mock_analysis(ideas: List[str]) -> Tuple[Results, PlotData]:
        # Simplified but realistic similarity scores
        similarity_scores = [
            0.92,  # Automated support
            0.88,  # Feedback surveys
            0.85,  # Training program
            0.82,  # Complaint tracking
        ]
        
        results = Results(
            ideas=ideas,
            similarity=similarity_scores[:len(ideas)],
            distance=[1 - score for score in similarity_scores[:len(ideas)]]
        )
        
        plot_data = PlotData(
            scatter_points=[
                [0.8, 0.3],   # Automated support
                [-0.7, 0.6],  # Feedback surveys
                [-0.2, -0.8], # Training program
                [-0.5, 0.5],  # Complaint tracking
                [0.0, 0.0]    # Centroid
            ][:len(ideas) + 1],
            marker_sizes=similarity_scores[:len(ideas)],
            ideas=ideas,
            pairwise_similarity=[
                [1.0, 0.75, 0.62, 0.70],  # Automated support similarities
                [0.75, 1.0, 0.58, 0.85],  # Feedback survey similarities
                [0.62, 0.58, 1.0, 0.65],  # Training program similarities
                [0.70, 0.85, 0.65, 1.0]   # Complaint tracking similarities
            ][:len(ideas)],
            kmeans_data={
                "data": [
                    [0.8, 0.3],   # Automated support
                    [-0.7, 0.6],  # Feedback surveys
                    [-0.2, -0.8], # Training program
                    [-0.5, 0.5]   # Complaint tracking
                ][:len(ideas)],
                "centers": [
                    [0.8, 0.3],   # Digital Solutions center
                    [-0.6, 0.5]   # Customer Feedback center
                ],
                "cluster": [0, 1, 1, 1][:len(ideas)]  # Two logical clusters
            }
        )
        
        return results, plot_data
    
    monkeypatch.setattr("app.services.analyzer.centroid_analysis", mock_analysis)

@pytest.fixture
def mock_summarize_clusters(monkeypatch):
    """Basic mock for cluster summarization with test names"""
    async def mock_summarize(ranked_ideas: List[RankedIdea]) -> List[ClusterName]:
        cluster_ids = sorted(set(idea.cluster_id for idea in ranked_ideas))
        return [
            ClusterName(
                id=cluster_id,
                name=f"Test Cluster {cluster_id}"
            )
            for cluster_id in cluster_ids
        ]
    
    monkeypatch.setattr("app.services.clustering.summarize_clusters", mock_summarize)

def _generate_realistic_similarity_matrix(size: int) -> List[List[float]]:
    """Generate a realistic similarity matrix for related business ideas"""
    base_matrix = [
        # Digital Solutions cluster
        [1.0, 0.85, 0.82, 0.45, 0.40, 0.78, 0.80, 0.55],  # Website
        [0.85, 1.0, 0.88, 0.50, 0.45, 0.72, 0.85, 0.60],  # Mobile app
        [0.82, 0.88, 1.0, 0.48, 0.42, 0.70, 0.90, 0.58],  # Chatbot
        # Customer Feedback cluster
        [0.45, 0.50, 0.48, 1.0, 0.92, 0.52, 0.45, 0.65],  # Surveys
        [0.40, 0.45, 0.42, 0.92, 1.0, 0.48, 0.40, 0.62],  # Feedback
        # Support Infrastructure cluster
        [0.78, 0.72, 0.70, 0.52, 0.48, 1.0, 0.75, 0.88],  # Knowledge base
        [0.80, 0.85, 0.90, 0.45, 0.40, 0.75, 1.0, 0.82],  # Training
        [0.55, 0.60, 0.58, 0.65, 0.62, 0.88, 0.82, 1.0]   # Email
    ]
    return [row[:size] for row in base_matrix[:size]]

@pytest.fixture
def test_user():
    """Generate unique test user credentials"""
    timestamp = int(datetime.now(UTC).timestamp())
    return {
        "email": f"test_{timestamp}@example.com",
        "password": "SecureTestPass123!"
    }

@pytest.fixture
def client():
    """Create a test client that connects to the running server"""
    import httpx
    with httpx.Client(base_url="http://localhost:8000", timeout=30.0) as client:
        yield client

@pytest.fixture
def auth_headers(test_user):
    """Fixture for authentication headers"""
    from jose import jwt
    
    # Create a valid JWT token
    token = jwt.encode(
        {
            "user_id": "test_user",
            "email": test_user["email"],
            "is_guest": False,
            "email_verified": True
        },
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_verify_token(monkeypatch):
    """Mock the token verification to return a test user"""
    
    async def mock_verify(request=None, credentials=None):
        # Return a mock user without actually verifying the token
        return {
            "user_id": "test-user-id",
            "email": "test@example.com",
            "email_verified": True,
            "is_guest": False,
            "credits": 100
        }
    
    # Properly monkeypatch the dependency function
    monkeypatch.setattr("app.api.v1.dependencies.auth.verify_token", mock_verify)
    return mock_verify

@pytest.fixture
def mock_centroid_analysis_realistic(monkeypatch):
    """Mock for realistic centroid analysis"""
    def mock_analysis(ideas: List[str]) -> Tuple[Results, PlotData]:
        similarity_scores = [0.95, 0.92, 0.88, 0.85, 0.82, 0.78, 0.75, 0.72]
        
        results = Results(
            ideas=ideas,
            similarity=similarity_scores[:len(ideas)],
            distance=[1 - score for score in similarity_scores[:len(ideas)]]
        )
        
        plot_data = PlotData(
            scatter_points=[[0.1 * i, 0.1 * i] for i in range(len(ideas) + 1)],
            marker_sizes=similarity_scores[:len(ideas)],
            ideas=ideas,
            pairwise_similarity=_generate_realistic_similarity_matrix(len(ideas)),
            kmeans_data={
                "data": [[0.1 * i, 0.1 * i] for i in range(len(ideas))],
                "centers": [[0.2, 0.2], [0.5, 0.5], [0.8, 0.8]],
                "cluster": [i % 3 for i in range(len(ideas))]
            }
        )
        return results, plot_data
    
    monkeypatch.setattr("app.services.analyzer.centroid_analysis", mock_analysis)

@pytest.fixture
def mock_summarize_clusters_realistic(monkeypatch):
    """Mock for realistic cluster summarization"""
    async def mock_summarize(ranked_ideas: List[RankedIdea]) -> List[ClusterName]:
        cluster_names = {
            0: "Digital Solutions",
            1: "Customer Feedback",
            2: "Support Infrastructure"
        }
        cluster_ids = sorted(set(idea.cluster_id for idea in ranked_ideas))
        return [
            ClusterName(
                id=cluster_id,
                name=cluster_names.get(cluster_id, f"Cluster {cluster_id}")
            )
            for cluster_id in cluster_ids
        ]
    
    monkeypatch.setattr("app.services.clustering.summarize_clusters", mock_summarize)

@pytest.fixture
def verified_test_user(test_user):
    """Create a test user that's considered verified"""
    return test_user

@pytest.fixture
def is_local_supabase():
    """Check if we're using local Supabase"""
    return "127.0.0.1" in settings.DATABASE_URL or "localhost" in settings.DATABASE_URL

@pytest.fixture
def is_test_env():
    """Check if we're in test environment with verification disabled"""
    return settings.ENVIRONMENT == "TEST" and settings.SKIP_EMAIL_VERIFICATION

@pytest.fixture(autouse=True)
def disable_limiter():
    """Disable rate limiting during tests"""
    from app.core.limiter import limiter
    limiter.enabled = False
    yield
    limiter.enabled = True

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limits between test sessions"""
    yield
    time.sleep(1)  # Small delay between tests
