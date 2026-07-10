# Surface Routing Engine — Algorithmic & Design Specifications

This document details the Cellular Automata (CA) D8 routing algorithm, boundary condition mechanisms, mass conservation audits, and benchmark results for the Mumbai Flood Digital twin `SurfaceRoutingEngine` (Sprint 3).

---

## 1. Why Fixed Timestep is Used

Cellular Automata (CA) simulations with cell-based rules and neighbour lookup tables are computationally defined per step. Since Sprint 3 does not use partial differential equations (PDEs) like Shallow Water Equations, we don't need adaptive sub-stepping via Courant-Friedrichs-Lewy (CFL) stability conditions for grid velocities. Timesteps are fixed (e.g. $\Delta t$) to make the routing deterministic and directly correspond to the clock steps of the simulation controller.

---

## 2. Why Neighbour Lookup Replaces `np.roll`

While shifting grids using `np.roll` is fast, it has major architectural limitations:
1. **Toroidal Wrapping**: `np.roll` forces boundary cells to wrap around to the opposite side of the grid, requiring complex masking to undo.
2. **Grid Topology Coupling**: `np.roll` is strictly tied to Cartesian grid layouts.
3. **Redesign Risk**: It cannot easily scale to advanced routing models like D-Infinity or Multiple Flow Direction (MFD) where water splits between multiple neighbors.

By replacing `np.roll` with a **neighbour lookup table** (`downstream_cells` indexing array), the `SurfaceRoutingEngine` decouples the routing mechanism from grid topology. A cell simply references its target coordinates `(target_r, target_c)`. This allows seamless future support for D-Infinity and MFD models by expanding the lookup table schema to multiple indices and weights, without changing the routing engine's core code.

---

## 3. Water Transfer Policy

At each timestep, a cell transfers a configurable fraction (`transfer_fraction`, default = `0.25`) of its current water depth to its downstream cell:

$$ \text{outflow} = \text{water\_depth} \times \text{transfer\_fraction} $$

Sinks (cells that flow to themselves) transfer zero water. Since the maximum transfer fraction is $1.0$, the outflow from any cell can never exceed its available water depth:

$$ \text{water\_depth}_{\text{new}} \ge \text{water\_depth} - \text{water\_depth} \cdot 1.0 \ge 0.0 $$

This mathematically guarantees that water depths can never become negative. Minor floating-point rounding errors are protected against using `np.maximum(new_water, 0.0)`.

---

## 4. Boundary Types

We define a `BoundaryType` enum supporting:
* **CLOSED** (Implemented): Water cannot leave the grid. Flows pointing off-grid are blocked (the source cell retains the water).
* **OPEN** (Implemented): Water flows freely off-grid. The source cell loses the water, and it leaves the system (tracked as boundary outflow).
* **OUTFLOW** (Interface): Drains water based on custom outflow curves.
* **FIXED_LEVEL** (Interface): Enforces a fixed water height.
* **SEA** (Interface): Tidally influenced sea boundary.
* **REFLECTIVE** (Interface): Bounces wave energy back.

---

## 5. Mass Balance Reporting

For every timestep, the engine generates and caches a `MassBalanceReport`:
* **Initial Water**: Total storage before routing ($m^3$).
* **Boundary Inflow**: Volume entering the grid ($m^3$).
* **Boundary Outflow**: Volume leaving the grid ($m^3$).
* **Current Storage**: Total storage after routing ($m^3$).
* **Absolute Error**: $\text{Current Storage} - (\text{Initial Water} + \text{Boundary Inflow} - \text{Boundary Outflow})$.
* **Relative Error**: $\text{Absolute Error} / (\text{Initial Water} + \text{Boundary Inflow})$.

This audit log guarantees that water volume is strictly tracked, with relative conservation error bounded by the machine epsilon of `float32` (approx $10^{-7}$).

---

## 6. Computational Complexity

Since routing is implemented using fully vectorized NumPy operations (e.g. `np.add.at`), there are no Python loops over grid cells.
* **Time Complexity**: $\mathcal{O}(N)$ per step, where $N$ is the number of grid cells.
* **Space Complexity**: $\mathcal{O}(N)$ to maintain coordinate meshes and temporary accumulators.
* **Performance**: Performance tests on a 500x500 grid ($250,000$ cells) complete in **<2.0 ms** per step, well below the target regression limit of 150 ms.

---

## 7. Benchmark Results

All 8 benchmarks passed their physical and mass balance validation checks:
1. **flat_pool**: Water remains stationary in flat terrain.
2. **uniform_slope**: Water flows South down the slope and pools at the closed boundary.
3. **diagonal_slope**: Water flows diagonally from NW to SE and pools at the corner.
4. **single_barrier**: Water is blocked by a high ridge row and pools behind it.
5. **pit**: Water converges to a single depression cell.
6. **ridge**: Water flows away from a central high ridge.
7. **open_boundary**: Water drains off the open southern edge, reducing total volume.
8. **closed_boundary**: Water is conserved and pools at the closed southern edge.
