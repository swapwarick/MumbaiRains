# Numerical Verification & Benchmark Framework

This document outlines the numerical verification, benchmark scenarios, calibration/validation layouts, and performance profiling guidelines established prior to Sprint 2.

---

## 1. Numerical Verification (`simulation/core/verification.py`)

To ensure computations remain physically consistent and free of structural errors (common in spatial flood models), the system implements runtime numerical audits:

* **No Negative Water Depth (`verify_no_negative_water_depth`):** Checks that no cell contains negative water heights. Negative depths indicate numerical instability (e.g. over-routing or stability violations).
* **Mass Conservation (`verify_mass_conservation`):** Audits total water balance:
  $$\text{Initial Volume} + \text{Cumulative Inflow} - \text{Cumulative Outflow} \approx \text{Current Volume}$$
  Permitted deviation threshold defaults to $1.0\%$.
* **Grid & DEM Integrity (`verify_grid_integrity`):** Audits input grid arrays for structural spikes, valid boundary values, and matching dimensions.
* **NaN & Infinite Checks (`verify_nan_values`):** Scan intermediate states to catch arithmetic faults (e.g., division by zero) before they propagate.
* **Timestep CFL Stability (`verify_timestep_stability`):** Computes Courant-Friedrichs-Lewy conditions dynamically to verify stability limits:
  $$\text{CFL} = \Delta t \left( \frac{|u|}{\Delta x} + \frac{|v|}{\Delta y} \right) \le 1.0$$
* **Flow Continuity (`verify_flow_balance`):** Confirms that change in grid storage over the timestep matches the net inflow rate minus net outflow rate.

---

## 2. Benchmark Framework (`benchmarks/`)

Before executing simulations across the full Mumbai topography, algorithms are verified against standardized test cases located in the `benchmarks/` directory:

1. **`simple_slope/`:** Verify gravity-driven flow routing on a constant linear slope.
2. **`flat_surface/`:** Verify static ponding and mass conservation on a flat surface.
3. **`single_building/`:** Verify flow diversion around a solid barrier block.
4. **`single_drain/`:** Verify water sink extraction at a point drain.
5. **`small_catchment/`:** Verify integrated runoff and flow accumulation on a synthetic sub-basin grid.
6. **`mumbai_test_block/`:** Real-world 1 km × 1 km DEM slice from Kurla/BKC.

---

## 3. Calibration & Validation Layouts

To evolve the simulator into a research-grade tool, observed data structures are partitioned:

* **Calibration (`calibration/`):** Contains observed rainfall hyetographs, flood depths, and drainage levels. Optimization algorithms adjust Curve Numbers ($CN$), Manning's roughness ($n$), and discharge capacities to minimize errors against real observations.
* **Validation (`validation/historical/`):** Holds historical storm runs (e.g., `2005/`, `2024/`, `2025/`) to validate optimized model predictions against independent historical flood extents.

---

## 4. Performance Profiling (`profiling/`)

Instrumenting code runs ensures optimizations are evidence-based. The performance profiler (`simulation/core/profiler.py`) tracks:
* **Execution Duration:** Real wall time of simulation steps.
* **Memory Footprint:** Growth and RSS allocation tracking.
* **Spatial operations:** Number of disk raster reads, vector/R-Tree queries, and tile cache hits.
* **CPU Load:** Processor utilization.

---

## 5. Strategic Focus: Kurla/BKC 1 km × 1 km Test Area

Simulating the entire Greater Mumbai grid introduces immense data calibration noise and slows down iterations.
We have selected a **1 km × 1 km test area** centered around **Kurla / Sion / Bandra-Kurla Complex (BKC) and the Mithi River** for model development.

### Reasons:
1. **Critical Flooding hotspot:** Kurla/BKC experiences severe, recurring monsoon flooding, making it the most heavily documented area in Mumbai.
2. **Mithi River boundary:** Houses the complex tidally-influenced river channel boundary, which is the primary driver of central suburb flooding.
3. **Ground Truth Data Availability:** Observed water levels and community flood maps are highly available for this corridor.
4. **Scale Progression:** 
   $$\text{1 km × 1 km (BKC)} \longrightarrow \text{5 km × 5 km} \longrightarrow \text{25 km × 25 km} \longrightarrow \text{Whole Mumbai}$$
