# Testing Guide

This guide describes how to run tests for SimScore API.

## Test Structure

```
tests/
├── api/
│   └── v1/
│       └── routes/
│           └── test_ideas.py      # Tests for idea ranking API
├── integration/
│   ├── test_auth_basic.py        # Basic auth flow tests
│   ├── test_auth_guest.py        # Guest user tests
│   └── test_auth_verified.py     # Verified user tests
└── conftest.py                   # Shared test fixtures
```

## Environment Setup

1. Create or update `.env` file with test configuration:

```env
# Test Environment
ENVIRONMENT="DEV"
SKIP_EMAIL_VERIFICATION="true"  # Required for running auth tests
TEST_USER_EMAIL="test@simscore.dev"
TEST_USER_PASSWORD="TestPass123!"

# Database (Local Supabase)
DATABASE_URL="http://127.0.0.1:54321"
DATABASE_KEY="your-service-role-key"

# Rate Limiting
RATE_LIMIT_PER_USER="20/minute"
GUEST_DAILY_CREDITS=10
GUEST_MAX_CREDITS=100
USER_DAILY_CREDITS=100
USER_MAX_CREDITS=1000
```

## Running Tests

### Authentication Tests

1. Basic Auth (`test_auth_basic.py`):
```bash
poetry run pytest tests/integration/test_auth_basic.py -v -s
```
Tests:
- User signup
- Rate limiting (5 requests/minute)
- Input validation

2. Verified Users (`test_auth_verified.py`):
```bash
poetry run pytest tests/integration/test_auth_verified.py -v -s
```
Tests:
- API key creation/management
- Email verification flow
- Credit system

3. Guest Users (`test_auth_guest.py`):
```bash
poetry run pytest tests/integration/test_auth_guest.py -v -s
```
Tests:
- Guest access
- Guest credit limits

### Ideas API Tests (`test_ideas.py`)

```bash
poetry run pytest tests/api/v1/routes/test_ideas.py -v -s
```

Tests:
- Basic idea ranking
- Cluster analysis
- Advanced features:
  - Relationship graphs
  - Cluster naming
  - Similarity matrices
- Input validation:
  - Minimum 4 ideas
  - Maximum 10,000 ideas
  - Size limits (10MB)
- Credit management
- Rate limiting

## Test Categories (Markers)

Run tests by category using pytest markers:

```bash
# Auth tests
poetry run pytest -m verified
poetry run pytest -m guest
poetry run pytest -m integration

# Rate limiting tests
poetry run pytest -m rate_limited

# Async tests
poetry run pytest -m asyncio
```

## Available Test Fixtures

From `conftest.py`:

### Auth Fixtures
- `client`: HTTP test client
- `test_user`: Test user credentials from env
- `auth_headers`: Pre-configured auth headers
- `is_test_env`: Environment checker
- `verified_test_user`: Pre-verified test user

### Ideas API Fixtures
- `mock_ideas`: Sample test ideas
- `realistic_ideas`: Realistic business ideas
- `mock_credit_service`: Mocked credit system
- `mock_centroid_analysis`: Basic analysis mock
- `mock_centroid_analysis_realistic`: Realistic analysis mock
- `mock_summarize_clusters`: Cluster naming mock

## Common Issues & Solutions

### Rate Limiting
If tests fail with 429 status:
```bash
# Option 1: Wait for rate limit reset
sleep 60

# Option 2: Increase limit in .env
RATE_LIMIT_PER_USER="100/minute"

# Option 3: Disable rate limiting in tests
@pytest.fixture(autouse=True)
def disable_limiter():
    limiter.enabled = False
    yield
    limiter.enabled = True
```

### Email Verification
For verified user tests:
```bash
# Ensure in .env:
SKIP_EMAIL_VERIFICATION="true"
```

### Database Connection
If database tests fail:
```bash
# Check Supabase status
supabase status

# Ensure correct DATABASE_URL in .env
DATABASE_URL="http://127.0.0.1:54321"
```

## Writing New Tests

### Auth Test Example
```python
@pytest.mark.integration
def test_new_auth_feature(client, test_user):
    """Test description"""
    response = client.post("/v1/auth/endpoint", json=test_user)
    assert response.status_code == 200
```

### Ideas API Test Example
```python
@pytest.mark.asyncio
async def test_idea_analysis(mock_credit_service, mock_ideas):
    """Test idea analysis with mocked services"""
    response = client.post(
        "/v1/rank_ideas",
        json={
            "ideas": mock_ideas,
            "advanced_features": {
                "relationship_graph": True
            }
        }
    )
    assert response.status_code == 200
    assert "ranked_ideas" in response.json()
```