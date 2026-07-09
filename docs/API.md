# API Reference — Mumbai Flood Digital Twin

Base URL: `http://127.0.0.1:8000`

## Terrain Endpoints

### `GET /api/terrain`
Returns all terrain layers as nested arrays (backward-compatible).

**Response**
```json
{
  "width": 200,
  "height": 200,
  "crs": "EPSG:4326",
  "transform": [0.00095, 0.0, 72.80, 0.0, -0.0019, 19.27],
  "elevation": [[...200 rows of 200 floats...]],
  "slope": [[...]],
  "aspect": [[...]],
  "flow_direction": [[...]],
  "flow_accumulation": [[...]]
}
```

### `GET /api/terrain/metadata`
Returns lightweight metadata only — no raster arrays.

**Response**
```json
{
  "width": 200,
  "height": 200,
  "crs": "EPSG:4326",
  "transform": [...],
  "bounds": {"west": 72.80, "east": 72.99, "south": 18.89, "north": 19.27},
  "stats": {
    "elevation": {"min": 0.5, "max": 92.0, "mean": 18.3, "std": 14.2},
    "slope": {"min": 0.0, "max": 45.0, "mean": 8.1, "std": 6.3}
  }
}
```

## GIS Layer Endpoints

### `GET /api/roads`
### `GET /api/buildings`
### `GET /api/waterways`

All return a GeoJSON FeatureCollection in EPSG:4326.

## Simulation Endpoints

### `GET /api/simulation/status`
```json
{"status": "ready", "simulation_phase": 2, "message": "..."}
```

### `POST /api/simulation/run`
**Request Body**
```json
{
  "duration_hours": 4,
  "intensity_mm_hr": 50.0,
  "time_step_min": 15,
  "rainfall_mode": "constant"
}
```

**rainfall_mode values:**
- `"constant"` — uniform intensity (default)
- `"synthetic"` — Alternating Block Method
- `"historical"` — not yet implemented (Phase 3)

**Response**
```json
{
  "metadata": {
    "width": 200, "height": 200,
    "crs": "EPSG:4326",
    "transform": [...]
  },
  "time_steps_min": 15,
  "rainfall_hyetograph_mm": [12.5, 12.5, ...],
  "depth_history": [
    [[0.0, 0.0, ...], ...],
    [[0.001, 0.002, ...], ...]
  ]
}
```

### `POST /api/simulation/reset`
```json
{"status": "success", "message": "Simulation states reset successfully."}
```

### `GET /api/simulation/rainfall/modes`
Lists available rainfall modes with descriptions.

## Error Format

All errors return:
```json
{"detail": "Human-readable error message"}
```

HTTP codes:
- `500` — server-side error (TerrainException, SimulationException, etc.)
- `422` — validation error (invalid request body field)
