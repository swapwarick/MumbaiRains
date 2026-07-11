# Mumbai Flood Digital Twin Frontend

This frontend replaces the prototype dashboard with a GIS workstation surface for operators, researchers, and executive reviews.

## Structure

- `src/components/workstation` contains the command bar, docks, map viewport, timeline, command palette, and notifications.
- `src/features/digitalTwin` contains typed domain models, API adapters, metric derivation, scenario catalogs, and raster rendering utilities.
- `src/state/workspace.ts` stores persistent layout state, visible layers, active overlay, 3D mode, workspace mode, and command palette state.

## Rendering Model

- MapLibre GL is the primary renderer for the Mumbai basemap, camera, vector infrastructure layers, and WebGL raster compositing.
- The render order is basemap, DEM hillshade, terrain raster, flood depth raster, roads, buildings, waterways, inspector, and UI panels.
- Terrain and flood surfaces are rendered as canvas-backed image sources, then uploaded to MapLibre as raster layers.
- Flood depth uses bilinear sampling and a continuous depth color ramp: transparent, light blue, blue, cyan, yellow, orange, red, dark red.
- Simulation playback updates the active water image source rather than drawing individual grid cells.
- 3D mode stays inside MapLibre by tilting the same map and extruding buildings.

## Workspace Modes

- Operator mode keeps core simulation controls and monitoring visible.
- Research mode exposes diagnostics, profiler, inspector, and mass balance panels.
- Executive mode collapses side docks for a presentation-first large-map view.

## Backend Boundary

The frontend continues to consume the existing endpoints:

- `GET /api/terrain`
- `GET /api/roads`
- `GET /api/buildings`
- `GET /api/waterways`
- `POST /api/simulation/run`
- `POST /api/simulation/reset`

No backend or simulation algorithm changes are required.

## Local Development

Vite proxies `/api` requests to `http://127.0.0.1:8000`. The frontend expects the FastAPI backend to provide real terrain, road, building, waterway, and simulation responses from the project data sources. It does not generate replacement GIS geometry.