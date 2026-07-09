"""
simulation/core/cell.py
-----------------------
Represents a single computational grid cell (pixel) in the Digital Twin.
Stores static physical attributes and dynamic simulation states.
"""

from dataclasses import dataclass


@dataclass
class Cell:
    """
    Lightweight cell model representing a single DEM pixel.
    
    Static properties describe the physical environment of the cell, while
    dynamic properties capture the state variables updated at each timestep.
    """
    # Grid coordinates
    row: int
    col: int
    
    # --- Static Physical Properties ---
    elevation: float            # Elevation in meters (DEM value)
    land_cover: str             # Land cover classification type
    surface_roughness: float    # Manning's roughness coefficient (n)
    building_mask: bool         # True if building footprint is present
    road_mask: bool             # True if road centerline is present
    river_mask: bool            # True if waterway is present
    drain_capacity: float       # Storm drain inlet capacity in m/s or m3/s
    soil_type: str              # Soil type classification for infiltration (e.g. HSG A/B/C/D)
    
    # --- Dynamic Simulation States ---
    water_depth: float = 0.0    # Current water depth on surface (m)
    rainfall: float = 0.0       # Incremental rainfall depth deposited (m)
    velocity_x: float = 0.0     # Flow velocity in X direction (m/s)
    velocity_y: float = 0.0     # Flow velocity in Y direction (m/s)
    flow_direction: float = 0.0 # Direction of flow in compass degrees [0, 360)
    infiltration: float = 0.0   # Infiltrated water depth in this step (m)
    flood_flag: bool = False    # True if water_depth exceeds flood threshold (e.g. >0.05m)
