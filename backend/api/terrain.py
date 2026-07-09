"""
backend/api/terrain.py
-----------------------
Terrain API router.

Controllers only:
    1. Validate request parameters (handled by FastAPI/Pydantic automatically)
    2. Call the service
    3. Return the response

No business logic. No direct simulation imports.
"""

from fastapi import APIRouter, HTTPException
from backend.utils import get_logger
from backend.exceptions import TerrainException
from backend.services.terrain_service import terrain_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/terrain", tags=["Terrain"])


@router.get(
    "",
    summary="Get full terrain grid",
    description=(
        "Returns all computed terrain layers (elevation, slope, aspect, "
        "flow direction, flow accumulation) as nested arrays. "
        "Backward-compatible with the MapDashboard.tsx frontend."
    ),
)
def get_terrain_grid() -> dict:
    """Return complete terrain grid — all layers as nested float lists."""
    try:
        return terrain_service.get_full_grid()
    except TerrainException as exc:
        logger.error(f"Terrain grid error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/metadata",
    summary="Get terrain metadata only",
    description="Returns grid dimensions, CRS, bounds, and per-layer statistics. No raster arrays.",
)
def get_terrain_metadata() -> dict:
    """Return lightweight terrain metadata without any raster arrays."""
    try:
        return terrain_service.get_metadata()
    except TerrainException as exc:
        logger.error(f"Terrain metadata error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
