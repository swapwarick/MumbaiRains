"""
backend/services/gis_service.py
--------------------------------
GISService and GISLayerManager.

GISLayerManager:
    - Loads OSM layers using the GISRepository
    - Caches per-layer GeoJSON to avoid repeated disk reads

GISService:
    - Exposes get_roads(), get_buildings(), get_waterways() to API controllers
    - Delegates all loading to GISLayerManager
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from backend.utils import get_logger
from backend.config import settings
from backend.exceptions import GISException
from backend.database.repositories.gis import GISRepository

logger = get_logger(__name__)


class GISLayerManager:
    """
    Manages and caches GeoJSON vector layers from the GIS data repository.
    """
    def __init__(self, repository: GISRepository) -> None:
        self.repository = repository
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_layer(self, layer_name: str) -> Dict[str, Any]:
        """
        Retrieves a layer from cache, or loads it from repository if not cached.
        """
        if layer_name in self._cache:
            return self._cache[layer_name]

        logger.info("GISLayerManager loading layer", extra={"layer": layer_name})
        geojson = self.repository.load_vector_layer(layer_name)
        
        # Simple structural validation
        if geojson.get("type") != "FeatureCollection":
            raise GISException(f"Layer '{layer_name}' is not a valid FeatureCollection")
            
        self._cache[layer_name] = geojson
        logger.info("Layer cached", extra={"layer": layer_name, "features": len(geojson.get("features", []))})
        return geojson

    def invalidate(self, layer_name: Optional[str] = None) -> None:
        """Invalidates the cache."""
        if layer_name:
            self._cache.pop(layer_name, None)
        else:
            self._cache.clear()
        logger.info("GIS layer cache cleared")


class GISService:
    """
    Application service exposing GeoJSON layer datasets to API controllers.
    """
    def __init__(self, manager: GISLayerManager) -> None:
        self.manager = manager

    def get_roads(self) -> Dict[str, Any]:
        return self.manager.get_layer("roads")

    def get_buildings(self) -> Dict[str, Any]:
        return self.manager.get_layer("buildings")

    def get_waterways(self) -> Dict[str, Any]:
        return self.manager.get_layer("waterways")


# Singletons setup
_gis_repository = GISRepository(settings.gpkg_path)
_layer_manager = GISLayerManager(_gis_repository)
gis_service = GISService(_layer_manager)
