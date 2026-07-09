# Architecture — Mumbai Flood Digital Twin

## Overview

The Mumbai Flood Digital Twin is a research-grade GIS and hydrological
simulation platform. It is organized around Clean Architecture principles:
the simulation domain is completely independent of the API layer, which is
independent of the configuration layer.

```
┌─────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)               │
│  backend/api/terrain.py                             │
│  backend/api/gis.py                                 │
│  backend/api/simulation.py                          │
└───────────────────┬─────────────────────────────────┘
                    │ calls
┌───────────────────▼─────────────────────────────────┐
│               Service Layer                         │
│  TerrainService   GISService   SimulationService    │
│  RainfallService  GISLayerManager                   │
└───────────────────┬─────────────────────────────────┘
                    │ calls
┌───────────────────▼─────────────────────────────────┐
│             Simulation Domain                       │
│  SimulationEngine (orchestrator)                    │
│    ├── TerrainEngine (DEM + derivatives)            │
│    ├── HydrologyEngine (SCS runoff + weights)       │
│    ├── RainfallEngine (hyetograph)                  │
│    ├── DrainageEngine (network capacity)            │
│    └── FloodEngine (2D diffusion routing)           │
└───────────────────┬─────────────────────────────────┘
                    │ reads
┌───────────────────▼─────────────────────────────────┐
│              Data Layer                             │
│  data/dem/mumbai_dem.tif   data/osm/mumbai_osm.gpkg │
│  (PostgreSQL/PostGIS — Phase 3)                     │
└─────────────────────────────────────────────────────┘
```

## Design Principles

| Principle | How Applied |
|---|---|
| **Single Responsibility** | Each class has exactly one reason to change |
| **Open/Closed** | Engines accept any elevation array — no Mumbai-specific hardcoding in logic |
| **Liskov** | RainfallMode enum allows swapping modes without changing callers |
| **Interface Segregation** | TerrainService exposes metadata OR full grid — caller chooses |
| **Dependency Inversion** | API controllers depend on service abstractions, not engines directly |
| **Clean Architecture** | Simulation domain has zero imports from FastAPI or HTTP layer |

## Dependency Rules

```
Allowed: API → Service → Engine → Algorithms
Forbidden: Engine → API  /  Engine → Service
Allowed: Any layer → backend/config/settings.py
Allowed: Any layer → backend/utils/logger.py
Allowed: Any layer → backend/exceptions.py
```

## Key Architectural Decisions

### No Globals in Controllers
All services are module-level singletons injected via import.
FastAPI `Depends()` can be adopted in Phase 3 for full DI.

### Stateless Simulation Runs
Each `POST /api/simulation/run` creates a fresh `SimulationEngine` instance.
This is thread-safe and avoids shared state bugs.
Phase 3 can add a task queue (Celery + Redis) for long-running simulations.

### Backward-Compatible API
`/api/terrain` returns full raster arrays (for the existing frontend).
`/api/terrain/metadata` returns only statistics (for lightweight clients and future dashboards).

### Shim Layer
Old flat files (`simulation/terrain.py`, `simulation/flood.py`, etc.) are preserved
as thin re-export shims. This allows gradual migration of any external code
without breaking changes.
