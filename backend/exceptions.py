"""
Custom Exceptions
-----------------
Domain-specific exception hierarchy for the Mumbai Flood Digital Twin.
Catching these in API controllers allows fine-grained HTTP error mapping.

Hierarchy:
    FloodTwinException
    ├── TerrainException
    ├── SimulationException
    ├── GISException
    ├── DrainageException
    └── RainfallException
"""


class FloodTwinException(Exception):
    """Base exception for all domain errors in this platform."""


class TerrainException(FloodTwinException):
    """Raised when DEM loading or terrain processing fails."""


class SimulationException(FloodTwinException):
    """Raised when the simulation engine encounters an unrecoverable error."""


class GISException(FloodTwinException):
    """Raised when GIS layer loading, CRS validation, or geometry checks fail."""


class MissingSpatialDependencyError(GISException):
    """Raised when required spatial libraries (rasterio, geopandas, shapely) are unavailable."""


class DrainageException(FloodTwinException):
    """Raised when drainage network initialisation or routing fails."""


class RainfallException(FloodTwinException):
    """Raised when rainfall data loading or hyetograph generation fails."""
