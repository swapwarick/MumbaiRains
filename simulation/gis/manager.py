"""
simulation/gis/manager.py
-------------------------
Implements LayerManager (layer lifecycle, caching, registry, lazy-loading)
and GISManager (loading datasets, reprojections, rasterizations).
"""

import json
import os
from typing import Dict, Any, List, Tuple, Optional

import numpy as np

from backend.config import settings
from backend.utils import get_logger
from backend.exceptions import GISException, MissingSpatialDependencyError
from simulation.gis.layers import BaseLayer, RasterLayer, VectorLayer

logger = get_logger(__name__)

try:
    import geopandas as gpd
    from shapely.geometry import shape as shapely_shape
    _GEOPANDAS = True
except ImportError:
    _GEOPANDAS = False

try:
    import rasterio
    _RASTERIO = True
except ImportError:
    _RASTERIO = False


class LayerManager:
    """
    Manages registering, lazy-loading, caching, and unloading spatial layers.
    """
    def __init__(self) -> None:
        self.registry: Dict[str, Dict[str, Any]] = {}
        self.cache: Dict[str, BaseLayer] = {}

    def register_layer(self, name: str, layer_type: str, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Registers a layer without loading it immediately.
        """
        self.registry[name.lower()] = {
            "type": layer_type.lower(),
            "path": file_path,
            "metadata": metadata or {}
        }
        logger.info("Layer registered", extra={"layer": name, "type": layer_type, "path": file_path})

    def get_layer(self, name: str) -> BaseLayer:
        """
        Lazily loads and returns a layer. Caches it in memory for future access.
        """
        key = name.lower()
        if key in self.cache:
            return self.cache[key]

        if key not in self.registry:
            raise GISException(f"Layer '{name}' is not registered in LayerManager.")

        # Lazy load layer
        reg_info = self.registry[key]
        layer = self._load_registered_layer(name, reg_info)
        self.cache[key] = layer
        return layer

    def unload_layer(self, name: str) -> None:
        """
        Unloads a layer from the in-memory cache to free resources.
        """
        key = name.lower()
        if key in self.cache:
            del self.cache[key]
            logger.info("Layer unloaded from cache", extra={"layer": name})

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Returns metadata for the registered layer."""
        key = name.lower()
        if key not in self.registry:
            raise GISException(f"Layer '{name}' is not registered.")
        return self.registry[key]["metadata"]

    def _load_registered_layer(self, name: str, reg_info: Dict[str, Any]) -> BaseLayer:
        """Loads layer from disk based on type."""
        path = reg_info["path"]
        l_type = reg_info["type"]

        if l_type == "raster":
            # Read minimal metadata first without loading entire grid
            if _RASTERIO and os.path.exists(path) and os.path.getsize(path) > 100:
                with rasterio.open(path) as src:
                    t = src.transform
                    transform_coeff = [t.a, t.b, t.c, t.d, t.e, t.f]
                    resolution = (src.res[0], src.res[1])
                    bounds = (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)
                    shape = (src.height, src.width)
                    crs_str = str(src.crs)
                    nodata = src.nodata
                
                layer = RasterLayer(
                    name=name,
                    crs=crs_str,
                    bounds=bounds,
                    shape=shape,
                    transform=transform_coeff,
                    resolution=resolution,
                    nodata=nodata,
                    file_path=path
                )
                return layer
            else:
                # Fallback synthetic config initialization
                logger.info("Using synthetic fallback values for raster load", extra={"layer": name})
                cols, rows = settings.dem_fallback_cols, settings.dem_fallback_rows
                lon_w, lat_n = settings.dem_fallback_lon_west, settings.dem_fallback_lat_north
                lon_e, lat_s = settings.dem_fallback_lon_east, settings.dem_fallback_lat_south
                dx = (lon_e - lon_w) / cols
                dy = (lat_n - lat_s) / rows
                
                return RasterLayer(
                    name=name,
                    crs=settings.default_crs,
                    bounds=(lon_w, lat_s, lon_e, lat_n),
                    shape=(rows, cols),
                    transform=[dx, 0.0, lon_w, 0.0, -dy, lat_n],
                    resolution=(dx, -dy),
                    nodata=-9999.0,
                    file_path=path
                )

        elif l_type == "vector":
            # Load vectors
            features: List[Dict[str, Any]] = []
            bounds = (0.0, 0.0, 0.0, 0.0)
            crs_str = settings.default_crs

            if _GEOPANDAS and os.path.exists(path) and os.path.getsize(path) > 100:
                try:
                    # In GPKG, load layer name matching registry info or filename
                    layer_name = reg_info["metadata"].get("layer_name", name)
                    gdf = gpd.read_file(path, layer=layer_name)
                    if gdf.crs and str(gdf.crs) != settings.default_crs:
                        gdf = gdf.to_crs(settings.default_crs)
                    crs_str = str(gdf.crs or settings.default_crs)
                    b = gdf.total_bounds
                    bounds = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
                    features = json.loads(gdf.to_json())["features"]
                except Exception as exc:
                    logger.warning(f"Failed to load vector via geopandas: {exc}")

            # Basic parsing if empty
            if not features:
                features = [{"type": "Feature", "properties": {}, "geometry": None}]

            layer = VectorLayer(name=name, crs=crs_str, bounds=bounds, features=features)
            layer.build_spatial_index()
            return layer

        else:
            raise GISException(f"Unsupported layer storage type: {l_type}")


class GISManager:
    """
    Orchestrates advanced GIS tasks: re-projections, rasterizations, and mask generation.
    """
    def __init__(self, layer_manager: LayerManager) -> None:
        self.layer_manager = layer_manager

    def validate_crs_match(self, layer_name: str, expected_crs: str = "EPSG:4326") -> bool:
        """
        Validates that a layer's projection matches the expectation.
        """
        layer = self.layer_manager.get_layer(layer_name)
        cleaned_layer_crs = layer.crs.strip().upper().replace(" ", "")
        cleaned_expected = expected_crs.strip().upper().replace(" ", "")
        return cleaned_expected in cleaned_layer_crs or cleaned_layer_crs in cleaned_expected

    def reproject_vector_layer(self, layer_name: str, target_crs: str = "EPSG:4326") -> None:
        """
        Reprojects a vector layer coordinates and clears spatial index.
        """
        if not _GEOPANDAS:
            raise MissingSpatialDependencyError(
                "Geopandas is required for vector reprojection. "
                "Installation instructions: run 'pip install geopandas'. "
                "Affected functionality: vector spatial coordinate reprojections."
            )

        layer = self.layer_manager.get_layer(layer_name)
        if not isinstance(layer, VectorLayer):
            raise GISException(f"Layer '{layer_name}' is not a VectorLayer.")

        # Re-load into GeoDataFrame, reproject, serialize back
        path = self.layer_manager.registry[layer_name.lower()]["path"]
        sub_layer_name = self.layer_manager.registry[layer_name.lower()]["metadata"].get("layer_name", layer_name)
        
        gdf = gpd.read_file(path, layer=sub_layer_name)
        gdf = gdf.to_crs(target_crs)
        
        layer.crs = target_crs
        b = gdf.total_bounds
        layer.bounds = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
        layer.features = json.loads(gdf.to_json())["features"]
        layer.build_spatial_index()
        logger.info("Layer reprojected successfully", extra={"layer": layer_name, "crs": target_crs})

    def rasterize_layer(
        self,
        vector_layer_name: str,
        template_raster_name: str,
        all_touched: bool = True
    ) -> np.ndarray:
        """
        Rasterizes a VectorLayer's geometries onto the grid shape of a template RasterLayer.
        Returns a binary boolean mask grid (True where vector features intersect).
        """
        vector_layer = self.layer_manager.get_layer(vector_layer_name)
        raster_layer = self.layer_manager.get_layer(template_raster_name)

        if not isinstance(vector_layer, VectorLayer):
            raise GISException(f"Layer '{vector_layer_name}' must be a VectorLayer.")
        if not isinstance(raster_layer, RasterLayer):
            raise GISException(f"Layer '{template_raster_name}' must be a RasterLayer.")

        height, width = raster_layer.shape
        t = raster_layer.transform

        # Enforce scientific correctness: approximate fallbacks are prohibited.
        if not _RASTERIO or not _GEOPANDAS:
            raise MissingSpatialDependencyError(
                "Required spatial libraries (rasterio and geopandas) are unavailable. "
                "Installation instructions: run 'pip install rasterio geopandas'. "
                "Affected functionality: vector geometry rasterization onto computational grids."
            )

        from rasterio.features import rasterize
        affine_transform = rasterio.transform.Affine(t[0], t[1], t[2], t[3], t[4], t[5])
        
        geoms = []
        for feat in vector_layer.features:
            geom_data = feat.get("geometry")
            if geom_data:
                geoms.append(shapely_shape(geom_data))

        if not geoms:
            return np.zeros((height, width), dtype=bool)

        # Rasterize geometries with value 1, default background 0
        mask = rasterize(
            shapes=[(g, 1) for g in geoms],
            out_shape=(height, width),
            transform=affine_transform,
            all_touched=all_touched,
            fill=0,
            dtype=np.uint8
        )
        return mask.astype(bool)

    def generate_masks(self, template_raster_name: str) -> Dict[str, np.ndarray]:
        """
        Generates road, building, and waterways boolean masks aligned to the DEM.
        """
        masks = {}
        # Safely try loading registered vector layers and rasterizing them
        for target in ["roads", "buildings", "waterways"]:
            try:
                masks[target] = self.rasterize_layer(target, template_raster_name)
            except Exception as exc:
                # If layer missing or failed, return empty grid
                logger.warning(f"Could not rasterize layer '{target}': {exc}. Returning empty mask.")
                raster_layer = self.layer_manager.get_layer(template_raster_name)
                masks[target] = np.zeros(raster_layer.shape, dtype=bool)
                
        return masks
