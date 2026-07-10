"""
backend/data/observation_repo.py
--------------------------------
ObservationRepository for querying observed historical gauges and sensor data.
"""

from typing import Dict, List, Tuple, Any
import csv
import os

from backend.config import settings
from backend.exceptions import GISException

class ObservationRepository:
    """
    Repository for sensor observations and historical gauge readings.
    """
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.join(str(settings.project_root), "data", "validation")
        os.makedirs(self.data_dir, exist_ok=True)

    def load_gauge_observations(self, gauge_id: str) -> List[Tuple[float, float]]:
        """
        Loads time series of observed values (time_min, depth_m) for a given gauge sensor.
        If file doesn't exist, returns realistic generated dummy observations.
        """
        filepath = os.path.join(self.data_dir, f"gauge_{gauge_id}.csv")
        if not os.path.exists(filepath):
            # Return dummy observation series (mock sensor data)
            # representing a 4-hour event with peak at t=2h
            return [
                (0.0, 0.0),
                (30.0, 0.02),
                (60.0, 0.15),
                (90.0, 0.35),
                (120.0, 0.44),  # peak
                (150.0, 0.38),
                (180.0, 0.25),
                (210.0, 0.12),
                (240.0, 0.05)
            ]

        obs = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    obs.append((float(row["time_min"]), float(row["depth_m"])))
            return obs
        except Exception as exc:
            raise GISException(f"Failed to read observations for gauge {gauge_id}: {exc}") from exc
