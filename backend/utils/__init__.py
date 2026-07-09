"""
backend/utils package
---------------------
General platform utilities: logger and validators.
"""

from .logger import get_logger
from .validation import (
    validate_crs,
    validate_raster_alignment,
    validate_dem_anomalies,
    validate_geojson_geometries,
)

__all__ = [
    "get_logger",
    "validate_crs",
    "validate_raster_alignment",
    "validate_dem_anomalies",
    "validate_geojson_geometries",
]
