"""
backend/main.py
---------------
FastAPI application factory.

Responsibilities (ONLY):
    1. Create the FastAPI app instance
    2. Register CORS middleware
    3. Mount API routers
    4. Serve the frontend static build
    5. Handle the root route

No business logic. No direct simulation imports.
No database queries. No GIS loading.
"""

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.utils import get_logger
from backend.api.terrain import router as terrain_router
from backend.api.gis import router as gis_router
from backend.api.simulation import router as simulation_router

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI instance.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        description=settings.app_phase,
    )

    # ------------------------------------------------------------------ #
    # Startup Configuration Validation (Task 8)
    # ------------------------------------------------------------------ #
    @app.on_event("startup")
    def validate_configuration_on_startup() -> None:
        logger.info("Running startup configuration validations...")
        
        # 1. Validate DEM file
        dem_path = str(settings.dem_path)
        if not os.path.exists(dem_path):
            raise RuntimeError(f"Startup validation failed: Copernicus DEM file is missing at {dem_path}")
        if os.path.getsize(dem_path) < 1024:
            raise RuntimeError(f"Startup validation failed: Copernicus DEM file at {dem_path} is invalid/empty.")
            
        # 2. Validate OSM GeoPackage file
        gpkg_path = str(settings.gpkg_path)
        if not os.path.exists(gpkg_path):
            raise RuntimeError(f"Startup validation failed: OSM GeoPackage is missing at {gpkg_path}")
            
        # 3. Validate Cache directory
        cache_dir = os.path.join(str(settings.project_root), "data", "cache", "terrain")
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception as exc:
            raise RuntimeError(f"Startup validation failed: Cache directory at {cache_dir} is not creatable: {exc}")
            
        # 4. Validate Output directory is writable
        output_dir = str(settings.output_dir)
        try:
            os.makedirs(output_dir, exist_ok=True)
            test_file = os.path.join(output_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as exc:
            raise RuntimeError(f"Startup validation failed: Output directory at {output_dir} is not writable: {exc}")

        # 5. Validate Scenarios directory exists
        scenarios_dir = os.path.join(str(settings.project_root), "scenarios")
        if not os.path.exists(scenarios_dir) or not os.listdir(scenarios_dir):
            raise RuntimeError(f"Startup validation failed: Scenarios directory at {scenarios_dir} is missing or empty.")

        logger.info("All startup configuration validations passed successfully.")

    # ------------------------------------------------------------------ #
    # Middleware
    # ------------------------------------------------------------------ #
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    # API Routers
    # ------------------------------------------------------------------ #
    app.include_router(terrain_router)
    app.include_router(gis_router)
    app.include_router(simulation_router)

    # ------------------------------------------------------------------ #
    # Root route — serves index.html for HTML requests, JSON for others
    # ------------------------------------------------------------------ #
    @app.get("/", include_in_schema=False)
    def read_root(request: Request):
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            index_path = settings.frontend_dist / "index.html"
            if index_path.exists():
                return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
        return {
            "status": "running",
            "project": "Urban Hydrodynamic Simulation Platform (UHSP)",
            "phase": settings.app_phase,
            "version": settings.app_version,
        }

    # ------------------------------------------------------------------ #
    # Static files — serve built React app
    # ------------------------------------------------------------------ #
    dist_path = str(settings.frontend_dist)
    if os.path.exists(dist_path):
        app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")
        logger.info("Frontend static files mounted", extra={"path": dist_path})
    else:
        logger.warning("Frontend dist not found — run 'npm run build' in frontend/")

    return app


# Create the module-level app instance that uvicorn targets
app = create_app()
logger.info(f"{settings.app_title} v{settings.app_version} ready")
