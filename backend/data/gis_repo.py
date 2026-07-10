"""
backend/data/gis_repo.py
------------------------
GISRepository loading GIS vector layers (roads, buildings, waterways).
"""

from typing import Dict, Any, List
import os

from backend.config import settings
from backend.exceptions import GISException
from backend.database.repositories.gis import GISRepository as db_GISRepository

class GISRepository:
    """
    Repository layer for GIS vector spatial data.
    """
    def __init__(self, gpkg_path: str = "") -> None:
        self.gpkg_path = gpkg_path or str(settings.gpkg_path)
        self._db_repo = db_GISRepository(self.gpkg_path)

    def load_layer(self, layer_name: str) -> Dict[str, Any]:
        """
        Loads a GIS vector layer from the GeoPackage.
        Raises GISException in production if file is missing.
        """
        # Production validation check (never silently fallback)
        if getattr(settings, "environment", "development") == "production":
            if not os.path.exists(self.gpkg_path) or os.path.getsize(self.gpkg_path) < 100:
                raise GISException(
                    f"Production validation failed: GIS GeoPackage file is missing or empty at {self.gpkg_path}"
                )

        return self._db_repo.load_vector_layer(layer_name)
