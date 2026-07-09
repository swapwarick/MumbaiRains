"""
backend/services/terrain_service.py
-------------------------------------
TerrainService — service layer wrapping TerrainEngine and TerrainRepository.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from backend.utils import get_logger
from backend.config import settings
from backend.exceptions import TerrainException
from backend.database.repositories.terrain import TerrainRepository
from simulation.terrain.engine import TerrainEngine

logger = get_logger(__name__)


class TerrainService:
    """
    Application service managing DEM loading and derived topographic layers.
    Caches processed engine results in memory to avoid repeated calculations.
    """
    def __init__(self, repository: TerrainRepository) -> None:
        self.repository = repository
        self.engine: Optional[TerrainEngine] = None

    def _get_engine(self) -> TerrainEngine:
        """Returns the loaded TerrainEngine, creating it if necessary."""
        if self.engine is None:
            logger.info("TerrainService loading DEM from repository")
            try:
                # Load DEM array and meta from repository
                elevation, meta = self.repository.load_elevation_grid()
                
                # Construct TerrainEngine around it
                self.engine = TerrainEngine(
                    _elevation=elevation,
                    _meta=meta
                )
            except Exception as exc:
                raise TerrainException(f"TerrainService failed to initialize terrain products: {exc}") from exc
        return self.engine

    def get_metadata(self) -> Dict[str, Any]:
        return self._get_engine().metadata

    def get_full_grid(self) -> Dict[str, Any]:
        return self._get_engine().full_grid()

    def invalidate_cache(self) -> None:
        self.engine = None
        logger.info("TerrainService cache invalidated")


# Singletons setup
_terrain_repository = TerrainRepository(settings.dem_path)
terrain_service = TerrainService(_terrain_repository)
