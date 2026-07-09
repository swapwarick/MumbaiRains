"""
simulation/gis/crs.py
---------------------
Implements CRSManager to coordinate projections, coordinate transformations,
suggest projected coordinate systems, and perform geodetic distance and area calculations.

References:
1. Snyder, J.P., 1987. Map projections--A working manual (Vol. 1395). US Government Printing Office.
2. Karney, C.F., 2013. Algorithms for geodesics. Journal of Geodesy.
"""

from typing import Tuple, List, Optional
import numpy as np
import pyproj
from pyproj import CRS, Transformer, Geod

from backend.utils import get_logger

logger = get_logger(__name__)


class CRSManager:
    """
    Manages projections, coordinate system conversions, and geodetic measurements.
    """
    
    @staticmethod
    def validate_crs(crs_string: str) -> bool:
        """
        Validates whether the provided CRS string is recognized by GDAL/PROJ.

        Args:
            crs_string: CRS representation (e.g. 'EPSG:4326', WKT string).

        Returns:
            True if valid, else False.
        """
        try:
            CRS.from_user_input(crs_string)
            return True
        except Exception as exc:
            logger.warning("Invalid CRS string validation failure", extra={"crs": crs_string, "error": str(exc)})
            return False

    @staticmethod
    def compare_crs(crs_a: str, crs_b: str) -> bool:
        """
        Compares two CRS definitions for equivalence.
        """
        try:
            c1 = CRS.from_user_input(crs_a)
            c2 = CRS.from_user_input(crs_b)
            return c1 == c2
        except Exception:
            return False

    @staticmethod
    def transform_coordinates(
        x: float,
        y: float,
        source_crs: str,
        target_crs: str
    ) -> Tuple[float, float]:
        """
        Transforms coordinates from source CRS to target CRS.

        Args:
            x: Easting or Longitude.
            y: Northing or Latitude.
            source_crs: Source Coordinate system.
            target_crs: Target Coordinate system.

        Returns:
            A tuple of (x_transformed, y_transformed).
        """
        try:
            transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
            tx, ty = transformer.transform(x, y)
            return float(tx), float(ty)
        except Exception as exc:
            logger.error("Coordinate transformation failed", extra={"from": source_crs, "to": target_crs, "error": str(exc)})
            raise exc

    @staticmethod
    def suggest_projected_crs(lon: float, lat: float) -> str:
        """
        Suggests the local UTM (Universal Transverse Mercator) zone projection CRS.
        Formula: Zone = floor((lon + 180) / 6) + 1.
        EPSG prefix is 326xx for northern hemisphere, 327xx for southern hemisphere.
        
        Mumbai (approx 72.85 E, 19.0 N) maps to UTM Zone 43N (EPSG:32643).
        """
        zone = int((lon + 180.0) / 6.0) + 1
        hemisphere = 32600 if lat >= 0 else 32700
        epsg_code = hemisphere + zone
        return f"EPSG:{epsg_code}"

    @staticmethod
    def calculate_distance(
        coord1: Tuple[float, float],
        coord2: Tuple[float, float],
        crs: str
    ) -> float:
        """
        Calculates the distance between two coordinates in the specified CRS.
        If the CRS is geographic, uses Karney's geodesic method (WGS-84 ellipsoidal distance).
        If the CRS is projected, calculates the Euclidean distance.

        Args:
            coord1: (x1, y1) coordinates.
            coord2: (x2, y2) coordinates.
            crs: Coordinate system name.

        Returns:
            Distance in meters.
        """
        proj_crs = CRS.from_user_input(crs)
        
        if proj_crs.is_geographic:
            # Geographic coordinate system: calculate geodetic distance on WGS-84 ellipsoid
            geod = Geod(ellps="WGS84")
            # lon1, lat1, lon2, lat2
            _, _, distance = geod.inv(coord1[0], coord1[1], coord2[0], coord2[1])
            return float(distance)
        else:
            # Projected coordinate system: Euclidean distance
            dx = coord2[0] - coord1[0]
            dy = coord2[1] - coord1[1]
            return float(np.sqrt(dx**2 + dy**2))

    @staticmethod
    def calculate_area(
        polygon_coords: List[Tuple[float, float]],
        crs: str
    ) -> float:
        """
        Calculates the area of a polygon defined by coordinate vertices.
        If the CRS is geographic, calculates ellipsoidal area safely.
        If projected, calculates Euclidean area using the Shoelace algorithm.

        Args:
            polygon_coords: List of (x, y) coordinates defining the closed polygon.
            crs: Coordinate system name.

        Returns:
            Area in square meters.
        """
        if len(polygon_coords) < 3:
            return 0.0

        proj_crs = CRS.from_user_input(crs)
        
        if proj_crs.is_geographic:
            # Ellipsoidal area
            geod = Geod(ellps="WGS84")
            lons = [c[0] for c in polygon_coords]
            lats = [c[1] for c in polygon_coords]
            area, _ = geod.polygon_area_perimeter(lons, lats)
            return float(abs(area))
        else:
            # Shoelace polygon area: 0.5 * abs(sum(x_i * y_{i+1} - x_{i+1} * y_i))
            x = np.array([c[0] for c in polygon_coords])
            y = np.array([c[1] for c in polygon_coords])
            
            # Make sure it is closed
            if x[0] != x[-1] or y[0] != y[-1]:
                x = np.append(x, x[0])
                y = np.append(y, y[0])
                
            return float(0.5 * np.abs(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1])))
