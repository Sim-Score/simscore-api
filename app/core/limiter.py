# fastlimits:

# from limits.aio.storage import MemoryStorage
# from limits.aio.strategies import FixedWindowRateLimiter

# limiter = FixedWindowRateLimiter(storage=MemoryStorage())


# slowapi:
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

def get_identifier(request):
    """Get unique identifier for rate limiting based on auth status"""
    if "authorization" in request.headers:
        return request.headers["authorization"]
    return get_remote_address(request)

limiter = Limiter(
    key_func=get_identifier,
    default_limits=[settings.RATE_LIMIT_PER_USER],
    strategy="fixed-window",
    storage_uri="memory://"  # Use memory storage for testing
)