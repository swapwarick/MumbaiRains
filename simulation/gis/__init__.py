"""
simulation/gis package
----------------------
Layer abstractions and GIS manager coordinating spatial operations.
"""

from .layers import BaseLayer, RasterLayer, VectorLayer, LayerMetadata
from .manager import LayerManager, GISManager
from .catalog import DatasetCatalog, DatasetMetadata
from .crs import CRSManager
from .geometry_repair import repair_geometry, GeometryRepairReport
from .mask_factory import MaskFactory
from .provenance import ProvenanceContext, AuditRecord
from .immutable import ImmutableDataset
from .validation import ValidationReport

__all__ = [
    "BaseLayer",
    "RasterLayer",
    "VectorLayer",
    "LayerMetadata",
    "LayerManager",
    "GISManager",
    "DatasetCatalog",
    "DatasetMetadata",
    "CRSManager",
    "repair_geometry",
    "GeometryRepairReport",
    "MaskFactory",
    "ProvenanceContext",
    "AuditRecord",
    "ImmutableDataset",
    "ValidationReport",
]
