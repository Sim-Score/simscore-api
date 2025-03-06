# Testing Guide for SimScore API

## Overview

This guide describes the testing approach for SimScore API, covering test organization, setup instructions, and common testing scenarios.

## Test Organization

```
tests/
├── api/                   # API endpoint tests
│   └── v1/
│       └── routes/
│           ├── test_ideas.py      # Idea ranking endpoint tests
│           ├── test_auth.py       # Authentication endpoint tests
│           └── test_rate_limit.py # Rate limiting tests
├── integration/           # End-to-end flows
│   ├── test_auth_basic.py        # Basic authentication flows
│   ├── test_auth_guest.py        # Guest user flows
│   └── test_auth_verified.py     # Verified user flows
└── conftest.py            # Shared test fixtures
```

## Test Environment Setup

1. Create a `.env` file with test configuration:

```
# Environment
ENVIRONMENT=TEST

# API Configuration
RATE_LIMIT_PER_USER=20/minute
GLOBAL_RATE_LIMIT=1000/minute

# Test Settings
SKIP_EMAIL_VERIFICATION=true
TEST_API_TOKEN=<your-test-token>

# Database (Local Supabase)
DATABASE_URL=http://127.0.0.1:54321
DATABASE_KEY=<your-supabase-service-role-key>

# Credits Configuration
GUEST_DAILY_CREDITS=10
GUEST_MAX_CREDITS=100
USER_DAILY_CREDITS=100
USER_MAX_CREDITS=1000
```

2. Start the API server in development mode:

```bash
poetry run uvicorn app.main:app --reload
```

3. Ensure Supabase is running locally:

```bash
supabase start
```

## Running Tests

### API Endpoint Tests

```bash
# Run all API tests
poetry run pytest tests/api/

# Run specific API tests
poetry run pytest tests/api/v1/routes/test_ideas.py
poetry run pytest tests/api/v1/routes/test_auth.py
poetry run pytest tests/api/v1/routes/test_rate_limit.py
```

### Integration Tests

```bash
# Run all integration tests
poetry run pytest tests/integration/

# Run specific integration flows
poetry run pytest tests/integration/test_auth_basic.py
poetry run pytest tests/integration/test_auth_guest.py
poetry run pytest tests/integration/test_auth_verified.py
```

### Running Tests by Marker

```bash
# Auth-related tests
poetry run pytest -m verified
poetry run pytest -m guest
poetry run pytest -m integration

# Rate limiting tests
poetry run pytest -m rate_limited
```

## Test Categories

### Ideas API Tests

Tests the idea ranking endpoint functionality:

- Input validation (minimum/maximum ideas, size limits)
- Cluster analysis and visualization
- Advanced features (relationship graphs, cluster naming)
- Credit system integration
- Error handling

### Authentication Tests

Tests user management and authentication:

- User registration and login
- Email verification
- API key creation and management
- Rate limiting on auth endpoints
- User credits and quotas

### Rate Limiting Tests

Verifies API protection against abuse:

- Request limiting based on IP address
- Appropriate rate limit configuration
- 429 response handling

## Key Test Fixtures

The `conftest.py` file provides shared fixtures:

- `client`: HTTP client for API requests
- `test_user`: Dynamically generated test credentials
- `auth_headers`: Pre-authenticated request headers
- `mock_ideas`: Sample idea data for testing
- `mock_credit_service`: Credit system bypass
- `disable_limiter`: Disables rate limiting during tests

## Troubleshooting

### Rate Limit Errors

If tests fail with 429 status codes:

```bash
# Option 1: Wait for rate limit reset
sleep 60

# Option 2: Run with disabled rate limiting
DISABLE_RATE_LIMITS=true poetry run pytest
```

### Database Connection Issues

If tests fail to connect to Supabase:

```bash
# Check if Supabase is running
supabase status

# Restart Supabase if needed
supabase stop
supabase start
```

### Authentication Failures

For auth test failures:

```bash
# Ensure email verification is disabled for tests
SKIP_EMAIL_VERIFICATION=true

# Use a pre-configured test token
TEST_API_TOKEN=<valid-test-token>
```

## CI/CD Integration

Tests run automatically on:
- Pull requests to main branch
- Nightly builds

The CI pipeline runs tests in a containerized environment with:
- Isolated test database
- Test-specific rate limits
- Email verification disabled
