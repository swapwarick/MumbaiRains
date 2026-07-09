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
│   ├── dem/mumbai_dem.tif       # GeoTIFF DEM (stub — rasterio not installed; fallback in terrain.py)
│   └── osm/mumbai_osm.gpkg      # SQLite GeoPackage — roads, waterways, buildings
├── benchmarks/                  # Standardized test blocks (simple_slope, flat_surface, single_building)
├── calibration/                 # Parameter learning (observed rainfall, levels)
├── validation/                  # Historical validation events (2005, 2024, 2025)
├── profiling/                   # CPU, Memory, and Timing trace files
├── scripts/
│   └── generate_mock_gis_data.py  # Regenerates DEM + GPKG mock files
└── frontend/src/components/
    └── MapDashboard.tsx           # Main React component — map, overlays, simulation UI
```

---

## DEM Configuration — FULL GREATER MUMBAI (CRITICAL)

The terrain grid must cover full Greater Mumbai. This is defined in the FALLBACK inside
`simulation/terrain.py` (around line 32) since rasterio is NOT installed.

| Setting | Value |
|---|---|
| Grid size | 200 × 200 cells |
| Longitude | 72.80 → 72.99 (west coast → eastern suburbs) |
| Latitude | 18.89 → 19.27 (Bandra → Borivali) |
| Cell resolution | ~105m lon × ~210m lat |
| Transform array | `[0.00095, 0.0, 72.80, 0.0, -0.00190, 19.27]` |

**If the grid shows as a tiny rectangle** in one corner of Mumbai, it means the old
fallback (100×100 at lon=72.85, lat=19.15) is running. Fix by ensuring `terrain.py`
contains the 200×200 full Mumbai fallback.

### Elevation model features
- West coast (Bandra, Juhu): 2–5m — floods first
- Dharavi (south-central): near sea level — heavy flooding
- Mithi River valley: diagonal NE→SW trough
- Aarey/Goregaon hills: 30–50m
- SGNP/Borivali hills (north-east): 65–90m — never floods

---

## Simulation Science

- **Rainfall**: Synthetic hyetograph, uniform distribution, configurable intensity + duration
- **Runoff**: SCS Curve Number (CN=85 urban), incremental per timestep
- **Spatial weighting**: `flood_weight = exp(-3 × elev_norm)` — low areas get ~5× more water
- **Drainage factor**: 5%–50% reduction based on elevation (valleys = overwhelmed drains)
- **2D routing**: Diffusion-wave cellular automata, 4-connectivity, 5 sub-steps/timestep
- **Output**: `depth_history` list of 2D float grids, values in meters

---

## Frontend Critical Implementation Notes (`MapDashboard.tsx`)

### Feature ID Fix — MUST have id in BOTH places
MapLibre `setFeatureState` with `promoteId: 'id'` requires `id` in **feature.properties**,
not just at the feature top level:

```javascript
// CORRECT
features.push({ type: "Feature", id: id, properties: { id: id, row: r, col: c } });

// WRONG — setFeatureState will silently fail, no water visible
features.push({ type: "Feature", id: id++, properties: { row: r, col: c } });
```

Same for roads and buildings:
```javascript
roadsData.features = roadsData.features.map((f, idx) => ({
  ...f, id: idx, properties: { ...f.properties, id: idx }
}));
```

### Water Layer Paint
- Source: `terrain-grid` GeoJSON with `promoteId: 'id'`
- Layer: `water-layer` fill driven by `feature-state.water_depth`
- Opacity data-driven: 0 (dry) → 0.92 (1m+ depth) so shallow cells remain semi-transparent
- Color: transparent → sky-blue (0.001m) → navy (2.5m+)

### Map Init
- Center: auto-computed from DEM transform midpoint
- Zoom: 11 (covers full 200×200 Mumbai extent)
- Style: CartoDB Dark Matter

---

## Known Issues & Fixes Applied

| Issue | Root Cause | Fix Applied |
|---|---|---|
| Tiny rectangle grid in corner | Old 100×100 fallback at lon=72.85 in terrain.py | Updated terrain.py fallback to 200×200 at full Mumbai extent |
| No water visible after simulation | `promoteId:'id'` needs id in properties, not just feature.id | Added `id` to properties in generateGridGeoJSON and road/building mapping |
| Solid blue block (uniform flood) | Uniform rainfall adds same water to every cell | Added elevation-based flood_weight + drainage_factor in flood.py |
| Water invisible for light rain | Old 0.05m threshold too high | Lowered visibility to 0.001m in water-layer interpolation |
| Backend serving old code | Server not restarted after Python file changes | Kill old process, run: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 |
| Browser showing old JS bundle | Browser cache | Hard refresh Ctrl+Shift+R or navigate to new ?nocache=N URL |

---

## Dependencies — rasterio and geopandas NOT installed

All GIS operations use pure Python/numpy fallbacks.

Python: fastapi, uvicorn, numpy, pydantic (rasterio/geopandas missing — use fallbacks)
Frontend: React + TypeScript + MapLibre GL JS + Vite + lucide-react + Tailwind CSS

---

## Strategic Focus & Test Area Recommendation

To ensure numerical stability and evidence-based calibration, development will focus on a **1 km × 1 km test block** around **Kurla / Sion / Bandra-Kurla Complex (BKC) and the Mithi River** before scaling to the entire 200 × 200 Greater Mumbai grid.
* Center Coordinates: Lon = 72.865, Lat = 19.060 (approximate BKC center).
* Key features: Tidally influenced Mithi river boundary, dense urban terrain, high flooding history.
* Scaling strategy: 1 km × 1 km $\rightarrow$ 5 km × 5 km $\rightarrow$ 25 km × 25 km $\rightarrow$ Full Greater Mumbai.

---

## Sprint 2: Terrain Engine — Current Status & Next Steps

### Accomplished Today:
1. **Algorithms Refactored:** Added `compute_slope_percent`, `compute_flow_direction_d8_all` (with compass angle and downstream indices), and `delineate_watershed` using non-recursive BFS.
2. **Synthetic & Golden Datasets:** Created `synthetic_generator.py` and generated/saved analytical golden benchmark `.npz` files inside `benchmarks/golden/` for flat, uniform slope, hill, valley, and watershed geometries.
3. **Caching & Loading:** Implemented `TerrainCache` (saves grids to disk) and `TerrainLoader` (resolves synthetic references automatically).
4. **Verification & Exporting:** Integrated NaN, Inf, and D8 code checks prior to engine caching. Developed `visualizer.py` supporting optional `matplotlib` and `rasterio` PNG/TIFF/stats outputs.
5. **Testing Framework:** Created `tests/test_terrain.py` checking golden reference tolerances, watershed boundaries, and performance regression constraints (<0.2s for 100x100, <2s for 500x500, <8s for 1000x1000).

### Remaining Tasks for Tomorrow:
1. **Fix Test Failures:**
   - Debug and align computed outputs vs. analytical/calculated golden keys in `test_golden_datasets_tolerances` (verify if key differences exist between flow direction/accumulation formats in `.npz` vs computed ones).
   - Investigate BFS return comparison issue in `test_delineate_watershed` (`assert np.True_ is True` type conversion error).
2. **Integrate with API:** Ensure `/api/terrain/grid` works flawlessly with the new TerrainEngine.
3. **Run Performance/Memory Regressions:** Perform final evidence validation.
