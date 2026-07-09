"""
backend/database/repositories/gis.py
------------------------------------
GISRepository handles reading and writing geospatial layers (roads, buildings, waterways)
from SQLite-based GeoPackages or PostGIS databases.
No SQL or GIS loading logic is allowed outside of this repository layer.
"""

import json
import os
import sqlite3
from typing import Dict, Any

from backend.config import settings
from backend.utils import get_logger
from backend.exceptions import GISException

logger = get_logger(__name__)

try:
    import geopandas as gpd
    _GEOPANDAS = True
except ImportError:
    _GEOPANDAS = False


class GISRepository:
    """
    Data Repository for OpenStreetMap and GIS vector datasets.
    Abstracts files vs database connections from the application services.
    """
    def __init__(self, gpkg_path: str | os.PathLike) -> None:
        self.path = str(gpkg_path)

    def load_vector_layer(self, layer_name: str) -> Dict[str, Any]:
        """
        Loads a GIS vector layer and reprojects to the default CRS if necessary.
        
        Args:
            layer_name: Table/layer name in the database (e.g. roads, buildings, waterways).

        Returns:
            GeoJSON FeatureCollection dictionary.
        """
        # 1. Check geopandas availability & file existence
        if _GEOPANDAS and os.path.exists(self.path) and os.path.getsize(self.path) > 100:
            try:
                gdf = gpd.read_file(self.path, layer=layer_name)
                if gdf.crs and str(gdf.crs) != settings.default_crs:
                    logger.debug(
                        "Reprojecting vector layer",
                        extra={"layer": layer_name, "from_crs": str(gdf.crs), "to_crs": settings.default_crs}
                    )
                    gdf = gdf.to_crs(settings.default_crs)
                return json.loads(gdf.to_json())
            except Exception as exc:
                logger.warning(
                    f"geopandas read failed for {layer_name}: {exc}. Falling back to SQLite."
                )

        # 2. SQLite direct read fallback
        if os.path.exists(self.path):
            try:
                return self._load_from_sqlite(layer_name)
            except Exception as exc:
                raise GISException(
                    f"Failed to query SQLite GeoPackage for {layer_name}: {exc}"
                ) from exc

        logger.warning(
            "GeoPackage file not found — returning empty FeatureCollection",
            extra={"path": self.path, "layer": layer_name}
        )
        return {"type": "FeatureCollection", "features": []}

    def _load_from_sqlite(self, layer_name: str) -> Dict[str, Any]:
        """Reads GeoJSON from SQLite GeoPackage table directly."""
        conn = sqlite3.connect(self.path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({layer_name})")
            columns = [col[1] for col in cursor.fetchall()]

            name_col = (
                "name" if "name" in columns
                else ("type" if "type" in columns else None)
            )

            if "geojson" in columns:
                cursor.execute(f"SELECT {name_col or 'NULL'}, geojson FROM {layer_name}")
                features = []
                for row in cursor.fetchall():
                    prop_val = row[0]
                    prop_key = "name" if name_col == "name" else "type"
                    features.append({
                        "type": "Feature",
                        "properties": {prop_key: prop_val} if name_col else {},
                        "geometry": json.loads(row[1])
                    })
                return {"type": "FeatureCollection", "features": features}
        finally:
            conn.close()

        return {"type": "FeatureCollection", "features": []}
