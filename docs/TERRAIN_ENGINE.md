# Terrain Engine — Architectural Specifications & Policies

This document outlines the architectural assumptions, validation rules, dataset identification strategies, and regression testing policies for the Mumbai Flood Digital Twin Terrain Engine.

---

## 1. Affine Transform Assumptions & Validation

The Terrain Engine processes 2D grid cell elevation data. All spatial mapping from grid coordinates (row, col) to real-world coordinates is defined by the affine transform:

$$ X = a \cdot col + b \cdot row + c $$
$$ Y = d \cdot col + e \cdot row + f $$

In order to ensure physical correctness and numerical stability for isotropic 2D routing, the following validation constraints are enforced on the transform `[a, b, c, d, e, f]`:

* **No Rotation or Skew**: Rotation/skew coefficients `b` and `d` must be exactly `0.0` (with a tolerance of `1e-7`). Rotated or skewed rasters are rejected with a `TerrainException`.
* **Standard Grid Orientation**: Pixel width `a` must be strictly positive, and pixel height `e` must be strictly negative (standard North-up grid).
* **Isotropic Cell Size**:
  * **Geographic CRS** (e.g., geographic coordinates in degrees, detected when pixel width/height is `< 0.1`): The engine enforces that the degree aspect ratio `width/height` lies within `[0.2, 5.0]` to prevent extreme grid distortion. The actual horizontal grid cell size in meters is set to the isotropic default of `settings.cell_size_m` (`30.0` meters).
  * **Projected CRS** (e.g., UTM coordinates in meters, detected when pixel width/height is `>= 0.1`): The cell width `a` and cell height `abs(e)` must be equal within a `1%` tolerance. The isotropic cell size is calculated as the average of the two: `(width + height) / 2.0` to avoid bias.

---

## 2. Dataset Identity Strategy

To prevent caching conflicts and safely identify cached intermediate products (slope, aspect, flow direction/accumulation, hillshade), each terrain dataset is assigned a unique 16-character SHA256 hash. The hash is computed from the following attributes:

1. **Raster Dimensions**: Width and height of the grid.
2. **Coordinate Reference System (CRS)**: Full CRS string representation.
3. **Affine Transform**: Coefficients formatted to 8 decimal places.
4. **NoData Value**: The value representing nodata cells.
5. **Data Type**: System data type (e.g., `float32`).
6. **Source File Path**: Path from which the dataset was loaded.
7. **Elevation Checksum**: SHA256 hash of the raw elevation byte array.

Any change to any of these attributes will generate a different hash, ensuring absolute cache safety.

---

## 3. Golden Dataset Policy

Golden datasets inside `benchmarks/golden/` serve as the absolute baseline for algorithm correctness.

* **No Modification**: Golden reference datasets must **never** be edited or modified to bypass failing test cases.
* **Troubleshooting Failures**:
  * Verify the mathematical and scientific correctness of the algorithm.
  * Verify the correctness of the analytical benchmark representation.
  * Only regenerate the golden outputs if a scientific error is identified in the codebase and the correction of that error is explicitly approved.
* **Regeneration Process**: Run the synthetic generator module to refresh golden benchmarks when an approved algorithm change is implemented:
  ```powershell
  python -m simulation.terrain.synthetic_generator
  ```

---

## 4. Numerical Tolerance Policy

To maintain test auditability, all numerical comparison tolerances are centralized in [tolerances.py](file:///c:/Users/Hitesh/Desktop/mumbai-flood-digital-twin/tests/tolerances.py). Hardcoding tolerances in individual test files is strictly forbidden.

* **Elevation Grid Matching**: Relative tolerance `ELEVATION_RTOL = 1e-05`, Absolute tolerance `ELEVATION_ATOL = 1e-08`.
* **Slope Degree**: `SLOPE_DEG_TOLERANCE = 0.01` degrees.
* **Slope Percent**: `SLOPE_PCT_TOLERANCE = 0.5` percent.
* **Aspect Degree**: `ASPECT_DEG_TOLERANCE = 0.5` degrees.
