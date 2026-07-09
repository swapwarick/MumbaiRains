"""
simulation/terrain/cache.py
---------------------------
TerrainCache — caches computed terrain grids on disk (e.g. slope, aspect,
flow direction/accumulation) to avoid redundant recalculation.
"""

import os
from typing import Optional
import numpy as np

from backend.utils import get_logger
from backend.config import settings

logger = get_logger(__name__)


class TerrainCache:
    """
    Manages caching of intermediate computational grids on the filesystem.
    """
    def __init__(self, cache_dir: Optional[str] = None) -> None:
        # Default cache directory inside data folder
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "cache", "terrain"
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cached_grid(self, key: str, dataset_hash: str) -> Optional[np.ndarray]:
        """
        Retrieves a cached numpy array if it exists.
        """
        filename = f"{key}_{dataset_hash}.npy"
        file_path = os.path.join(self.cache_dir, filename)
        if os.path.exists(file_path):
            try:
                data = np.load(file_path)
                logger.info(f"Loaded cached grid '{key}' from disk", extra={"path": file_path})
                return data
            except Exception as exc:
                logger.warning(f"Failed to load cached grid '{key}': {exc}")
        return None

    def cache_grid(self, key: str, dataset_hash: str, array: np.ndarray) -> None:
        """
        Saves a numpy array to the cache directory.
        """
        filename = f"{key}_{dataset_hash}.npy"
        file_path = os.path.join(self.cache_dir, filename)
        try:
            np.save(file_path, array)
            logger.info(f"Saved grid '{key}' to disk cache", extra={"path": file_path})
        except Exception as exc:
            logger.warning(f"Failed to save grid '{key}' to cache: {exc}")

    def clear(self) -> None:
        """
        Clears all cached grids in the directory.
        """
        try:
            for file in os.listdir(self.cache_dir):
                if file.endswith(".npy"):
                    os.remove(os.path.join(self.cache_dir, file))
            logger.info("TerrainCache cleared successfully.")
        except Exception as exc:
            logger.error(f"Failed to clear TerrainCache: {exc}")
