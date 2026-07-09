"""
simulation/terrain/loader.py
----------------------------
Responsible for loading DEM files. Supports loading real GeoTIFF rasters,
predefined synthetic benchmark datasets, and fallback synthetic topographic DEMs.
"""

import os
from typing import Dict, Any, Tuple, Optional
import numpy as np

from backend.utils import get_logger
from backend.config import settings
from backend.exceptions import TerrainException

logger = get_logger(__name__)

try:
    import rasterio
    _RASTERIO = True
except ImportError:
    _RASTERIO = False
    logger.warning("rasterio not installed — using synthetic Mumbai DEM fallback")


class TerrainLoader:
    """
    Handles loading of elevation grids from disk, including synthetic test surfaces.
    """
    def __init__(self, golden_dir: Optional[str] = None) -> None:
        self.golden_dir = golden_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "benchmarks", "golden"
        )

    def load_raster(self, path_or_name: str) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Loads an elevation raster. If a predefined benchmark name is passed,
        loads the corresponding golden synthetic grid from disk.
        """
        name_lower = path_or_name.lower().strip()
        benchmarks = ["flat_surface", "uniform_slope", "single_hill", "single_valley", "synthetic_watershed"]
        
        # Check if loading a synthetic benchmark
        for bench in benchmarks:
            if bench in name_lower:
                bench_path = os.path.join(self.golden_dir, f"{bench}.npz")
                if os.path.exists(bench_path):
                    try:
                        archive = np.load(bench_path)
                        elev = archive["elevation"].astype(np.float32)
                        rows, cols = elev.shape
                        meta = {
                            "driver": "GTiff",
                            "dtype": "float32",
                            "nodata": -9999.0,
                            "width": cols,
                            "height": rows,
                            "count": 1,
                            "crs": settings.default_crs,
                            "transform": [10.0, 0.0, 0.0, 0.0, -10.0, float(rows) * 10.0],
                        }
                        logger.info(f"Loaded synthetic benchmark dataset: {bench}", extra={"shape": elev.shape})
                        return elev, meta
                    except Exception as exc:
                        raise TerrainException(f"Failed to load synthetic benchmark {bench}: {exc}")
                        
        # Fallback to standard loader
        return load_dem(path_or_name)


def load_dem(dem_path: str | os.PathLike) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Load a DEM GeoTIFF and return (elevation_array, metadata).

    Falls back to a synthetic Greater Mumbai DEM when:
    - rasterio is not installed
    - the file does not exist
    - the file is a stub (< 1 KB)
    """
    path = str(dem_path)
    use_fallback = (
        not _RASTERIO
        or not os.path.exists(path)
        or os.path.getsize(path) < 1024
    )

    if use_fallback:
        logger.info("Loading synthetic Mumbai DEM fallback")
        return _build_synthetic_dem()

    try:
        with rasterio.open(path) as src:
            elevation = src.read(1).astype(np.float32)
            t = src.transform
            transform_coeff = [t.a, t.b, t.c, t.d, t.e, t.f]
            meta: Dict[str, Any] = {
                "driver": src.driver,
                "dtype": "float32",
                "nodata": src.nodata,
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "crs": str(src.crs),
                "transform": transform_coeff,
            }
        logger.info(
            "DEM loaded from disk",
            extra={"path": path, "shape": elevation.shape},
        )
        return elevation, meta
    except Exception as exc:
        raise TerrainException(f"Failed to read DEM from {path}: {exc}") from exc


def _build_synthetic_dem() -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Generates a physically plausible 200×200 elevation grid covering the
    entire Greater Mumbai Peninsula.
    """
    s = settings

    cols, rows = s.dem_fallback_cols, s.dem_fallback_rows
    lon_w, lat_n = s.dem_fallback_lon_west, s.dem_fallback_lat_north
    lon_e, lat_s = s.dem_fallback_lon_east, s.dem_fallback_lat_south

    lon_res = (lon_e - lon_w) / cols   # ~0.00095° ≈ 105 m
    lat_res = (lat_n - lat_s) / rows   # ~0.00190° ≈ 210 m

    x = np.linspace(0, 1, cols)
    y = np.linspace(0, 1, rows)
    X, Y = np.meshgrid(x, y[::-1])  # row 0 = north (lat_n)

    base        = X * 30.0 + 2.0
    sgnp_hills  = 65.0 * np.exp(-((X - 0.75)**2 / 0.04  + (Y - 0.85)**2 / 0.06))
    aarey       = 30.0 * np.exp(-((X - 0.65)**2 / 0.025 + (Y - 0.55)**2 / 0.03))
    powai       = -8.0 * np.exp(-((X - 0.70)**2 / 0.008 + (Y - 0.42)**2 / 0.008))
    river_dist  = (X - 0.30) - (Y - 0.50) * 0.8
    mithi       = -6.0 * np.exp(-(river_dist**2) / 0.006)
    dharavi     = -4.0 * np.exp(-((X - 0.30)**2 / 0.015 + (Y - 0.15)**2 / 0.015))

    rng = np.random.default_rng(seed=42)
    noise = rng.normal(0, 0.5, (rows, cols))

    elevation = (base + sgnp_hills + aarey + powai + mithi + dharavi + noise)
    elevation = np.clip(elevation, 0.5, 110.0).astype(np.float32)

    transform_coeff = [lon_res, 0.0, lon_w, 0.0, -lat_res, lat_n]
    meta: Dict[str, Any] = {
        "driver": "GTiff",
        "dtype": "float32",
        "nodata": -9999,
        "width": cols,
        "height": rows,
        "count": 1,
        "crs": s.default_crs,
        "transform": transform_coeff,
    }
    return elevation, meta
