"""
backend/schemas/terrain.py
---------------------------
Pydantic response schemas for terrain data.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ArrayStats(BaseModel):
    """Statistical summary of a raster layer."""
    min: float
    max: float
    mean: float
    std: float


class TerrainBounds(BaseModel):
    """Geographic bounding box of the DEM in WGS-84 decimal degrees."""
    west: float
    east: float
    south: float
    north: float


class TerrainMetadata(BaseModel):
    """
    Lightweight terrain summary — no raster arrays.
    Returned by /api/terrain/metadata.
    """
    width: int
    height: int
    crs: str
    transform: List[float] = Field(description="Affine transform [a, b, c, d, e, f]")
    bounds: TerrainBounds
    stats: Dict[str, ArrayStats]


class TerrainGrid(BaseModel):
    """
    Full terrain grid response — all layers as nested lists.
    Returned by /api/terrain (backward-compatible with frontend).
    """
    width: int
    height: int
    crs: str
    transform: List[float]
    elevation: List[List[float]]
    slope: List[List[float]]
    aspect: List[List[float]]
    flow_direction: List[List[int]]
    flow_accumulation: List[List[float]]
