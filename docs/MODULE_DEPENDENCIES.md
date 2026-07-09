# Module Dependencies Document — Mumbai Flood Digital Twin

This document details the coupling rules, dependency guidelines, and module interaction flow of the Digital Twin.

## 1. Dependency Graph

The following diagram illustrates the unidirectional layer dependencies. Higher layers can import from lower layers, but lower layers must never import from higher ones.

```
                  ┌──────────────────────┐
                  │   FastAPI Routers    │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Application Services │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌──────────────────────┐           ┌──────────────────────┐
│  Database Repos      │           │ SimulationController │
└──────────────────────┘           └──────────┬───────────┘
                                              │
                       ┌──────────────────────┴──────────────────────┐
                       ▼                                             ▼
            ┌──────────────────────┐                      ┌──────────────────────┐
            │  Boundary Engines    │                      │   Physical Engines   │
            │  clock, state,       │                      │  landcover, routing, │
            │  meteorology, tide   │                      │  infiltration,       │
            └──────────────────────┘                      │  hydraulic_network,  │
                                                          │  flood               │
                                                          └──────────────────────┘
```

## 2. Key Interaction Sequence

When a simulation run is requested:

```
[SimulationService] ──> [SimulationController.initialize]
                           │
                           ├── GridManager.initialize_grid
                           ├── InfiltrationEngine.initialise
                           └── TideEngine / MeteorologyEngine.initialise
[SimulationService] ──> [SimulationController.run_all]
                           │
                           ├── loop: SimulationController.step()
                           │           │
                           │           ├── SimulationClock.advance_timestep()
                           │           ├── Ingest rain & tide boundaries
                           │           ├── InfiltrationEngine.compute_infiltration()
                           │           ├── HydraulicNetworkEngine.apply_drainage_intake()
                           │           ├── FlowRoutingEngine.route() (sub-stepping)
                           │           └── FloodEngine.update_metrics()
                           │
                           └── returns depth history
```

## 3. Coupling Guardrails

* **Zero Web Dependency in Simulation:** No module in `simulation/` may import from `backend/`, `fastapi`, or `starlette`.
* **Gatekeeper Grid Access:** The `GridManager` is the only class allowed to load and parse raster DEM data.
* **No SQL in Engines:** Hydrological and hydraulic routing engines must be pure mathematical modules. Any database or file I/O must be performed through the `backend/database/repositories/` layer.
