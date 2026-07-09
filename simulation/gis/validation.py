"""
simulation/gis/validation.py
----------------------------
Defines the ValidationReport dataclass and helpers for structured validation logging.
Ensures scientific auditability and consistency of spatial inputs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class ValidationReport:
    """
    Strongly typed report auditing validation results for GIS datasets.
    """
    dataset_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    crs_status: str = "Valid"
    geometry_status: str = "Valid"
    raster_alignment: str = "Aligned"
    nodata_statistics: Dict[str, Any] = field(default_factory=dict)
    extent: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    resolution: Tuple[float, float] = (0.0, 0.0)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    result: bool = True  # True if valid, False if errors exist
