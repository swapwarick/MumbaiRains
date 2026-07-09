# Project Folder Structure — Mumbai Flood Digital Twin

The project is structured following modular design and clean architecture principles. This ensures a clean separation of concerns between web services, GIS layer management, numerical simulation kernels, tests, and frontend presentation.

```
mumbai-flood-digital-twin/
│
├── backend/                        # FastAPI Web API Application
│   ├── api/                        # API route controllers (no business logic)
│   │   ├── gis.py                  # Routes for vector layers (roads, buildings, waterways)
│   │   ├── simulation.py           # Routes for running & controlling simulations
│   │   └── terrain.py              # Routes for DEM elevations and stats
│   ├── config/                     # Global settings and environment overrides
│   │   └── settings.py             # Pydantic Settings configuration manager
│   ├── models/                     # Request/Response Pydantic validation models
│   │   └── simulation.py           # Simulation parameters and response schemas
│   ├── schemas/                    # Pydantic serializer schemas
│   │   └── terrain.py              # Serializers for terrain metadata and grid datasets
│   ├── services/                   # Application services (the glue between API and Simulation)
│   │   ├── gis_service.py          # Exposes GeoJSON layers; maps GPKG to API format
│   │   ├── rainfall_service.py     # Rainfall profile preview and configuration
│   │   ├── simulation_service.py   # Wires API calls to the Simulation Engine
│   │   └── terrain_service.py      # Lazily evaluates and caches the DEM model
│   ├── utils/                      # Helper utilities
│   │   └── logger.py               # Structured logger with custom formatters
│   ├── exceptions.py               # Custom platform exceptions mapped to HTTP errors
│   └── main.py                     # FastAPI entry point and router registration
│
├── simulation/                     # Core GIS and Hydrological Simulation Domain
│   ├── core/                       # Simulation pipeline coordination
│   │   └── simulation_engine.py    # Master orchestrator for the simulation run
│   ├── drainage/                   # Storm-water networks & drainage models
│   │   └── engine.py               # DrainageEngine (pipe flow & inlet interception)
│   ├── flood/                      # Overland 2D flood routing
│   │   └── engine.py               # FloodEngine (vectorized diffusion-wave ca routing)
│   ├── hydrology/                  # Hydrological runoff and infiltration
│   │   ├── engine.py               # HydrologyEngine (spatial runoff & weights)
│   │   └── runoff.py               # SCS Curve Number mathematical functions
│   ├── rainfall/                   # Rainfall storm profiles
│   │   └── engine.py               # RainfallEngine (hyetographs & alternating block)
│   └── terrain/                    # GIS DEM loading & analysis
│       ├── algorithms.py           # Vectorized NumPy functions (slope, aspect, flow direction)
│       ├── engine.py               # TerrainEngine (caching and property manager)
│       └── loader.py               # DEM TIFF reader & synthetic fallback model
│
├── data/                           # Geographic data files
│   ├── dem/                        # Digital Elevation Models (mumbai_dem.tif)
│   └── osm/                        # OpenStreetMap vector layers (mumbai_osm.gpkg)
│
├── docs/                           # Platform Architecture & Developer Documentation
│   ├── API.md                      # API endpoint definitions and responses
│   ├── Architecture.md             # Core design principles and layer diagram
│   ├── FolderStructure.md          # This file
│   ├── Hydrology.md                # Theoretical background on SCS CN and routing
│   └── Simulation.md               # Simulation execution and stability parameters
│
├── tests/                          # Automated Pytest Suite
│   ├── conftest.py                 # Shared fixtures (tiny_dem, flat_dem, etc.)
│   ├── test_api.py                 # FastAPI integration tests
│   ├── test_hydrology.py           # Runoff formula unit tests
│   ├── test_rainfall.py            # Storm hyetograph unit tests
│   ├── test_simulation.py          # 2D routing integration and conservation tests
│   └── test_terrain.py             # Slope, aspect, and flow unit tests
│
├── scripts/                        # Automation & GIS generation utilities
│   └── generate_mock_gis_data.py   # Regenerates fallback DEM and GPKG mock layers
│
└── frontend/                       # React + TypeScript + MapLibre GL UI Dashboard
```

## Key Directory Guidelines

1. **`backend/api/`** must contain only routing code. It should never contain simulation equations, database queries, or GIS file IO.
2. **`backend/services/`** is the only layer allowed to instantiate or talk to classes in `simulation/`. It is also the caching layer.
3. **`simulation/`** must be self-contained. Code in this directory should never import from `backend/` or `fastapi` packages.
4. **`tests/`** should run and pass in under 2 seconds. Any long-running simulation test should use a downscaled grid (e.g. 10x10) or mocks.
