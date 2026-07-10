"""
simulation/hydraulic/junction.py
--------------------------------
Junction class representing physical geometry of network junctions/nodes.
"""


class Junction:
    """
    Represents the physical boundaries and properties of a manhole/junction node
    in the sub-surface drainage network.
    """
    def __init__(
        self,
        junction_id: str,
        ground_elevation: float,
        invert_elevation: float,
        overflow_elevation: float,
        max_storage_volume: float = 10.0
    ) -> None:
        """
        Args:
            junction_id: Unique identifier for the junction.
            ground_elevation: Surface elevation at ground level (m).
            invert_elevation: Elevation of the bottom of the junction (m).
            overflow_elevation: Elevation at which water starts to spill above ground (m).
            max_storage_volume: Nominal storage capacity (m^3) before overflow events trigger.
        """
        self.junction_id = junction_id
        self.ground_elevation = float(ground_elevation)
        self.invert_elevation = float(invert_elevation)
        self.overflow_elevation = float(overflow_elevation)
        self.max_storage_volume = float(max_storage_volume)
        
        # Verify elevations
        self._verify_elevations()

    def _verify_elevations(self) -> None:
        if self.invert_elevation > self.ground_elevation:
            raise ValueError(
                f"Junction '{self.junction_id}' invert elevation ({self.invert_elevation}m) "
                f"cannot exceed ground elevation ({self.ground_elevation}m)."
            )
        if self.overflow_elevation < self.ground_elevation:
            raise ValueError(
                f"Junction '{self.junction_id}' overflow elevation ({self.overflow_elevation}m) "
                f"cannot be below ground elevation ({self.ground_elevation}m)."
            )
        if self.max_storage_volume <= 0:
            raise ValueError(f"Junction '{self.junction_id}' max storage volume must be strictly positive.")
