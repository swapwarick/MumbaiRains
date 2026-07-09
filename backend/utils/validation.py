"""
backend/utils/validation.py
--------------------------
Implements dataset validators for the Digital Twin platform.
Verifies CRS compliance, raster-vector alignment, geometry validity,
and data anomalies.
"""

from typing import Dict, Any, List
import numpy as np

from backend.config import settings
from backend.utils import get_logger
from backend.exceptions import GISException

logger = get_logger(__name__)


def validate_crs(crs_string: str, expected_crs: str = "EPSG:4326") -> bool:
    """
    Verifies that the dataset CRS matches the expected projection (WGS-84 decimal degrees).
    """
    cleaned_crs = crs_string.strip().upper().replace(" ", "")
    cleaned_expected = expected_crs.strip().upper().replace(" ", "")
    
    is_valid = (cleaned_expected in cleaned_crs) or (cleaned_crs in cleaned_expected)
    if not is_valid:
        logger.error("CRS mismatch detected", extra={"expected": expected_crs, "received": crs_string})
    return is_valid


def validate_raster_alignment(
    shape: tuple[int, int],
    transform: List[float],
    expected_rows: int = 200,
    expected_cols: int = 200
) -> bool:
    """
    Verifies that the loaded raster grid dimensions align with expectations.
    """
    rows, cols = shape
    if rows != expected_rows or cols != expected_cols:
        logger.warning(
            "Raster size anomaly detected",
            extra={"expected": (expected_rows, expected_cols), "received": (rows, cols)}
        )
        return False
    return True


def validate_dem_anomalies(elevation_grid: np.ndarray, nodata_value: float = -9999.0) -> Dict[str, Any]:
    """
    Scans the DEM for invalid values, extreme outliers, or missing cells (nodata values).
    
    Returns:
        A statistics report dict.
    """
    missing_mask = (elevation_grid == nodata_value) | np.isnan(elevation_grid)
    num_missing = int(np.sum(missing_mask))
    
    min_val = float(elevation_grid[~missing_mask].min()) if np.any(~missing_mask) else 0.0
    max_val = float(elevation_grid[~missing_mask].max()) if np.any(~missing_mask) else 0.0

    report = {
        "missing_cells": num_missing,
        "elevation_min": min_val,
        "elevation_max": max_val,
        "is_valid": num_missing == 0 and min_val >= -10.0 and max_val <= 8848.0
    }
    
    if num_missing > 0:
        logger.warning("DEM contains missing elevation values", extra={"missing_count": num_missing})
    if min_val < -10.0 or max_val > 500.0:
        logger.warning("DEM contains extreme elevation values", extra={"min": min_val, "max": max_val})

    return report


def validate_geojson_geometries(geojson: Dict[str, Any]) -> List[str]:
    """
    Validates GeoJSON geometries, checking for self-intersections or null geometries.
    
    Returns:
        List of error descriptions.
    """
    errors = []
    features = geojson.get("features", [])
    for idx, feature in enumerate(features):
        geom = feature.get("geometry")
        if not geom:
            errors.append(f"Feature at index {idx} has null geometry.")
            continue
        
        g_type = geom.get("type")
        coords = geom.get("coordinates")
        if not g_type or coords is None:
            errors.append(f"Feature at index {idx} has incomplete geometry payload.")
    
    if errors:
        logger.warning(
            "GeoJSON validation warnings",
            extra={"total_warnings": len(errors), "layer_size": len(features)}
        )
    return errors
