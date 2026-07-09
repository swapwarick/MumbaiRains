"""
backend/database/repositories/terrain.py
----------------------------------------
TerrainRepository handles loading raw raster DEM data from files or databases.
Supports full grid loading and windowed reads.
"""

import os
from typing import Tuple, Dict, Any

from backend.config import settings
from backend.utils import get_logger
from simulation.terrain.loader import load_dem

logger = get_logger(__name__)


class TerrainRepository:
    """
    Repository layer for Digital Elevation Model (DEM) and raster layers.
    Abstracts files, database rasters, or caching layers.
    """
    def __init__(self, dem_path: str | os.PathLike) -> None:
        self.path = str(dem_path)

    def load_elevation_grid(self) -> Tuple[Any, Dict[str, Any]]:
        """
        Loads the elevation grid from the configured DEM source.

        Returns:
            A tuple of (elevation_grid as np.ndarray, metadata dict).
        """
        logger.debug("Loading elevation grid from source", extra={"path": self.path})
        return load_dem(self.path)

    def load_window(self, start_row: int, start_col: int, nrows: int, ncols: int) -> Tuple[Any, Dict[str, Any]]:
        """
        Stub for windowed raster reads (e.g. using rasterio block window reading).
        Useful for running simulations on extremely large rasters without loading into memory.
        """
        # Placeholder for Phase 3 large raster window reads
        # For now, falls back to full grid slice.
        grid, meta = self.load_elevation_grid()
        windowed_grid = grid[start_row:start_row + nrows, start_col:start_col + ncols]
        
        windowed_meta = meta.copy()
        windowed_meta["width"] = ncols
        windowed_meta["height"] = nrows
        # Transform adjustments are out of scope for stub
        return windowed_grid, windowed_meta
