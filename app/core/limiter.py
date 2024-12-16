# fastlimits:

# from limits.aio.storage import MemoryStorage
# from limits.aio.strategies import FixedWindowRateLimiter

# limiter = FixedWindowRateLimiter(storage=MemoryStorage())


# slowapi:
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
  key_func=get_remote_address, 
  default_limits=["1/minute"],
  strategy="fixed-window",
  storage_uri="memory://",  # if we have auto-scaling / multiple servers we'd want to change this to a database
)
