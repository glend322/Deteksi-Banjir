from slowapi import Limiter
from slowapi.util import get_remote_address

# Centralized Limiter instance to prevent circular imports between main.py and endpoints
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

