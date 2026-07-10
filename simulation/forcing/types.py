"""
simulation/forcing/types.py
----------------------------
Forcing types and event definitions.
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any

class ForcingType(Enum):
    RAIN = "rain"
    POINT = "point"
    AREA = "area"
    LINE = "line"
    RIVER = "river"
    TIDE = "tide"
    DRAIN = "drain"
    USER = "user"


class ForcingEventType(Enum):
    RAIN_STARTED = "Rain Started"
    RAIN_STOPPED = "Rain Stopped"
    SOURCE_ADDED = "Source Added"
    SOURCE_REMOVED = "Source Removed"
    SIMULATION_STARTED = "Simulation Started"
    SIMULATION_FINISHED = "Simulation Finished"


@dataclass
class ForcingEvent:
    timestamp: str
    simulation_uuid: str
    event_type: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
