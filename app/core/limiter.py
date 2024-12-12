from limits.aio.storage import MemoryStorage
from limits.aio.strategies import FixedWindowRateLimiter

limiter = FixedWindowRateLimiter(storage=MemoryStorage())
