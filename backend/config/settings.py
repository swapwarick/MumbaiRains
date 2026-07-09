"""
Configuration Settings
----------------------
All application configuration is defined here using Pydantic BaseSettings.
Values can be overridden via environment variables or a .env file.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root — two levels up from this file (backend/config/settings.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Centralised configuration for the Mumbai Flood Digital Twin platform.
    All hardcoded paths and magic numbers live here.
    Override any value by setting the matching environment variable.
    """

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ #
    # Application
    # ------------------------------------------------------------------ #
    app_title: str = "Mumbai Flood Digital Twin API"
    app_version: str = "2.0.0"
    app_phase: str = "Phase 2 - Hydrological Simulation Engine"
    log_level: str = "INFO"

    # ------------------------------------------------------------------ #
    # File system paths
    # ------------------------------------------------------------------ #
    project_root: Path = _PROJECT_ROOT
    dem_path: Path = _PROJECT_ROOT / "data" / "dem" / "mumbai_dem.tif"
    gpkg_path: Path = _PROJECT_ROOT / "data" / "osm" / "mumbai_osm.gpkg"
    output_dir: Path = _PROJECT_ROOT / "data" / "output"
    frontend_dist: Path = _PROJECT_ROOT / "frontend" / "dist"

    # ------------------------------------------------------------------ #
    # GIS / Raster configuration
    # ------------------------------------------------------------------ #
    default_crs: str = "EPSG:4326"
    tile_size: int = 256          # pixels per raster tile
    cell_size_m: float = 30.0     # metres per DEM cell (used in flow calculations)

    # Mumbai DEM fallback extent (when rasterio is unavailable)
    dem_fallback_cols: int = 200
    dem_fallback_rows: int = 200
    dem_fallback_lon_west: float = 72.80
    dem_fallback_lat_north: float = 19.27
    dem_fallback_lon_east: float = 72.99
    dem_fallback_lat_south: float = 18.89

    # ------------------------------------------------------------------ #
    # Simulation defaults
    # ------------------------------------------------------------------ #
    default_duration_hours: int = 4
    default_intensity_mm_hr: float = 30.0
    default_timestep_min: int = 15
    default_cn: float = 85.0       # SCS Curve Number — urban impervious surface
    diffusion_substeps: int = 5    # sub-steps per simulation timestep

    # ------------------------------------------------------------------ #
    # Database (PostGIS) — stub ready for Phase 3
    # ------------------------------------------------------------------ #
    database_url: str = "postgresql://flood:flood@localhost:5432/mumbai_flood"
    db_pool_size: int = 5
    db_max_overflow: int = 10


# Module-level singleton — import `settings` everywhere
settings = Settings()
