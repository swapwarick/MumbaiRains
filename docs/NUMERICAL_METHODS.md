# Numerical Methods Document — Mumbai Flood Digital Twin

This document details the numerical solvers, finite difference approximations, stability conditions, and array vectorization techniques used in the digital twin.

## 1. 2D Flow Routing Schemes

Overland flow can be mathematically solved using different numerical schemes:

* **Shallow Water Equations (2D Saint-Venant):**
  Uses a Finite Volume method with shock-capturing Godunov-type Riemann solvers to route conservation of mass and momentum. This is planned for Phase 3 to calculate flow velocities accurately.
* **Diffusive Wave Approximation:**
  Neglects the acceleration and inertia terms in the momentum equation. Flow is driven solely by the water surface slope (hydraulic gradient).
* **Cellular Automata (CA) Routing:**
  Approximates diffusive flow by exchanging volume between adjacent cells based on hydraulic head differences.

## 2. Vectorized 2D Diffusion CA

The `FlowRoutingEngine` implements a vectorized Cellular Automata diffusion solver using NumPy.

### Traditional nested loop (O(N²))
A cell-by-cell loop computes flows in 4 directions by querying neighbors:
```python
for r in range(rows):
    for c in range(cols):
        # calculate head difference with neighbours, then transfer volume
```
This is slow in Python, taking up to several seconds for a 200×200 grid.

### Vectorized array shifting (O(1) Python overhead)
We compute flow for the entire grid at once by shifting the hydraulic head matrix using `np.roll()`:
```python
# Shift matrix in 4 directions to bring neighbor head adjacent to center head
head = elevation + water_depth

flow_n = np.maximum(head - np.roll(head, -1, axis=0), 0.0) * diff_coeff * water_depth
# Similarly compute flow_s, flow_e, flow_w
```
This executes compiled C-level loops, reducing timestep computation time to milliseconds.

## 3. Stability Condition (CFL)

To prevent numerical oscillations (water transferring back and forth between cells, causing negative depths), the timestep must satisfy the **Courant-Friedrichs-Lewy (CFL)** condition:
$$C = \frac{v \cdot \Delta t}{\Delta x} \le C_{max}$$

For 2D grid diffusion, this requires:
$$\Delta t \le \frac{\Delta x^2}{4 \cdot D}$$
Where $D$ is the diffusion coefficient. We cap the local diffusion multiplier at `0.25` and limit the outflow per step to a maximum of 20% of the cell volume, guaranteeing that water depth never drops below zero.
