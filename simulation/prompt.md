You are a senior GIS software architect, hydrologist, and full-stack engineer.

We are building a production-quality application called "Mumbai Flood Digital Twin".

The application will simulate rainfall, storm-water drainage, runoff, and flooding across Mumbai using real GIS datasets.

This is NOT a visualization project. It is a scientific simulation platform.

========================
PROJECT GOAL
========================

Build a modular digital twin capable of:

- Loading Copernicus DEM
- Loading OpenStreetMap GeoPackage
- Simulating rainfall
- Simulating runoff
- Simulating drainage
- Computing flood depth
- Showing flood progression over time
- Supporting historical and custom rainfall events
- Later integrating IMD rainfall and tide data

========================
TECH STACK
========================

Backend
- Python 3.12
- FastAPI
- Rasterio
- GeoPandas
- NumPy
- SciPy
- Shapely
- PyProj
- PySheds
- NetworkX
- SQLAlchemy

Database
- PostgreSQL
- PostGIS

Frontend
- React
- TypeScript
- Vite
- MapLibre GL
- TailwindCSS

Visualization
- MapLibre
- Deck.gl
- Later: CesiumJS

Testing
- pytest

========================
PROJECT STRUCTURE
========================

mumbai-flood-digital-twin/

data/
    dem/
        mumbai_dem.tif

    osm/
        mumbai_osm.gpkg

    rainfall/

    drainage/

    rivers/

    tide/

    output/

backend/

frontend/

simulation/

docs/

tests/

========================
SIMULATION MODULES
========================

Create independent simulation modules.

terrain.py

Responsibilities

- Read DEM
- Generate elevation model
- Generate slope
- Generate aspect
- Generate flow direction
- Generate flow accumulation

rainfall.py

Responsibilities

- Read rainfall datasets
- Support historical replay
- Support synthetic rainfall

runoff.py

Responsibilities

- Cellular runoff simulation
- Surface water movement
- Infiltration

drainage.py

Responsibilities

- River flow
- Storm-water drains
- Overflow
- Pump stations (future)

flood.py

Responsibilities

- Water depth
- Flood extent
- Flood duration
- Velocity

========================
BACKEND API
========================

Create REST endpoints.

GET /terrain

GET /roads

GET /buildings

GET /simulation/status

POST /simulation/run

POST /simulation/reset

POST /rainfall/load

GET /flood/depth

GET /flood/history

========================
FRONTEND
========================

React dashboard.

Features

- Interactive map
- Rainfall slider
- Time slider
- Play/Pause simulation
- Flood depth colors
- Road flooding
- Building flooding
- Layer manager
- Legend
- Simulation controls

========================
ARCHITECTURE
========================

Use clean architecture.

Separate:

GIS
Hydrology
Simulation
API
Frontend

No business logic inside API controllers.

Use dependency injection where appropriate.

Use dataclasses or Pydantic models.

========================
INITIAL MILESTONE
========================

Only implement Phase 1.

Phase 1

- Load DEM
- Load OSM
- Display terrain
- Display roads
- Display waterways
- Display buildings
- Verify CRS
- Build Terrain Engine

No flood simulation yet.

========================
FUTURE PHASES
========================

Phase 2

Rainfall engine

Phase 3

Runoff engine

Phase 4

Drainage engine

Phase 5

Flood engine

Phase 6

Historical replay

Phase 7

Real-time IMD integration

Phase 8

AI-assisted scenario analysis

========================
CODE QUALITY
========================

Generate production-quality code.

Use type hints.

Use docstrings.

Use logging.

Avoid duplicated code.

Provide architecture documentation.

Generate a README describing how to run the application.

Generate requirements.txt.

Generate Docker support.

The codebase should be maintainable and scalable for a city-wide digital twin.






=--=-=-=-=-=-

You are the Lead Software Architect for the Mumbai Flood Digital Twin project.

Review the entire existing codebase before making any changes.

Do NOT generate duplicate code.

Do NOT rewrite working modules unnecessarily.

Your task is to refactor the project into a scalable research-grade GIS and hydrology platform.

==================================================
OBJECTIVE
==================================================

Transform the current prototype into a modular architecture suitable for simulating Mumbai flooding using real GIS datasets.

The architecture must support:

• DEM processing
• Hydrological modelling
• Rainfall simulation
• Surface runoff
• Storm-water drainage
• River flow
• Flood depth calculation
• Historical replay
• Future AI decision support

The architecture must be modular and production ready.

==================================================
DO NOT CHANGE
==================================================

