"""FastAPI router collection."""

from wb_ops.api.routers.assignments import router as assignments_router
from wb_ops.api.routers.dashboard import router as dashboard_router
from wb_ops.api.routers.health import router as health_router
from wb_ops.api.routers.operators import router as operators_router
from wb_ops.api.routers.skus import router as skus_router

__all__ = ["assignments_router", "dashboard_router", "health_router", "operators_router", "skus_router"]
