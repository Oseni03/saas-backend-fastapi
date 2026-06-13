"""
HTTP request/response logging middleware.
Logs method, path, status code, and duration for every request.
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.lib.logger import logger

# Paths to skip logging (health checks would spam logs)
_SKIP_PATHS = {"/api/v1/health", "/api/v1/ready", "/favicon.ico"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log = logger.bind(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        if response.status_code >= 500:
            log.error("http.request")
        elif response.status_code >= 400:
            log.warning("http.request")
        else:
            log.info("http.request")

        return response
