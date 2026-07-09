# API Design Document — Mumbai Flood Digital Twin

This document details the FastAPI controllers, serialization schemas, Pydantic request models, error formats, and database repositories.

## 1. REST Endpoints

### Terrain API
* `GET /api/terrain`: Returns the full 2D grid arrays (elevation, slope, aspect, flow accumulation/direction) for backward compatibility with the frontend.
* `GET /api/terrain/metadata`: Returns lightweight terrain bounding coordinates and statistics (min/max elevation) without grid arrays.

### GIS API
* `GET /api/roads`: Returns GeoJSON line geometries for the road network.
* `GET /api/buildings`: Returns GeoJSON polygon footprints for building areas.
* `GET /api/waterways`: Returns GeoJSON line geometries for waterways/rivers.

### Simulation API
* `GET /api/simulation/status`: Reports the readiness of the simulation engine.
* `POST /api/simulation/run`: Triggers a simulation run based on rainfall intensity, storm duration, and scenario settings.
* `POST /api/simulation/reset`: Resets dynamic water and diagnostic states.

## 2. Pydantic Models and Validation

Incoming requests are validated at the router boundaries using Pydantic fields:
- `duration_hours`: Int between 1 and 72 hours.
- `intensity_mm_hr`: Float between 0.0 and 500.0 mm/hr.
- `time_step_min`: Int between 5 and 60 minutes.

Invalid payloads return a standard `422 Unprocessable Entity` containing field-level error messages.

## 3. Database Repository Layer

Controllers never access files or SQL directly. Database operations are delegated to repositories located in `backend/database/repositories/`:

* **`GISRepository`:** Abstracts GeoPackage layer reading, CRS reprojections, and GeoJSON queries.
* **`TerrainRepository`:** Manages raster GeoTIFF DEM file loading and windowed reads.
* **`SimulationRepository`:** Handles saving and loading simulation run history to JSON or PostGIS.