Keep existing:

- FastAPI
- React
- TypeScript
- Docker
- PostgreSQL
- PostGIS
- MapLibre
- Existing DEM
- Existing GeoPackage

unless absolutely necessary.

==================================================
REFACTOR PROJECT STRUCTURE
==================================================

Organize the project into:

backend/

    api/
    services/
    config/
    database/
    models/
    schemas/
    utils/

simulation/

    terrain/
    hydrology/
    drainage/
    flood/
    rainfall/
    visualization/

frontend/

docs/

tests/

scripts/

==================================================
CONFIGURATION
==================================================

Create

backend/config/settings.py

using Pydantic Settings.

Move every hardcoded path into configuration.

Example

DEM path

OSM path

Database

Tile size

Simulation timestep

Rainfall defaults

Output folder

==================================================
REMOVE HARDCODING
==================================================

Do NOT hardcode

DEM path

GeoPackage path

Rainfall values

Tile size

CRS

Database connection

Everything must come from configuration.

==================================================
LOGGING
==================================================

Replace print() with Python logging.

Create

backend/utils/logger.py

Use structured logging.

==================================================
API DESIGN
==================================================

API controllers must contain NO simulation logic.

Controllers should only

validate requests

call services

return responses

Simulation logic belongs only inside

simulation/

==================================================
CREATE SERVICES
==================================================

Create

TerrainService

SimulationService

GISService

LayerService

RainfallService

These services communicate with simulation modules.

==================================================
GIS LAYER MANAGER
==================================================

Create

GISLayerManager

Responsibilities

Load DEM

Load GeoPackage

Load Roads

Load Buildings

Load Waterways

Validate CRS

Validate Geometry

Cache loaded layers

==================================================
TERRAIN ENGINE
==================================================

Create

TerrainEngine

Responsibilities

Load DEM

Generate

Slope

Aspect

Hillshade

Flow Direction

Flow Accumulation

Watersheds

TerrainEngine should expose clean methods.

==================================================
DO NOT RETURN ENTIRE DEM
==================================================

Current implementation converts entire raster into JSON.

Replace this.

Instead

Store raster internally.

Return

Metadata

Requested window

Statistics

Preview

Later support raster tiles.

==================================================
SIMULATION ENGINE
==================================================

Create

SimulationEngine

Responsibilities

Manage simulation state

Current timestep

Current rainfall

Current water depth

Simulation controls

Start

Pause

Resume

Reset

==================================================
RAINFALL ENGINE
==================================================

Create RainfallEngine.

Support

Constant rainfall

Historical rainfall

Synthetic rainfall

Future IMD integration

==================================================
HYDROLOGY ENGINE
==================================================

Create

HydrologyEngine

Responsibilities

Surface runoff

Infiltration

Flow routing

Cell updates

==================================================
DRAINAGE ENGINE
==================================================

Create

DrainageEngine

Responsibilities

Natural rivers

Nullahs

Storm-water drains

Overflow

Sea outlets

==================================================
FLOOD ENGINE
==================================================

Create

FloodEngine

Responsibilities

Water depth

Flood extent

Velocity

Flood duration

==================================================
DEPENDENCY INJECTION
==================================================

Avoid globals.

Use dependency injection.

==================================================
ERROR HANDLING
==================================================

Create custom exceptions

TerrainException

SimulationException

GISException

DrainageException

RainfallException

==================================================
DATABASE
==================================================

Create repositories.

Repository layer only accesses PostGIS.

Simulation must never directly query database.

==================================================
TESTING
==================================================

Create pytest tests.

Terrain

Hydrology

Rainfall

Simulation

==================================================
DOCUMENTATION
==================================================

Create

Architecture.md

Simulation.md

Hydrology.md

API.md

FolderStructure.md

==================================================
CODE QUALITY
==================================================

Use

Python type hints

Docstrings

SOLID

Clean Architecture

No duplicated code

No giant files

Prefer classes over utility functions.

==================================================
PERFORMANCE
==================================================

Avoid Python loops over rasters.

Use

NumPy

Vectorization

Rasterio

Lazy loading

Cache frequently used datasets.

==================================================
OUTPUT
==================================================

Refactor only.

Do not implement rainfall simulation yet.

Do not implement flood simulation yet.

Do not add placeholder code.

Produce a clean, scalable architecture ready for Phase 2.

After refactoring, generate a detailed report describing

1. What was changed

2. Why it was changed

3. Remaining technical debt

4. Recommended Phase 2 work