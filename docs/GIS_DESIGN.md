# GIS Foundation Design Document — Sprint 1

This document governs the design, public APIs, geometries, and raster processing guidelines of the GIS Foundation module (`simulation/gis/`).

## 1. Module Responsibilities

The GIS Foundation acts as the primary data model layer for all spatial inputs to the Digital Twin. It abstracts data ingestion, coordinate operations, and metadata tracking from the physical simulation engine:

* **Strongly Typed Metadata Model:** Replaces unstructured dict payloads with verified dataclass models (`LayerMetadata`).
* **Authoritative Dataset Catalog:** Registers, removes, gets, and validates datasets using a unified, strongly typed schema (`DatasetCatalog`).
* **Format Agnosticism:** Ingests multiple spatial GIS formats (GeoTIFF, GeoPackage, GeoJSON, and Shapefile).
* **Robust CRS & Coordinate Transformations:** Resolves coordinates, validates projection codes, suggests regional UTM projected grids, and calculates safe geodetic distance/area measurements without hardcoding EPSG values (`CRSManager`).
* **Tile-Based Loading:** Dynamically reads XYZ map tile raster chunks on-the-fly (`read_tile()`), ensuring the system never loads a massive raster completely into memory unless requested.
* **Multiband Raster Support:** Prepared for multiband raster reading (band count, band read, multi-band read, overview downsampling, histograms).
* **Explicit Geometry Repair:** Audits geometry topology and validation without mutating original geometries. Repairs are only executed when explicitly requested by the caller and generate comprehensive audit reports.
* **Mask Generation Factory:** Rasterizes OSM vector features to create aligned binary grids matching the DEM layout (`MaskFactory`).
* **Dataset Immutability Wrapper:** Wraps layers to prevent in-place modifications and trace parent-child data lineage.
* **Structured Validation Reports:** Audits datasets to produce standardized, machine-readable validation summary objects.
* **Stateful Provenance Contexts:** Manages independent simulation execution tracking without global shared state.

---

## 2. Public API Reference

### `BaseLayer` (Abstract Base Class)
* `name`: Layer name identifier.
* `crs`: Coordinate Reference System string.
* `bounds`: Bounding box tuple (xmin, ymin, xmax, ymax).
* `metadata`: Strongly typed `LayerMetadata` model instance.
* `validate()`: Performs validation and returns a `ValidationReport`.

### `RasterLayer` (Inherits from `BaseLayer`)
* `shape`: Row and column bounds tuple.
* `transform`: 6-parameter affine transform array.
* `resolution`: Cell resolution tuple.
* `nodata`: NoData marker value.
* `band_count`: Returns total band count in the raster file.
* `read_band(band_idx)`: Reads a single band array.
* `read_bands(band_indices)`: Reads multiple bands simultaneously.
* `read_window(window_bounds, band_idx)`: Reads a cropped NumPy grid from disk using bounds.
* `read_tile(tile_x, tile_y, zoom, tile_size, band_idx)`: Reads an XYZ web mapping tile raster window.
* `statistics(band_idx, grid_data)`: Computes min/max/mean/std.
* `histogram(band_idx, bins)`: Returns values distribution histogram.
* `nodata_mask(band_idx)`: Returns a boolean mask representing NoData values.
* `overview_levels(band_idx)`: Returns downsampling scales.

### `VectorLayer` (Inherits from `BaseLayer`)
* `features`: List of GeoJSON features.
* `spatial_index`: STRtree R-tree spatial index instance.
* `build_spatial_index()`: Builds R-tree index over geometries.

### `LayerMetadata` (Dataclass)
* Strongly typed metadata model containing:
  * `name`, `description`, `source`, `crs`, `extent`, `resolution`, `bands`, `dtype`, `nodata`, `created_at`, `updated_at`.

### `DatasetCatalog`
* `register_dataset(dataset_metadata)`: Registers a dataset.
* `remove_dataset(dataset_id)`: Removes a dataset.
* `get_dataset(dataset_id)`: Retrieves a cataloged dataset's metadata.
* `list_datasets()`: Returns all cataloged datasets.
* `validate_dataset(dataset_id)`: Performs disk path, CRS, and extent alignment checks.

