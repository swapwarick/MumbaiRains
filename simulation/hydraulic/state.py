"""
simulation/hydraulic/state.py
-----------------------------
HydraulicState storing instantaneous flow and storage variables of the network.
No cumulative variables or tracking balances are stored here.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class OverflowEvent:
    """Represents a localized water spill above ground level."""
    junction_id: str
    volume_m3: float
    elevation: float
    timestamp_seconds: float


@dataclass
class DischargeRequest:
    """Represents an outfall outflow request sent to boundary elements (e.g. TideEngine)."""
    outfall_id: str
    requested_flow_m3_s: float
    elevation: float


@dataclass
class HydraulicState:
    """
    Holds the instantaneous state variables of the network at any point in time.
    """
    pipe_flow: Dict[str, float]  # Instantaneous flow rate per pipe (m^3/s)
    pipe_storage: Dict[str, float]  # Instantaneous volume of water in pipe (m^3)
    junction_storage: Dict[str, float]  # Instantaneous volume of water in junction manhole (m^3)
    overflow_events: List[OverflowEvent] = field(default_factory=list)  # Spill events generated this step
    discharge_requests: List[DischargeRequest] = field(default_factory=list)  # Discharge requests generated this step
