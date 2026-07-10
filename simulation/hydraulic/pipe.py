"""
simulation/hydraulic/pipe.py
----------------------------
Pipe class representing structural geometry of conduits.
No hydraulic capacity or flow variables are stored in the pipe.
"""

import numpy as np


class Pipe:
    """
    Represents the physical geometry and location of a conduit/pipe edge
    in the sub-surface drainage network.
    """
    def __init__(
        self,
        pipe_id: str,
        length_m: float,
        diameter_m: float,
        roughness_n: float,
        invert_upstream: float,
        invert_downstream: float,
        upstream_node: str,
        downstream_node: str
    ) -> None:
        """
        Args:
            pipe_id: Unique identifier for the pipe.
            length_m: Length of the pipe in meters.
            diameter_m: Diameter of the circular pipe in meters.
            roughness_n: Manning's roughness coefficient (e.g. 0.013 for concrete).
            invert_upstream: Elevation (m) at the upstream pipe connection.
            invert_downstream: Elevation (m) at the downstream pipe connection.
            upstream_node: ID of the upstream junction node.
            downstream_node: ID of the downstream junction node.
        """
        self.pipe_id = pipe_id
        self.length = float(length_m)
        self.diameter = float(diameter_m)
        self.roughness = float(roughness_n)
        self.invert_upstream = float(invert_upstream)
        self.invert_downstream = float(invert_downstream)
        self.upstream_node = upstream_node
        self.downstream_node = downstream_node
        
        # Verify basic geometry parameters
        self._verify_geometry()

        # Calculate slope
        self.slope = (self.invert_upstream - self.invert_downstream) / self.length
        if self.slope <= 0:
            # Enforce a minimal gravity slope to avoid division by zero or backward gravity flow
            self.slope = 1e-4

    def _verify_geometry(self) -> None:
        if self.length <= 0:
            raise ValueError(f"Pipe '{self.pipe_id}' length must be strictly positive.")
        if self.diameter <= 0:
            raise ValueError(f"Pipe '{self.pipe_id}' diameter must be strictly positive.")
        if self.roughness <= 0:
            raise ValueError(f"Pipe '{self.pipe_id}' Manning's roughness must be strictly positive.")
        if self.upstream_node == self.downstream_node:
            raise ValueError(f"Pipe '{self.pipe_id}' cannot connect a node to itself.")
