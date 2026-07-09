"""
simulation/gis/mask_factory.py
------------------------------
MaskFactory — creates boolean grid masks (roads, buildings, waterways, vegetation,
and impervious surfaces) aligned perfectly with the DEM raster grid.
"""

from typing import Dict, Any, List, Optional
import numpy as np

from backend.utils import get_logger
from backend.exceptions import MissingSpatialDependencyError
from simulation.gis.layers import RasterLayer, VectorLayer

logger = get_logger(__name__)

try:
    from shapely.geometry import shape as shapely_shape
    _SHAPELY = True
except ImportError:
    _SHAPELY = False

try:
    import rasterio
    _RASTERIO = True
except ImportError:
    _RASTERIO = False


class MaskFactory:
    """
    Factory for producing raster masks from vector spatial geometries,
    aligned to a reference RasterLayer grid.
    """
    
    @staticmethod
    def rasterize_vector(
        vector_layer: VectorLayer,
        template_raster: RasterLayer,
        all_touched: bool = True
    ) -> np.ndarray:
        """
        Rasterizes a vector layer onto the grid of the template raster.
        Enforces scientific correctness: approximate fallbacks are prohibited.

        Args:
            vector_layer: VectorLayer containing the geometries.
            template_raster: RasterLayer representing the alignment template.
            all_touched: If True, all cells touched by geometry are set to True.

        Returns:
            A 2D boolean array.
        """
        height, width = template_raster.shape
        t = template_raster.transform

        if not _RASTERIO or not _SHAPELY:
            raise MissingSpatialDependencyError(
                "Required spatial libraries (rasterio and shapely) are unavailable. "
                "Installation instructions: run 'pip install rasterio shapely'. "
                "Affected functionality: vector geometry rasterization in MaskFactory."
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

    def generate_road_mask(self, roads_layer: VectorLayer, template_raster: RasterLayer) -> np.ndarray:
        """Generates a road network boolean mask grid."""
        logger.info("Generating road mask")
        return self.rasterize_vector(roads_layer, template_raster, all_touched=True)

    def generate_building_mask(self, buildings_layer: VectorLayer, template_raster: RasterLayer) -> np.ndarray:
        """Generates a building footprint boolean mask grid."""
        logger.info("Generating building mask")
        return self.rasterize_vector(buildings_layer, template_raster, all_touched=True)

    def generate_waterway_mask(self, waterways_layer: VectorLayer, template_raster: RasterLayer) -> np.ndarray:
        """Generates a waterway (river/nullah) network boolean mask grid."""
        logger.info("Generating waterway mask")
        return self.rasterize_vector(waterways_layer, template_raster, all_touched=True)

    def generate_vegetation_mask(self, vegetation_layer: VectorLayer, template_raster: RasterLayer) -> np.ndarray:
        """Generates a vegetation (forest/grass) canopy cover boolean mask grid."""
        logger.info("Generating vegetation mask")
        return self.rasterize_vector(vegetation_layer, template_raster, all_touched=True)

    def generate_impervious_mask(
        self,
        road_mask: np.ndarray,
        building_mask: np.ndarray,
        extra_concrete_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Combines road, building, and optional concrete footprints to construct
        the total urban impervious surfaces mask.
        """
        logger.info("Generating urban impervious surface mask")
        total_mask = road_mask | building_mask
        if extra_concrete_mask is not None:
            total_mask = total_mask | extra_concrete_mask
        return total_mask
