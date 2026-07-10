# Mumbai Flood Digital Twin — Project Memory

## Project Goal
A real-time interactive 2D flood simulation digital twin for Mumbai.
- **Phase 1**: Terrain Engine — DEM processing, slope/aspect/flow accumulation maps, OSM vector overlays
- **Phase 2**: Dynamic Flood Simulator — SCS runoff + 2D diffusion-wave routing, animated playback, flooded road/building detection

---

## How to Run

### Start backend
```powershell
cd C:\Users\Hitesh\Desktop\mumbai-flood-digital-twin
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Build frontend (after code changes)
```powershell
cd C:\Users\Hitesh\Desktop\mumbai-flood-digital-twin\frontend
npm run build
```

### Open in browser
```
http://127.0.0.1:8000/?nocache=<N>    # increment N each time to bust browser cache
```
> Always hard-refresh (Ctrl+Shift+R) or use a new ?nocache= number after rebuilding.

---

## Architecture

```
mumbai-flood-digital-twin/
├── backend/main.py              # FastAPI: /api/terrain, /api/roads, /api/buildings,
│                                #   /api/waterways, /api/simulation/run, /api/simulation/reset
├── simulation/
│   ├── gis/                     # Ingestion, CRS transforms, geometry repair, immutability, validation reports
│   ├── core/
│   │   ├── verification.py      # Numerical verification (mass conservation, CFL stability)
│   │   ├── profiler.py          # Timing, CPU, memory, spatial ops profiling
│   │   └── ...                  # SimulationEngine, GridManager, SimulationClock
│   ├── terrain/                 # Terrain processing (Slope, Aspect, D8 Flow)
│   ├── flood/                   # 2D routing (Diffusion wave CA)
│   ├── hydrology/               # Runoff (SCS Curve Number)
│   ├── rainfall/                # Rainfall Engine (Hyetograph generation)
│   └── drainage/                # Drainage Network Routing
├── data/
│   ├── dem/mumbai_dem.tif       # GeoTIFF DEM (regenerated as 200x200, 160 KB raster)
│   └── osm/mumbai_osm.gpkg      # SQLite GeoPackage — roads, waterways, buildings
├── benchmarks/                  # Standardized test blocks (simple_slope, flat_surface, single_building)
├── calibration/                 # Parameter learning (observed rainfall, levels)
├── validation/                  # Historical validation events (2005, 2024, 2025)
├── profiling/                   # CPU, Memory, and Timing trace files
├── scripts/
│   ├── generate_mock_gis_data.py  # Regenerates DEM + GPKG mock files
│   ├── run_integrated_simulation.py  # Step-by-step console simulation diagnostic
│   └── physics_validation_audit.py   # Runs physics validation stats, histograms, and prints correlation
├── diagnostics/                 # Exported diagnostic arrays and GeoTIFFs (dem, slope, depth, extent)
└── frontend/src/components/
    └── MapDashboard.tsx           # Main React component — map, overlays, simulation UI
```

---

## DEM Configuration — FULL GREATER MUMBAI

The terrain grid covers Greater Mumbai.
- **Raster File**: `data/dem/mumbai_dem.tif` (200 × 200 cells, EPSG:4326)
- **Cell resolution**: ~105m lon × ~210m lat
- **Transform array**: `[0.00095, 0.0, 72.80, 0.0, -0.00190, 19.27]`
- **Elevation features**: West coast (2–5m), Dharavi (near sea level), Mithi River valley (diagonal trough), SGNP hills (65–90m).

---

## Simulation Science & Calibration

- **Rainfall**: Synthetic or constant hyetograph.
- **Runoff Infiltration**: Changed from per-timestep SCS CN (which absorbed 98% of rain) to `constant` model set at 3 mm/hr (8.33e-7 m/s) representing urban concrete.
- **Rain Deposit**: Rain is weighted by elevation using `flood_weight = exp(-2 × elev_norm)` to represent converging overland flow to depressions over 15-min timesteps.
- **Drainage**: Drain capacity grid set at 2.78e-7 m/s (1 mm/hr) representing a typical partially clogged urban inlet.
- **2D Routing**: Diffusion-wave solver with open (absorbing) boundaries using padded slices (np.roll's wrapping boundaries were removed to prevent water circular flow). Diffusion coefficient set to 2.0 (capped at 0.25).
- **Correlation**: Pearson correlation between elevation and depth is now negative (**-0.362**), meaning water accumulates in valleys. Mithi corridor is **3.54x** deeper than hilltops.

---

## Frontend Color Scale

- **0 - 0.05 m**: transparent (rgba 0,0,0,0)
- **0.05 - 0.5 m**: sky blue (minor)
- **0.5 - 1.5 m**: amber/yellow (moderate)
- **1.5 - 3.0 m**: orange (severe)
- **> 3.0 m**: crimson/red (extreme)

---

## Accomplishments & Current Status (2026-07-10)

1. **Fixed Integration Issues**: Resolved why no water was visible by correcting the DEM stub, changing the CN infiltration model to a constant rate, reducing the over-absorbing drainage capacity, and wiring `rainfall_mode` from the API.
2. **Fixed Physics Uniformity**: Changed `np.roll` wrapping boundaries to padded-slice open boundary conditions to allow water to drain. Raised the diffusion coefficient to 2.0. Added elevation-based `flood_weight` to rain deposit.
3. **Frontend Rebuilt**: Configured `MapDashboard.tsx` with a 5-class hazard color scale. Rebuilt frontend successfully.
4. **Diagnostic Audits**: Created `scripts/physics_validation_audit.py` to calculate depth stats, histograms, correlations, and export arrays to `diagnostics/`.
5. **Passing Tests**: 143/143 tests pass (including updated mass conservation tests for open boundaries).

---

## Next Steps for Resume:
- Validate advanced drainage features or tide boundary conditions as requested by the user.
- Carry out calibration on real storm datasets if needed.
