"""
backend/api/gis.py
-------------------
GIS vector layer API router.
"""

from fastapi import APIRouter, HTTPException
from backend.utils import get_logger
from backend.exceptions import GISException
from backend.services.gis_service import gis_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["GIS Layers"])


@router.get("/roads", summary="Get road network as GeoJSON")
def get_roads() -> dict:
    """Return the road network as a GeoJSON FeatureCollection."""
    try:
        return gis_service.get_roads()
    except GISException as exc:
        logger.error(f"Roads layer error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/buildings", summary="Get building footprints as GeoJSON")
def get_buildings() -> dict:
    """Return building footprints as a GeoJSON FeatureCollection."""
    try:
        return gis_service.get_buildings()
    except GISException as exc:
        logger.error(f"Buildings layer error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/waterways", summary="Get waterways as GeoJSON")
def get_waterways() -> dict:
    """Return waterways (rivers, nullahs) as a GeoJSON FeatureCollection."""
    try:
        return gis_service.get_waterways()
    except GISException as exc:
        logger.error(f"Waterways layer error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
