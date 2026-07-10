"""
backend/data/terrain_repo.py
----------------------------
TerrainRepository handling Copernicus DEM raster loading.
"""

from typing import Dict, Any, Tuple
import numpy as np
import os

from backend.config import settings
from backend.exceptions import TerrainException
from simulation.terrain.loader import load_dem

class TerrainRepository:
    """
    Repository for elevation raster datasets.
    """
    def __init__(self, dem_path: str = "") -> None:
        self.dem_path = dem_path or str(settings.dem_path)

    def load_elevation_grid(self) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Loads the DEM elevation grid and associated raster metadata.
        Raises TerrainException in production if dataset is missing.
        """
        # Production validation check (never silently fallback)
        if getattr(settings, "environment", "development") == "production":
            if not os.path.exists(self.dem_path) or os.path.getsize(self.dem_path) < 1024:
                raise TerrainException(
                    f"Production validation failed: Copernicus DEM file is missing or corrupted at {self.dem_path}"
                )
        
        # Load the raster data
        return load_dem(self.dem_path)
