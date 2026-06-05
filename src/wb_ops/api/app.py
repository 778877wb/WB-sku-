"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from wb_ops.api.middleware import PermissionContextMiddleware
from wb_ops.api.routers import assignments_router, dashboard_router, health_router, operators_router, skus_router


def create_app() -> FastAPI:
    """Create and configure the WB Operations API application."""

    app = FastAPI(title="WB Operations Management API", version="0.1.0")
    app.add_middleware(PermissionContextMiddleware)
    app.include_router(health_router)
    app.include_router(skus_router, prefix="/api/v1")
    app.include_router(operators_router, prefix="/api/v1")
    app.include_router(assignments_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    return app


app = create_app()
