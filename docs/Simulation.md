# Simulation Engine Reference — Mumbai Flood Digital Twin

This document details the design, state management, and execution pipeline of the 2D Flood Simulation Engine.

## Simulation Pipeline Flow

The simulation runs in a sequential pipeline coordinated by the central `SimulationEngine`. The sequence of operations is as follows:

```
[Start Simulation]
        │
        ▼
1. Load Terrain (TerrainEngine)
        │  Reads DEM, computes slope, aspect, D8 flow, etc.
        ▼
2. Hydrology Initialisation (HydrologyEngine)
        │  Pre-computes elevation-based flood weights & drainage factors.
        ▼
3. Load Drainage Network (DrainageEngine)
        │  Loads pipe nodes/conduits or builds synthetic grid.
        ▼
4. Generate Hyetograph (RainfallEngine)
        │  Generates rain depth (mm) array based on storm intensity/duration.
        ▼
5. Time Loop (for each timestep in Hyetograph):
        ├── a. Compute Incremental Runoff (HydrologyEngine)
        │      Uses SCS Curve Number + spatial weights.
        ├── b. Add Runoff to Grid (FloodEngine)
        │      Applies runoff depth (m) to the simulation state.
        ├── c. Route 2D Overland Flow (FloodEngine)
        │      Runs diffusion-wave cellular automata routing over substeps.
        └── d. Capture State Snapshot
               Saves a rounded 2D float grid of water depths.
        ▼
[Return Results]
```

## Engines and Responsibilities

### 1. `SimulationEngine`
* **File:** `simulation/core/simulation_engine.py`
* **Role:** Master orchestrator. Wires all subsystems together, runs the time-loop, captures states, and returns final historical depth data.

### 2. `TerrainEngine`
* **File:** `simulation/terrain/engine.py`
* **Role:** Manages the Digital Elevation Model (DEM) and derived matrices (slope, aspect, flow direction/accumulation). It uses lazy-evaluation and caching to optimize performance.

### 3. `RainfallEngine`
* **File:** `simulation/rainfall/engine.py`
* **Role:** Translates rainfall parameters (intensity, duration, timestep) and distribution profiles (e.g. constant, alternating-block synthetic) into a time-series vector of rainfall increments.

### 4. `HydrologyEngine`
* **File:** `simulation/hydrology/engine.py`
* **Role:** Applies the SCS Curve Number method to convert rainfall depth into surface runoff. It handles spatial redistribution based on topographic factors (e.g., lower elevations get more water) and drainage deduction.

### 5. `DrainageEngine`
* **File:** `simulation/drainage/engine.py`
* **Role:** Represents the underground storm-water pipe network and manholes. Provides drainage capacity checks and scaffolds Phase 3 hydraulic routing.

### 6. `FloodEngine`
* **File:** `simulation/flood/engine.py`
* **Role:** Performs the 2D diffusion-wave routing over the elevation grid. Computes the horizontal movement of water between adjacent cells.

## Numerical Routing and Sub-stepping

The flood routing solves a simplified 2D diffusion-wave equation using a cellular automata approach:
$$Q_{ij \to nr,nc} = \max(H_{ij} - H_{nr,nc}, 0) \times C_{diff} \times D_{ij}$$

Where:
* $H$ is the hydraulic head (elevation $Z$ + water depth $D$).
* $C_{diff}$ is the diffusion coefficient ($0.1 \times dt / \text{cell\_size}^2$).
* $dt$ is the timestep duration.

To maintain numerical stability (i.e. to prevent water from oscillating wildly between adjacent cells and creating negative depths), the diffusion coefficient is capped at `0.25` (the Von Neumann stability condition for 2D grids), and the flow out of a single cell is limited to a maximum of 20% of its current volume per direction.

To allow large timesteps (e.g. 15 minutes) on the API level while keeping the physical routing stable, each timestep is broken down into `5` sub-steps inside the `FloodEngine`.

## Key Performance Features

* **No Python loops:** The routing logic uses fully vectorized NumPy array operations (`np.roll`), making execution extremely fast.
* **Stateless execution:** Every run is independent. State is contained within the request-response cycle, allowing the backend to remain thread-safe.
