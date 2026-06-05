"""Permission middleware foundation for FastAPI."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class PermissionContextMiddleware(BaseHTTPMiddleware):
    """Attach lightweight permission context to request state.

    This is intentionally non-blocking in Phase 8. It centralizes where future
    permission checks can read authenticated operator context from headers,
    tokens, or sessions.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request.state.operator_id = request.headers.get("X-Operator-Id")
        request.state.permission = request.headers.get("X-Permission")
        return await call_next(request)
