"""
simulation/gis/catalog.py
-------------------------
DatasetCatalog — authoritative catalog for all datasets loaded in the Digital Twin.
Every registered dataset contains strongly typed metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import os

from backend.utils import get_logger
from backend.exceptions import GISException

logger = get_logger(__name__)


@dataclass
class DatasetMetadata:
    """
    Strongly typed metadata tracking fields for active GIS datasets.
    """
    id: str
    name: str
    source: str
    version: str
    license: str
    download_date: str
    processing_date: str
    checksum: str
    crs: str
    extent: Tuple[float, float, float, float]  # (xmin, ymin, xmax, ymax)
    format: str                                 # 'GeoTIFF', 'GeoPackage', etc.
    file_path: str
    resolution: Optional[Tuple[float, float]] = None
    bands: int = 1
    nodata: Optional[float] = None
    processing_history: List[str] = field(default_factory=list)


class DatasetCatalog:
    """
    Registry database for all geospatial files imported into the platform.
    """
    def __init__(self) -> None:
        self._registry: Dict[str, DatasetMetadata] = {}

    def register_dataset(self, dataset: DatasetMetadata) -> None:
        """
        Registers a new dataset in the catalog.
        """
        self._registry[dataset.id.lower()] = dataset
        logger.info(
            "Dataset cataloged successfully",
            extra={"dataset_id": dataset.id, "format": dataset.format, "path": dataset.file_path}
        )

    def remove_dataset(self, dataset_id: str) -> None:
        """
        Removes a dataset from the catalog.
        """
        key = dataset_id.lower()
        if key in self._registry:
            del self._registry[key]
            logger.info("Dataset removed from catalog", extra={"dataset_id": dataset_id})
        else:
            raise GISException(f"Dataset '{dataset_id}' not found in catalog.")

    def get_dataset(self, dataset_id: str) -> DatasetMetadata:
        """
        Retrieves dataset metadata from the catalog.
        """
        key = dataset_id.lower()
        if key not in self._registry:
            raise GISException(f"Dataset '{dataset_id}' not found in catalog.")
        return self._registry[key]

    def list_datasets(self) -> List[DatasetMetadata]:
        """Returns all cataloged datasets."""
        return list(self._registry.values())

    def validate_dataset(self, dataset_id: str) -> List[str]:
        """
        Performs validation checks on a cataloged dataset (file path, CRS structure, size).
        """
        errors = []
        dataset = self.get_dataset(dataset_id)
        
        # 1. File existence
        if not os.path.exists(dataset.file_path):
            errors.append(f"File path does not exist on disk: {dataset.file_path}")
            return errors
            
        # 2. CRS validation
        if not dataset.crs.strip():
            errors.append("Dataset Coordinate Reference System (CRS) is undefined.")
            
        # 3. Extent validation
        xmin, ymin, xmax, ymax = dataset.extent
        if xmin >= xmax or ymin >= ymax:
            errors.append(f"Invalid bounding box boundaries: {dataset.extent}")
            
        # 4. Checksum verification stub
        if not dataset.checksum:
            errors.append("Dataset integrity checksum is missing.")

        return errors
