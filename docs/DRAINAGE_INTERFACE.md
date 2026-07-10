# Drainage Interface — Algorithmic & Architectural Specifications

This document outlines the architecture, data models, DEM-to-inlet spatial mapping, and public APIs of the `DrainageInterfaceEngine` (Sprint 5).

---

## 1. Architecture & Design Principles

The Drainage Interface serves as the structural link between the **2D Surface Flow Grid** and the **1D Sub-Surface Hydraulic Network**.

```
+------------------------------------+
|         2D Surface Grid            |
|  (Water depth, Overland flow, CN)  |
+-----------------+------------------+
                  |
                  | (DEM-to-inlet mapping lookup table)
                  v
+-----------------+------------------+
|      DrainageInterfaceEngine       |  <-- Computes available capacities & intakes
+-----------------+------------------+
                  |
                  | (Map inlet to connected_node_id)
                  v
+-----------------+------------------+
|      1D Hydraulic Network          |
|  (Graph nodes: INLET, JUNC, etc.)  |
+------------------------------------+
```

The Drainage Interface does **not** route or move water within pipes or channels. Instead, its role is to:
1. Identify how much surface water is sitting on grid cells associated with each inlet.
2. Verify if the inlet has available flow capacity ($Q_{\text{max}} \times \Delta t$).
3. Remove water from the surface grid and track the volume of water injected into the network.

---

## 2. Public API Specification

### `DrainInlet`
A data structure representing a physical street grate or drain inlet:
* `id` (str): Unique inlet identifier.
* `row` (int), `col` (int): Grid coordinates.
* `elevation` (float): Surface elevation at the grate.
* `capacity_m3_s` (float): Maximum volumetric intake rate ($m^3/s$).
* `invert_level` (float): Elevation of the pipe/conduit connection.
* `blocked` (bool): If `True`, capacity is set to `0.0`.
* `connected_node_id` (str): Target graph node ID in the Hydraulic Network.

### `DrainageInterfaceEngine`
* `__init__(inlets: List[DrainInlet], max_search_radius_m: float = 100.0)`: Initializes the engine.
* `associate_grid(rows: int, cols: int, transform: List[float]) -> np.ndarray`: Associates every cell on the DEM grid to the nearest inlet within `max_search_radius_m`. Returns a 2D array of associated inlet IDs (empty string if no inlet is in range).
* `apply_inlet_intake(water_depth_grid: np.ndarray, cell_area: float, dt: float) -> Tuple[np.ndarray, Dict[str, float], np.ndarray]`: Computes available capacities, drains the surface cells, and returns the updated depth grid and intake report.
* `get_statistics(timestep: int) -> DrainageInterfaceReport`: Returns an audit of the inlets (blocked counts, total capacities, coverage, spacing).

---

## 3. DEM-to-Inlet Mapping & Grouping

To map grid cells to inlets efficiently:
* Spatial coordinates $(x, y)$ of cell centers are computed from grid indices $(r, c)$ using the affine transform.
* SciPy's `KDTree` queries the nearest inlet for each coordinate.
* A distance filter rejects associations beyond the configured `max_search_radius_m`.

### Volumetric Grouping & Allocation
When applying intake, multiple cells may be associated with the same inlet. To prevent draining more water than the inlet capacity allows:
1. Available volumes are summed for all cells sharing an inlet `I`:
   $$ V_{\text{available}} = \sum_{(r, c) \in S_I} \text{depth}[r, c] \times \text{cell\_area} $$
2. The actual intake is limited by the step capacity:
   $$ V_{\text{intake}} = \min(V_{\text{available}}, I.\text{capacity\_m3\_s} \times \Delta t) $$
3. If $V_{\text{intake}} < V_{\text{available}}$, cells are drained proportionally to their depth:
   $$ \text{depth}_{\text{new}}[r, c] = \text{depth}[r, c] \times \left(1 - \frac{V_{\text{intake}}}{V_{\text{available}}}\right) $$

This ensures perfect mass conservation.

---

## 4. Known Limitations
* **Static Inlets**: Inlets are assumed to have fixed grid coordinates and static capacities.
* **Proportional Drainage**: Draining cells proportionally does not account for micro-topography within the associated catchment area.
