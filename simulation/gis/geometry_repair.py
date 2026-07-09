"""
simulation/gis/geometry_repair.py
---------------------------------
GeometryRepair — provides geometry validation and explicit geoprocessing repair.
Repair is never automatic. Immutable original geometries are preserved.

References:
1. Shapely geometry repair protocols and WKB serialization standards.
"""

from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional
import numpy as np

from backend.utils import get_logger
from backend.exceptions import GISException

logger = get_logger(__name__)

try:
    from shapely.geometry import shape as shapely_shape, mapping
    from shapely.validation import explain_validity, make_valid
    _SHAPELY = True
except ImportError:
    _SHAPELY = False


@dataclass
class GeometryRepairReport:
    """
    Detailed audit report for a geometry repair operation.
    """
    geometry_id: str
    original_validity_error: str
    repair_method_used: str
    repair_succeeded: bool
    geometry_area_before: float
    geometry_area_after: float
    geometry_changed: bool


def repair_geometry(
    geojson_feature: Dict[str, Any],
    geometry_id: str,
    repair_requested: bool = False
) -> Tuple[Dict[str, Any], GeometryRepairReport]:
    """
    Validates and conditionally repairs a GeoJSON geometry.
    Original geometries remain immutable.

    Args:
        geojson_feature: Input GeoJSON feature dictionary (read-only).
        geometry_id: Unique identifier for the feature/geometry.
        repair_requested: If True, executes the repair algorithm. If False, only validates.

    Returns:
        A tuple of (resulting_feature_dict, GeometryRepairReport).
    """
    if not _SHAPELY:
        raise GISException("Shapely is required for geometry validation and repair.")

    geom_data = geojson_feature.get("geometry")
    if not geom_data:
        report = GeometryRepairReport(
            geometry_id=geometry_id,
            original_validity_error="Empty or missing geometry payload",
            repair_method_used="None",
            repair_succeeded=False,
            geometry_area_before=0.0,
            geometry_area_after=0.0,
            geometry_changed=False
        )
        return geojson_feature, report

    geom = shapely_shape(geom_data)
    area_before = float(geom.area)

    # 1. Validation is always performed
    if geom.is_valid:
        report = GeometryRepairReport(
            geometry_id=geometry_id,
            original_validity_error="None - Geometry is valid",
            repair_method_used="None",
            repair_succeeded=True,
            geometry_area_before=area_before,
            geometry_area_after=area_before,
            geometry_changed=False
        )
        return geojson_feature, report

    validity_reason = explain_validity(geom)

    # 2. Repair is NEVER automatic
    if not repair_requested:
        logger.warning(
            "Invalid geometry detected; repair was not requested",
            extra={"geometry_id": geometry_id, "error": validity_reason}
        )
        report = GeometryRepairReport(
            geometry_id=geometry_id,
            original_validity_error=validity_reason,
            repair_method_used="None",
            repair_succeeded=False,
            geometry_area_before=area_before,
            geometry_area_after=area_before,
            geometry_changed=False
        )
        return geojson_feature, report

    # 3. Explicit repair requested
    logger.info(
        "Executing explicit geometry repair",
        extra={"geometry_id": geometry_id, "error": validity_reason}
    )
    
    repair_method = "make_valid"
    try:
        repaired_geom = make_valid(geom)
        
        # If make_valid results in GeometryCollection containing multiple types,
        # extract the dominant polygon/multipolygon geometries.
        if repaired_geom.geom_type == "GeometryCollection":
            sub_geoms = [g for g in repaired_geom.geoms if g.geom_type in (geom.geom_type, "Polygon", "MultiPolygon")]
            if sub_geoms:
                from shapely.ops import unary_union
                repaired_geom = unary_union(sub_geoms)
                repair_method = "make_valid + unary_union"

        # Fallback to buffer(0) if still invalid
        if not repaired_geom.is_valid:
            repaired_geom = geom.buffer(0.0)
            repair_method = "buffer(0.0)"

        if repaired_geom.is_valid:
            area_after = float(repaired_geom.area)
            changed = not repaired_geom.equals(geom)
            
            report = GeometryRepairReport(
                geometry_id=geometry_id,
                original_validity_error=validity_reason,
                repair_method_used=repair_method,
                repair_succeeded=True,
                geometry_area_before=area_before,
                geometry_area_after=area_after,
                geometry_changed=changed
            )
            
            # Create a new copy - original remains immutable
            repaired_feature = geojson_feature.copy()
            repaired_feature["geometry"] = mapping(repaired_geom)
            
            logger.info("Geometry repair succeeded", extra={"geometry_id": geometry_id, "method": repair_method})
            return repaired_feature, report
            
    except Exception as exc:
        logger.error(
            "Geometry repair failed due to exception",
            extra={"geometry_id": geometry_id, "error": str(exc)}
        )

    # If repair failed, return original geometry with failed report
    report = GeometryRepairReport(
        geometry_id=geometry_id,
        original_validity_error=validity_reason,
        repair_method_used=repair_method,
        repair_succeeded=False,
        geometry_area_before=area_before,
        geometry_area_after=area_before,
        geometry_changed=False
    )
    return geojson_feature, report
