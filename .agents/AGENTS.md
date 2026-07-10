# Urban Hydrodynamic Simulation Platform (UHSP) — Project Memory

## Project Goal
A real-time interactive 2D flood simulation platform for Greater Mumbai.
- **Phase 1**: Terrain Engine — DEM processing, slope/aspect/flow accumulation maps, OSM vector overlays.
- **Phase 2**: Dynamic Flood Simulator — SCS runoff + 2D diffusion-wave routing, animated playback, flooded road/building detection.
- **Phase B**: Validation, Calibration, and Assessment — Establishing scientific credibility via golden verification benchmarks and real-data validation case studies.

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
├── backend/
│   ├── main.py                  # FastAPI server and startup validation
│   └── data/                    # DataProvider & Repository Layer (Terrain, GIS, Scenario, etc.)
├── simulation/
│   ├── checkpoints/             # State serialization manager (save, load, resume)
│   ├── plugins/                 # Extensible solver registry and engine adapters
│   ├── diagnostics/             # Post-simulation diagnostic reports and plotting
│   └── core/
│       ├── verification.py      # Numerical verification (mass conservation, CFL stability)
│       └── ...                  # SimulationEngine, GridManager, SimulationClock
├── verification/
│   ├── golden/                  # Immutable benchmark reference outputs
│   ├── outputs/                 # Run arrays and validation GeoTIFFs
│   ├── plots/                   # Matplotlib scientific charts
│   ├── run_verification.py      # Verification benchmark runner
│   ├── kurla_study.py           # BKC case study runner
│   └── dashboard.py/html        # Compiled validation results dashboard
├── scenarios/                   # Packaged scenario folders (synthetic, historical_2005, blocked_drain)
├── data/
│   ├── dem/mumbai_dem.tif       # GeoTIFF DEM (200x200 raster)
│   └── osm/mumbai_osm.gpkg      # SQLite GeoPackage
└── UHSP_ASSESSMENT.md           # Platform evaluation report and release recommendation
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
- **Runoff Infiltration**: Constant model set at 3 mm/hr (8.33e-7 m/s) representing urban concrete.
- **Rain Deposit**: Rain is weighted by elevation using `flood_weight = exp(-2 × elev_norm)` to represent converging overland flow to depressions over 15-min timesteps.
- **Drainage**: Drain capacity grid set at 2.78e-7 m/s (1 mm/hr) representing a typical partially clogged urban inlet.
- **2D Routing**: Diffusion-wave solver with open (absorbing) boundaries using padded slices (np.roll's wrapping boundaries were removed to prevent water circular flow). Diffusion coefficient set to 2.0 (capped at 0.25).
- **Correlation**: Pearson correlation between elevation and depth is negative (**-0.362**), meaning water accumulates in valleys. Mithi corridor is **3.54x** deeper than hilltops.

---

## Frontend Color Scale

- **0 - 0.05 m**: transparent (rgba 0,0,0,0)
- **0.05 - 0.5 m**: sky blue (minor)
- **0.5 - 1.5 m**: amber/yellow (moderate)
- **1.5 - 3.0 m**: orange (severe)
- **> 3.0 m**: crimson/red (extreme)

---

## Accomplishments & Current Status (2026-07-10)

1. **Refactored Architecture for Version 1.0 Beta**: Decoupled file system logic with `DataProvider` and repositories. Implemented full `SimulationController` dependency injection and swappable solver interfaces under a new Plugin framework.
2. **State Checkpoints & Reproducibility**: Added full state save, load, and resume checkpoints. Recorded environmental versions, git commits, and file checksums in Version 2 of `SimulationManifest.json`.
3. **Scientific Verification Suite**: Created 7 verification benchmarks (Flat Plane, Single Slope, Bowl, Ridge, Blocked Drain, River Valley, Urban Block) comparing against baseline configurations in `golden/` with tight tolerances. All benchmarks pass validation.
4. **BKC Validation Case Study**: Completed validation simulation of the Kurla district using real Copernicus DEM and OSM layers, outputting georeferenced GeoTIFFs, flood/velocity maps, and drainage intake statistics.
5. **Interactive Dashboard & Reports**: Authored `UHSP_ASSESSMENT.md` (Release recommendation: YES), `UNCERTAINTY_REGISTER.md`, and compiled an interactive HTML validation dashboard displaying scientific graphs (hydrographs, mass balances, etc.).
6. **Passing Tests**: 147/147 tests pass.

---

## Next Steps for Resume:
- Integrate spatial Curve Number (SCS CN) soils mapping.
- Wire street-level drainage pipe network configurations into the 1D hydraulic strategy.
