import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("saferoute.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware logging terstruktur untuk setiap request/response (P3.4).
    Log format: METHOD PATH STATUS duration_ms [user_agent]
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            status_code = 500
            logger.error(
                f"UNHANDLED EXCEPTION | {request.method} {request.url.path} | {exc}",
                exc_info=True
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            # Skip logging untuk file statis agar tidak terlalu noisy
            if not request.url.path.startswith("/uploads"):
                logger.info(
                    f"{request.method} {request.url.path} | "
                    f"status={status_code} | {duration_ms}ms | "
                    f"ip={request.client.host if request.client else '-'}"
                )
        return response

