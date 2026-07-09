# System Design Document — Mumbai Flood Digital Twin

This document governs the system design, scientific parameters, and modular routing layout for the Mumbai Flood Digital Twin.

## 1. Overall Architecture

The platform uses a clean layered pattern separating web API routing, business services, database repositories, and the physical simulation kernel.

```
┌─────────────────────────────────────────────────────────┐
│                   API Controller Layer                  │
│       backend/api/terrain, gis, simulation.py           │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│                    Application Services                 │
│      TerrainService, GISService, SimulationService      │
└──────────────┬─────────────┬──────────────┬─────────────┘
               │             │              │
┌──────────────▼──────┐┌─────▼──────┐┌──────▼────────────┐
│   Database Repos    ││ Validation ││ Simulation Domain │
│ GIS, Terrain,       ││   Module   ││  Simulation-      │
│ Simulation Repos    ││ (CRS, DEM) ││  Controller       │
└─────────────────────┘└────────────┘└──────┬─────────────┘
                                            │
┌───────────────────────────────────────────▼─────────────┐
│                   Simulation Engines                    │
│  GridManager, Cell, Clock, State, landcover,            │
│  meteorology, infiltration, routing, tide, flood,       │
│  hydraulic_network                                      │
└─────────────────────────────────────────────────────────┘
```

## 2. Scientific Assumptions

* **Shallow Water Approximation:** Grid-based flow routing neglects momentum-based acceleration terms (diffusive wave approximation) in the initial phase, which is suitable for slow overland flow over flat terrain.
* **Intake Capacity Capping:** Stormwater intakes have a uniform inlet capacity. Water exceeding this capacity remains on the surface and continues routing.
* **Tidal Backwater:** Sea level is semidiurnal. local outfalls are blocked if sea level exceeds the outfall's elevation.

## 3. Simulation Workflow

Every simulation step coordinates:
1. `SimulationClock` advances the current step and calculates elapsed seconds.
2. `MeteorologyEngine` retrieves the spatial rainfall rate grid (m/s).
3. `TideEngine` calculates the boundary sea level height (m).
4. `InfiltrationEngine` calculates and subtracts the soil absorption layer (m).
5. `HydraulicNetworkEngine` calculates stormwater inlet capture and outfall block status.
6. `FlowRoutingEngine` performs vectorized 2D overland flow routing over sub-steps.
7. `FloodEngine` updates flood extent, duration, and Defra FD2321 hazard rating.

## 4. Coordinate Systems and Raster Resolution

* **Coordinate System:** WGS-84 Decimal Degrees (EPSG:4326) is the standard geographic reference system.
* **Resolution:** Grid resolution is 200 × 200 cells covering the full Greater Mumbai peninsula (72.80E to 72.99E, 18.89N to 19.27N). The equivalent resolution is ~105m longitude by ~210m latitude.

## 5. Flow Routing Strategy

* Diffusive-wave cellular automata routing using vectorized np.roll operations.
* 4-connectivity neighbor lookup.
* Sub-stepping (5 sub-steps per timestep) is used to keep the numerical scheme stable under the Courant-Friedrichs-Lewy (CFL) condition.

## 6. Future Hydraulic Solver

* **1-D dynamic wave solver:** Solve the St. Venant equations in channels and pipe conduits (integrating SWMM5 libraries).
* **2-D shallow water solver:** Godunov-type finite volume solver for shock wave routing.

## 7. Performance & Validation Strategy

* **Performance:** Vectorized matrix math with NumPy, windowed GeoTIFF reads with Rasterio, and in-memory caching of static layers.
* **Validation:** Explicit CRS compliance check, grid boundary alignment validator, and drain connectivity topology checks prior to execution.