### `CRSManager`
* `validate_crs(crs_string)`: Checks if a projection code is valid.
* `compare_crs(crs_a, crs_b)`: Compares two coordinate reference systems.
* `transform_coordinates(x, y, source, target)`: Transforms a coordinate pair.
* `suggest_projected_crs(lon, lat)`: Computes local UTM zone projected coordinate system.
* `calculate_distance(coord1, coord2, crs)`: Calculates geodetic distance.
* `calculate_area(coords, crs)`: Calculates polygon area.

### `geometry_repair`
* `repair_geometry(geojson_feature, geometry_id, repair_requested=False)`: Evaluates geometry topology. Returns a repaired copy if `repair_requested=True`, plus a `GeometryRepairReport` containing before/after areas, original errors, and change status.

### `MaskFactory`
* `generate_road_mask(roads, template)`: Generates binary grid of roads.
* `generate_building_mask(buildings, template)`: Generates binary grid of buildings.
* `generate_waterway_mask(waterways, template)`: Generates binary grid of rivers.
* `generate_vegetation_mask(vegetation, template)`: Generates binary grid of vegetation.
* `generate_impervious_mask(road_mask, building_mask, extra_concrete_mask)`: Generates combined impervious surface grid.

### `ProvenanceContext`
* State container tracking a single simulation execution, its parameters, warnings, errors, processing steps (`AuditRecord`), and exports. Supports concurrent runs.

### `ImmutableDataset`
* Wraps spatial layers to guarantee immutability. Derived datasets are generated via `.derive()`, tracking parent-child relationships for processing steps.

### `ValidationReport`
* Dataclass reporting CRS status, geometry status, raster alignment, NoData statistics, extent, resolution, warnings, errors, and validation result (bool).

---

## 3. Core Scientific Principles

### 3.1 Prohibiting Automatic Geometry Repair
Automatic, silent geometry repair is dangerous in research-grade scientific software because it hides topological errors in source GIS data (e.g., self-intersecting boundaries, duplicate vertices). 
* In this digital twin, validation is **always** run.
* If a geometry is invalid, it is not modified unless `repair_requested=True` is explicitly specified by the caller.
* When repair is requested, the operation generates a `GeometryRepairReport` documenting the original validity error, repair method (e.g., `make_valid`, `buffer(0)`), repair success status, area before/after repair, and whether the shape changed.
* Original datasets remain immutable.

### 3.2 Prohibiting Approximate Rasterization Fallbacks
Graceful degradation through centroid-based approximation masks spatial details and yields incorrect runoff and river routing grids. 
* If required binary dependencies (`rasterio`, `geopandas`, or `shapely`) are missing, the system will **never** silently fall back to centroid approximations.
* Instead, it raises a `MissingSpatialDependencyError` describing the missing library, installation command, and affected flood twin functionality.
* Scientific correctness and consistency are prioritized over graceful silent degradation.

### 3.3 Stateless Provenance Contexts
To support multiple simultaneous simulation runs and prevent data leakage, global singleton provenance trackers are prohibited.
* Each simulation execution instantiates a unique `ProvenanceContext`.
* This context records its own unique simulation ID, configuration parameters, input dataset versions, warning and error logs, and export paths.
* It captures structured `AuditRecord` entries for every GIS operation (operation name, input/output names, parameters, duration, tool versions).

### 3.4 Reproducibility via Immutable Datasets
To guarantee reproducibility, loaded datasets are never overwritten or modified in place.
* Every loaded layer is wrapped in an `ImmutableDataset`.
* Any geoprocessing step (e.g., clipping, filling depressions, calculating slope) must return a *new* derived `ImmutableDataset`.
* Parent-child relationships are tracked natively (`parent` and `children` properties), allowing callers to trace the lineage path leading to any computational grid via `.get_lineage_path()`.

---

## 4. Tile Loading & Memory Safety
Rasters are loaded lazily. If specific map tiles or coordinates are queried, `read_tile()` calculates the Web Mercator projection bounds of the XYZ tile, maps it to the geographic raster coordinates, and reads *only* that cropped grid using rasterio's windowed reads (`read_window`). This ensures the digital twin is memory-safe and scalable for gigabyte-scale datasets.
